// index.ts - API Server
import express, { Request, Response } from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import { z } from 'zod';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { spawn } from 'child_process';
import { scraperService } from './scraper.service.js';
import { MarkdownGenerator } from './markdown-generator.js';
import { JobData } from './types.js';

// ─── Terminal Spinner ────────────────────────────────────────────────────────

const SPINNER_FRAMES = ['|', '/', '-', '\\'];

function createSpinner(label: string) {
    let frame = 0;
    const start = Date.now();
    const isTTY = process.stdout.isTTY;

    const interval = setInterval(() => {
        const elapsed = ((Date.now() - start) / 1000).toFixed(1);
        const icon = SPINNER_FRAMES[frame % SPINNER_FRAMES.length];
        frame++;
        if (isTTY) {
            process.stdout.write(`\r  ${icon} ${label} (${elapsed}s)   `);
        }
    }, 100);

    return {
        stop(success: boolean, msg?: string) {
            clearInterval(interval);
            const elapsed = ((Date.now() - start) / 1000).toFixed(1);
            const icon = success ? '✅' : '❌';
            const line = msg ?? label;
            if (isTTY) {
                process.stdout.write(`\r  ${icon} ${line} (${elapsed}s)` + ' '.repeat(10) + '\n');
            } else {
                console.log(`  ${icon} ${line} (${elapsed}s)`);
            }
        }
    };
}

async function withSpinner<T>(label: string, fn: () => Promise<T>): Promise<T> {
    const spinner = createSpinner(label);
    try {
        const result = await fn();
        spinner.stop(true);
        return result;
    } catch (err) {
        spinner.stop(false, `ERRO em: ${label}`);
        throw err;
    }
}
// ─────────────────────────────────────────────────────────────────────────────

const app = express();
const PORT = process.env.PORT || 3000;
const FRONT_ORIGIN = process.env.FRONT_ORIGIN || 'http://localhost:8000';
const WEBHOOK_URL = 'https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional';
const ROOT_DIR = process.cwd();
const LANGCHAIN_DIR = path.join(ROOT_DIR, 'langchain');
const UPLOAD_DIR = path.join(LANGCHAIN_DIR, 'uploads');
const INGEST_SCRIPT_PATH = path.join(LANGCHAIN_DIR, 'Agente_FAQ.py');
const PYTHON_BIN = process.env.PYTHON_BIN || 'python';

function loadEnvFile(filePath: string): Record<string, string> {
    if (!fs.existsSync(filePath)) return {};
    const content = fs.readFileSync(filePath, 'utf-8');
    const env: Record<string, string> = {};
    for (const line of content.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx === -1) continue;
        env[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim();
    }
    return env;
}

const langchainEnv = loadEnvFile(path.join(LANGCHAIN_DIR, '.env'));
const SUPABASE_URL = langchainEnv.SUPABASE_URL || '';
const SUPABASE_SERVICE_KEY = langchainEnv.SUPABASE_SERVICE_KEY || '';

app.use(cors({ origin: '*' }));
app.use(express.json());

// 📦 Fila em memória (Para produção, considere Redis/BullMQ)
const jobQueue = new Map<string, JobData>();

if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

function sanitizeFileStem(fileName: string): string {
    const stem = path.parse(fileName).name;
    const sanitized = stem
        .replace(/\s+/g, '_')
        .replace(/[^a-zA-Z0-9_-]/g, '')
        .trim();

    if (!sanitized) {
        throw new Error('Nome de arquivo inválido para derivar ID_Conta');
    }

    return sanitized;
}

function deriveIdContaFromFileName(fileName: string): string {
    return sanitizeFileStem(fileName);
}

const storage = multer.diskStorage({
    destination: (_req, _file, cb) => {
        cb(null, UPLOAD_DIR);
    },
    filename: (_req, file, cb) => {
        try {
            const idConta = deriveIdContaFromFileName(file.originalname);
            cb(null, `${idConta}.md`);
        } catch (error: any) {
            cb(error);
        }
    }
});

const upload = multer({
    storage,
    limits: {
        fileSize: 20 * 1024 * 1024 // 20MB
    },
    fileFilter: (_req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        if (ext !== '.md') {
            cb(new Error('Apenas arquivos .md são permitidos'));
            return;
        }
        cb(null, true);
    }
});

const chatSchema = z.object({
    message: z.string().min(1, 'Mensagem obrigatória'),
    ID_Conta: z.string().min(1, 'ID_Conta obrigatório')
});

// Validação de entrada
const scrapeSchema = z.object({
    url: z.string().url({ message: 'URL inválida' }),
    options: z.object({
        timeout: z.number().min(5000).max(120000).optional(),
        waitUntil: z.enum(['load', 'domcontentloaded', 'networkidle0', 'networkidle2']).optional(),
    }).optional(),
});

/**
 * Endpoint de Health Check
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        activeJobs: jobQueue.size
    });
});

/**
 * POST /scrape - Inicia scraping assíncrono
 */
app.post('/scrape', async (req: Request, res: Response) => {
    try {
        const { url, options } = scrapeSchema.parse(req.body);
        const jobId = uuidv4();

        // Registra a tarefa
        jobQueue.set(jobId, {
            id: jobId,
            status: 'pending',
            url,
            startTime: Date.now()
        });

        // Dispara processamento em background (não bloqueia)
        processScrapingJob(jobId, url, options);

        // Responde imediatamente com 202 Accepted
        res.status(202).json({
            success: true,
            jobId,
            statusUrl: `http://localhost:${PORT}/status/${jobId}`,
            message: 'Scraping iniciado. Use o statusUrl para acompanhar.'
        });

    } catch (error: any) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/ingest-markdown - Upload de markdown e execução da ingestão
 */
app.post('/api/ingest-markdown', upload.single('markdownFile'), async (req: Request, res: Response) => {
    try {
        const file = req.file;
        if (!file) {
            return res.status(400).json({
                success: false,
                error: 'Nenhum arquivo enviado no campo markdownFile'
            });
        }

        const idConta = deriveIdContaFromFileName(file.originalname);
        const clear = String(req.body.clear || '').toLowerCase() === 'true';
        const table = String(req.body.table || 'marketing_rag');

        const ingestResult = await runIngestion(file.path, table, clear);

        return res.status(200).json({
            success: true,
            message: 'Ingestão concluída com sucesso',
            data: {
                ID_Conta: idConta,
                filePath: file.path,
                table,
                clear,
                output: ingestResult
            }
        });
    } catch (error: any) {
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/chat - Proxy para webhook N8N
 */
app.post('/api/chat', async (req: Request, res: Response) => {
    try {
        const { message, ID_Conta } = chatSchema.parse(req.body);

        const webhookResponse = await fetch(WEBHOOK_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, ID_Conta })
        });

        if (!webhookResponse.ok) {
            const body = await webhookResponse.text();
            throw new Error(`Webhook retornou ${webhookResponse.status}: ${body}`);
        }

        const contentType = webhookResponse.headers.get('content-type') || '';
        let reply = '';
        let raw: unknown = null;

        if (contentType.includes('application/json')) {
            raw = await webhookResponse.json();
            reply = extractReplyFromUnknown(raw);
        } else {
            raw = await webhookResponse.text();
            reply = String(raw);
        }

        return res.status(200).json({
            success: true,
            data: {
                reply,
                raw,
                ID_Conta
            }
        });
    } catch (error: any) {
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /status/:id - Consulta status da tarefa
 */
app.get('/status/:id', (req: Request, res: Response) => {
    const job = jobQueue.get(req.params.id);

    if (!job) {
        return res.status(404).json({
            success: false,
            error: 'Tarefa não encontrada'
        });
    }

    // Tarefa completada
    if (job.status === 'completed') {
        return res.json({
            status: 'completed',
            duration: `${((job.endTime! - job.startTime) / 1000).toFixed(2)}s`,
            data: {
                url: job.result!.url,
                markdownFile: job.result!.markdownFile,
                stats: job.result!.stats,
                metadata: job.result!.metadata,
                contactInfo: job.result!.contactInfo,
                storeInfo: job.result!.storeInfo
            }
        });
    }

    // Tarefa falhou
    if (job.status === 'failed') {
        return res.json({
            status: 'failed',
            error: job.error
        });
    }

    // Ainda processando
    res.json({
        status: job.status,
        url: job.url,
        elapsed: `${((Date.now() - job.startTime) / 1000).toFixed(2)}s`
    });
});

function extractReplyFromUnknown(data: unknown): string {
    if (typeof data === 'string') return data;
    if (Array.isArray(data)) return data.map(item => extractReplyFromUnknown(item)).join('\n').trim();
    if (!data || typeof data !== 'object') return JSON.stringify(data);

    const possibleKeys = ['reply', 'response', 'answer', 'message', 'output', 'text'];
    for (const key of possibleKeys) {
        const value = (data as Record<string, unknown>)[key];
        if (typeof value === 'string' && value.trim()) {
            return value;
        }
    }

    return JSON.stringify(data);
}

function runIngestion(inputPath: string, table: string, clear: boolean): Promise<{ stdout: string; stderr: string }> {
    return new Promise((resolve, reject) => {
        if (!fs.existsSync(INGEST_SCRIPT_PATH)) {
            reject(new Error(`Script de ingestão não encontrado: ${INGEST_SCRIPT_PATH}`));
            return;
        }

        const args = [INGEST_SCRIPT_PATH, '--input', inputPath, '--table', table];
        if (clear) {
            args.push('--clear');
        }

        const child = spawn(PYTHON_BIN, args, {
            cwd: ROOT_DIR,
            env: { ...process.env, PYTHONUNBUFFERED: '1' }  // força flush imediato no Python
        });

        let stdout = '';
        let stderr = '';
        let lineBuffer = '';

        child.stdout.on('data', (chunk: Buffer) => {
            const text = chunk.toString();
            stdout += text;
            // Imprime cada linha em tempo real com prefixo visual
            lineBuffer += text;
            const lines = lineBuffer.split('\n');
            lineBuffer = lines.pop() ?? '';
            for (const ln of lines) {
                if (ln.trim()) console.log(`  │ ${ln}`);
            }
        });

        child.stdout.on('end', () => {
            if (lineBuffer.trim()) console.log(`  │ ${lineBuffer}`);
        });

        child.stderr.on('data', (chunk: Buffer) => {
            stderr += chunk.toString();
        });

        child.on('error', (err) => {
            reject(new Error(`Falha ao executar Python (${PYTHON_BIN}): ${err.message}`));
        });

        child.on('close', (code) => {
            if (code === 0) {
                resolve({ stdout, stderr });
                return;
            }
            reject(new Error(`Ingestão falhou com código ${code}. Detalhes: ${stderr || stdout}`));
        });
    });
}

/**
 * GET /api/pipelines - Lista pipelines do Supabase
 */
app.get('/api/pipelines', async (req: Request, res: Response) => {
    try {
        if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
            return res.status(500).json({
                success: false,
                error: 'Credenciais Supabase não configuradas (langchain/.env)'
            });
        }

        const supaResponse = await fetch(
            `${SUPABASE_URL}/rest/v1/marketing_rag?select=ID_Conta,metadata`,
            {
                headers: {
                    'apikey': SUPABASE_SERVICE_KEY,
                    'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}`,
                }
            }
        );

        if (!supaResponse.ok) {
            const body = await supaResponse.text();
            throw new Error(`Supabase retornou ${supaResponse.status}: ${body}`);
        }

        const rows: any[] = await supaResponse.json();

        if (!rows || rows.length === 0) {
            return res.json({ success: true, data: [] });
        }

        const pipelinesMap: Record<string, { ID_Conta: string; url_inferido: string; total_faqs: number }> = {};

        for (const row of rows) {
            const idConta = row.ID_Conta;
            if (idConta && !pipelinesMap[idConta]) {
                const domainParts = idConta.includes('_') ? idConta.split('_')[0] : idConta;
                const urlInferido = domainParts.replace(/-/g, '.');
                pipelinesMap[idConta] = {
                    ID_Conta: idConta,
                    url_inferido: urlInferido.startsWith('http') ? urlInferido : `https://${urlInferido}`,
                    total_faqs: 0,
                };
            }
        }

        for (const row of rows) {
            const idConta = row.ID_Conta;
            if (idConta && pipelinesMap[idConta]) {
                pipelinesMap[idConta].total_faqs += 1;
            }
        }

        return res.json({ success: true, data: Object.values(pipelinesMap) });
    } catch (error: any) {
        console.error('[pipelines] Erro:', error.message);
        return res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * POST /api/pipeline - Pipeline completo: scrape → markdown → ingest
 */
app.post('/api/pipeline', async (req: Request, res: Response) => {
    try {
        const { url, table = 'marketing_rag', clear = false } = req.body;

        if (!url || typeof url !== 'string') {
            return res.status(400).json({ success: false, error: 'URL obrigatória' });
        }

        const hostname = new URL(url).hostname.replace(/^www\./, '');
        const idConta = hostname.replace(/\./g, '-');
        const mdFilename = `${idConta}.md`;
        const mdPath = path.join(UPLOAD_DIR, mdFilename);

        console.log(`\n${'='.repeat(60)}`);
        console.log(`  [PIPELINE] COMPLETO`);
        console.log(`${'='.repeat(60)}`);
        console.log(`  [URL]     : ${url}`);
        console.log(`  [tabela]  : ${table}`);
        console.log(`  [clear]   : ${clear}`);
        console.log(`  [id_conta]: ${idConta}`);
        console.log(`${'-'.repeat(60)}`);

        // -- 1. Scraping -------------------------------------------
        let scrapeResult: any;
        await withSpinner(`[1/3] Scraping: ${hostname}`, async () => {
            scrapeResult = await scraperService.scrapeUrl(url);
        });

        // -- 2. Markdown -------------------------------------------
        let markdown = '';
        await withSpinner(`[2/3] Gerando Markdown`, async () => {
            markdown = MarkdownGenerator.generate(scrapeResult);
            fs.writeFileSync(mdPath, markdown, 'utf-8');
        });
        console.log(`  [info] ${markdown.length.toLocaleString()} chars -> ${mdPath}`);

        // -- 3. Ingestão FAQ ---------------------------------------
        const chunks = Math.ceil(markdown.length / 50_000);
        console.log(`\n  [3/3] Ingestao FAQ (${chunks} chunk${chunks > 1 ? 's' : ''} estimado${chunks > 1 ? 's' : ''})`);
        console.log(`${'-'.repeat(60)}`);

        const ingestResult = await runIngestion(mdPath, table, clear);

        console.log(`${'-'.repeat(60)}`);
        console.log(`  [OK] Ingestao concluida`);
        console.log(`${'='.repeat(60)}\n`);

        return res.json({
            success: true,
            message: 'Pipeline completo executado com sucesso',
            data: {
                url,
                ID_Conta: idConta,
                markdown_file: mdPath,
                markdown_length: markdown.length,
                table,
                clear,
                ingest_output: ingestResult,
            }
        });
    } catch (error: any) {
        console.error(`\n  [X] [pipeline] Erro: ${error.message}`);
        return res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * 404 Handler
 */
app.use((req, res) => {
    res.status(404).json({
        success: false,
        error: 'Endpoint não encontrado'
    });
});

/**
 * 🎯 Função de Background - Processa scraping e gera markdown
 */
async function processScrapingJob(jobId: string, url: string, options: any) {
    const job = jobQueue.get(jobId)!;

    try {
        job.status = 'processing';
        console.log(`\n[Job ${jobId}] 🚀 Iniciando processamento: ${url}`);

        // 1. Executa o scraping
        const result = await scraperService.scrapeUrl(url, options);

        // 2. 🎯 GERA O ARQUIVO MARKDOWN
        const markdownPath = MarkdownGenerator.generateAndSave(result, jobId);

        // 3. Atualiza o job com sucesso
        job.status = 'completed';
        job.result = {
            ...result,
            markdownFile: markdownPath
        };
        job.endTime = Date.now();

        const duration = ((job.endTime - job.startTime) / 1000).toFixed(2);
        console.log(`[Job ${jobId}] ✅ Concluído em ${duration}s`);
        console.log(`[Job ${jobId}] 📄 Markdown salvo em: ${markdownPath}`);

    } catch (error: any) {
        console.error(`[Job ${jobId}] ❌ Erro:`, error.message);
        job.status = 'failed';
        job.error = error.message;
        job.endTime = Date.now();
    }
}

// Limpeza periodica: Remove jobs antigos (> 1 hora)
setInterval(() => {
    const now = Date.now();
    const oneHour = 3600000;

    for (const [id, job] of jobQueue.entries()) {
        if (job.endTime && (now - job.endTime > oneHour)) {
            jobQueue.delete(id);
            console.log(`[cleanup] Job ${id} removido (expirado)`);
        }
    }
}, 600000); // Executa a cada 10 minutos

// Inicia o servidor
app.listen(PORT, () => {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`  API DE SCRAPING INSTITUCIONAL`);
    console.log(`${'='.repeat(60)}`);
    console.log(`  Servidor: http://localhost:${PORT}`);
    console.log(`\n  Endpoints:`);
    console.log(`   POST   /api/pipeline        - Pipeline completo (scrape+ingest)`);
    console.log(`   GET    /api/pipelines       - Lista sites processados (Supabase)`);
    console.log(`   POST   /api/chat            - Chat com proxy para N8N`);
    console.log(`   POST   /api/ingest-markdown - Upload e ingestao por ID_Conta`);
    console.log(`   POST   /scrape              - Inicia scraping`);
    console.log(`   GET    /status/:id          - Consulta status`);
    console.log(`   GET    /health              - Health check`);
    console.log(`  Supabase: ${SUPABASE_URL ? 'Conectado' : '[!] NAO CONFIGURADO'}`);
    console.log(`${'='.repeat(60)}\n`);
});
