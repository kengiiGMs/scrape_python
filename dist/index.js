// index.ts - API Server
import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import { z } from 'zod';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { spawn } from 'child_process';
import { scraperService } from './scraper.service.js';
import { MarkdownGenerator } from './markdown-generator.js';
const app = express();
const PORT = process.env.PORT || 3000;
const WEBHOOK_URL = 'https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional';
const ROOT_DIR = process.cwd();
const PUBLIC_DIR = path.join(ROOT_DIR, 'public');
const LANGCHAIN_DIR = path.join(ROOT_DIR, 'langchain');
const UPLOAD_DIR = path.join(LANGCHAIN_DIR, 'uploads');
const INGEST_SCRIPT_PATH = path.join(LANGCHAIN_DIR, 'Agente_FAQ.py');
const PYTHON_BIN = process.env.PYTHON_BIN || 'python';
app.use(express.json());
app.use(express.static(PUBLIC_DIR));
// 📦 Fila em memória (Para produção, considere Redis/BullMQ)
const jobQueue = new Map();
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}
function sanitizeFileStem(fileName) {
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
function deriveIdContaFromFileName(fileName) {
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
        }
        catch (error) {
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
app.get('/', (_req, res) => {
    res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
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
app.post('/scrape', async (req, res) => {
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
    }
    catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});
/**
 * POST /api/ingest-markdown - Upload de markdown e execução da ingestão
 */
app.post('/api/ingest-markdown', upload.single('markdownFile'), async (req, res) => {
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
    }
    catch (error) {
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});
/**
 * POST /api/chat - Proxy para webhook N8N
 */
app.post('/api/chat', async (req, res) => {
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
        let raw = null;
        if (contentType.includes('application/json')) {
            raw = await webhookResponse.json();
            reply = extractReplyFromUnknown(raw);
        }
        else {
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
    }
    catch (error) {
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});
/**
 * GET /status/:id - Consulta status da tarefa
 */
app.get('/status/:id', (req, res) => {
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
            duration: `${((job.endTime - job.startTime) / 1000).toFixed(2)}s`,
            data: {
                url: job.result.url,
                markdownFile: job.result.markdownFile,
                stats: job.result.stats,
                metadata: job.result.metadata,
                contactInfo: job.result.contactInfo,
                storeInfo: job.result.storeInfo
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
function extractReplyFromUnknown(data) {
    if (typeof data === 'string')
        return data;
    if (Array.isArray(data))
        return data.map(item => extractReplyFromUnknown(item)).join('\n').trim();
    if (!data || typeof data !== 'object')
        return JSON.stringify(data);
    const possibleKeys = ['reply', 'response', 'answer', 'message', 'output', 'text'];
    for (const key of possibleKeys) {
        const value = data[key];
        if (typeof value === 'string' && value.trim()) {
            return value;
        }
    }
    return JSON.stringify(data);
}
function runIngestion(inputPath, table, clear) {
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
            env: process.env
        });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (chunk) => {
            stdout += chunk.toString();
        });
        child.stderr.on('data', (chunk) => {
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
async function processScrapingJob(jobId, url, options) {
    const job = jobQueue.get(jobId);
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
    }
    catch (error) {
        console.error(`[Job ${jobId}] ❌ Erro:`, error.message);
        job.status = 'failed';
        job.error = error.message;
        job.endTime = Date.now();
    }
}
// 🧹 Limpeza periódica: Remove jobs antigos (> 1 hora)
setInterval(() => {
    const now = Date.now();
    const oneHour = 3600000;
    for (const [id, job] of jobQueue.entries()) {
        if (job.endTime && (now - job.endTime > oneHour)) {
            jobQueue.delete(id);
            console.log(`🗑️  Job ${id} removido (expirado)`);
        }
    }
}, 600000); // Executa a cada 10 minutos
// Inicia o servidor
app.listen(PORT, () => {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`🚀 API DE SCRAPING INSTITUCIONAL`);
    console.log(`${'='.repeat(60)}`);
    console.log(`📡 Servidor rodando em: http://localhost:${PORT}`);
    console.log(`\n📌 Endpoints disponíveis:`);
    console.log(`   POST   /scrape       - Inicia scraping`);
    console.log(`   POST   /api/ingest-markdown - Upload e ingestão por ID_Conta`);
    console.log(`   POST   /api/chat     - Chat com proxy para N8N`);
    console.log(`   GET    /status/:id   - Consulta status`);
    console.log(`   GET    /health       - Health check`);
    console.log(`${'='.repeat(60)}\n`);
});
