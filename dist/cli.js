// cli.ts - Script de linha de comando (substitui main.ts)
import { scraperService } from './scraper.service.js';
import { MarkdownGenerator } from './markdown-generator.js';
async function main() {
    const targetUrl = process.argv[2];
    if (!targetUrl) {
        console.error('❌ Erro: URL não fornecida');
        console.log('\n📖 Uso: npm run cli <URL>');
        console.log('   Exemplo: npm run cli https://example.com\n');
        process.exit(1);
    }
    try {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`🎯 SCRAPING CLI - Modo Direto`);
        console.log(`${'='.repeat(60)}`);
        console.log(`🌐 URL: ${targetUrl}\n`);
        const startTime = Date.now();
        // 1. Executa scraping
        console.log('🔄 Iniciando scraping...\n');
        const result = await scraperService.scrapeUrl(targetUrl, {
            waitUntil: 'networkidle2',
            timeout: 30000
        });
        // 2. Gera markdown
        console.log('\n📝 Gerando arquivo markdown...');
        const markdownPath = MarkdownGenerator.generateAndSave(result, 'cli-' + Date.now());
        const duration = ((Date.now() - startTime) / 1000).toFixed(2);
        // 3. Exibe resumo
        console.log(`\n${'='.repeat(60)}`);
        console.log(`✅ SCRAPING CONCLUÍDO EM ${duration}s`);
        console.log(`${'='.repeat(60)}`);
        console.log(`\n📊 Resumo:`);
        console.log(`   📄 Páginas processadas: ${result.stats.pagesScraped}`);
        console.log(`   📋 Páginas institucionais: ${result.stats.totalInstitutional}`);
        console.log(`   📧 Emails encontrados: ${result.contactInfo.emails.length}`);
        console.log(`   📞 Telefones encontrados: ${result.contactInfo.phones.length}`);
        console.log(`   🌐 Redes sociais: ${Object.keys(result.contactInfo.socialMedia).length}`);
        console.log(`   📄 Markdown salvo em: ${markdownPath}`);
        console.log(`${'='.repeat(60)}\n`);
        await scraperService.closeBrowser();
        process.exit(0);
    }
    catch (error) {
        console.error(`\n❌ ERRO: ${error.message}\n`);
        await scraperService.closeBrowser();
        process.exit(1);
    }
}
main();
