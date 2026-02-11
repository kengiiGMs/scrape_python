// scraper.service.ts - Versão MELHORADA CORRIGIDA
import puppeteer from 'puppeteer';
import * as cheerio from 'cheerio';
import TurndownService from 'turndown';
import * as fs from 'fs';
class WebScraperService {
    browser = null;
    turndownService;
    visitedUrls = new Set();
    constructor() {
        this.turndownService = new TurndownService({
            headingStyle: 'atx',
            hr: '---',
            bulletListMarker: '-',
            codeBlockStyle: 'fenced',
        });
    }
    // ============================================================================
    // 🆕 ANTI-DETECÇÃO - Headers e User-Agent Dinâmicos
    // ============================================================================
    async configurePage(page) {
        const userAgents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ];
        await page.setUserAgent(userAgents[Math.floor(Math.random() * userAgents.length)]);
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        });
    }
    // ============================================================================
    // 🆕 DELAY ALEATÓRIO
    // ============================================================================
    async randomDelay(min = 1500, max = 3500) {
        const delay = Math.floor(Math.random() * (max - min + 1)) + min;
        console.log(`   ⏳ Aguardando ${(delay / 1000).toFixed(1)}s...`);
        await new Promise(resolve => setTimeout(resolve, delay));
    }
    // ============================================================================
    // 🆕 SCROLL PROGRESSIVO
    // ============================================================================
    async progressiveScroll(page) {
        await page.evaluate(async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight || totalHeight > 10000) {
                        clearInterval(timer);
                        window.scrollTo(0, 0);
                        resolve();
                    }
                }, 200);
            });
        });
    }
    // ============================================================================
    // 🆕 CARREGAMENTO INTELIGENTE
    // ============================================================================
    async waitForDynamicContent(page) {
        try {
            await Promise.race([
                page.waitForSelector('footer, nav, a[href]', { timeout: 5000 }),
                page.waitForFunction(() => document.querySelectorAll('a').length > 10, { timeout: 5000 }),
                new Promise(resolve => setTimeout(resolve, 5000))
            ]);
            await this.progressiveScroll(page);
            await page.waitForNetworkIdle({ idleTime: 1000, timeout: 5000 }).catch(() => { });
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        catch (e) {
            console.log('   ⚠️ Timeout em carregamento dinâmico (continuando...)');
        }
    }
    // ============================================================================
    // 🆕 FILTRAGEM INTELIGENTE DE EMAILS
    // ============================================================================
    extractEmails(bodyText) {
        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+[.][a-zA-Z]{2,}/g;
        const emails = bodyText.match(emailRegex) || [];
        const blacklist = [
            'seu@email.com', 'example@example.com', 'user@domain.com',
            'email@exemplo.com', 'seuemail@', 'exemplo@'
        ];
        return [...new Set(emails.filter(email => {
                const lower = email.toLowerCase();
                return !blacklist.some(blocked => lower.includes(blocked)) &&
                    !lower.includes('noreply') &&
                    !lower.includes('no-reply');
            }))];
    }
    // ============================================================================
    // 🆕 EXTRAÇÃO DO DOM RENDERIZADO
    // ============================================================================
    async extractContactInfoFromDOM(page) {
        return await page.evaluate(() => {
            const extractText = (selectors) => {
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent)
                        return el.textContent;
                }
                return '';
            };
            return {
                emails: Array.from(document.querySelectorAll('a[href^="mailto:"]'))
                    .map(a => a.href.replace('mailto:', ''))
                    .filter(e => e && !e.includes('seu@email') && !e.includes('example')),
                phones: Array.from(document.querySelectorAll('a[href^="tel:"], .phone, .telefone, [class*="contato"]'))
                    .map(el => el.textContent ? el.textContent.trim() : '')
                    .filter(t => /[0-9]{8,}/.test(t)),
                cnpjText: extractText(['footer', '.footer', '[class*="rodape"]'])
            };
        });
    }
    // ============================================================================
    // 🆕 SISTEMA DE PONTUAÇÃO
    // ============================================================================
    scoreInstitutionalLink(url, text, context) {
        let score = 0;
        const urlLower = url.toLowerCase();
        const textLower = text.toLowerCase();
        const contextLower = context.toLowerCase();
        const productTerms = ['/produto/', '/p/', '/item/', 'comprar', 'carrinho', '-cm', '-kg'];
        if (productTerms.some(term => urlLower.includes(term)))
            return -10;
        const highPriority = ['contato', 'fale-conosco', 'sobre', 'empresa', 'institucional'];
        if (highPriority.some(term => urlLower.includes(term) || textLower.includes(term)))
            score += 5;
        const mediumPriority = ['privacidade', 'termos', 'politica', 'ajuda', 'faq'];
        if (mediumPriority.some(term => urlLower.includes(term) || textLower.includes(term)))
            score += 3;
        const lowPriority = ['trocas', 'devolucoes', 'envio', 'pagamento', 'carreiras'];
        if (lowPriority.some(term => urlLower.includes(term) || textLower.includes(term)))
            score += 1;
        if (contextLower.includes('footer') || contextLower.includes('institucional'))
            score += 2;
        return score;
    }
    // ============================================================================
    // 🆕 EXTRAÇÃO MELHORADA DE LINKS
    // ============================================================================
    extractInstitutionalLinks(page, baseUrl) {
        return page.evaluate((base) => {
            const links = [];
            const seenUrls = new Set();
            const allLinks = document.querySelectorAll('a[href]');
            allLinks.forEach((el) => {
                const a = el;
                const href = a.getAttribute('href');
                const text = a.innerText.trim();
                if (!href)
                    return;
                try {
                    const absolute = new URL(href, base);
                    if (!seenUrls.has(absolute.href) && !absolute.href.startsWith('javascript:')) {
                        seenUrls.add(absolute.href);
                        const context = a.closest('footer, nav, [class*="institucional"]')?.className || '';
                        links.push({
                            url: absolute.href,
                            text: text || 'Sem texto',
                            context,
                            internal: absolute.origin === new URL(base).origin
                        });
                    }
                }
                catch (err) {
                    // Ignora URLs inválidas
                }
            });
            return links;
        }, baseUrl);
    }
    // --- Métodos Auxiliares (mantidos para compatibilidade) ---
    isInstitutionalLink(url, text) {
        return this.scoreInstitutionalLink(url, text, '') > 0;
    }
    getPageMarkdown($) {
        const mainElement = $('main').length ? $('main') :
            $('article').length ? $('article') :
                $('#content').length ? $('#content') :
                    $('.main, .content, .main-content').first().length ? $('.main, .content, .main-content').first() :
                        $('body');
        const content = mainElement.clone();
        content.find('script, style, nav, footer, header, noscript, iframe, .ads, .popup, .cookie-banner').remove();
        return this.turndownService.turndown(content.html() || '').trim();
    }
    // ============================================================================
    // 🆕 RETRY COM BACKOFF
    // ============================================================================
    async scrapeWithRetry(browser, url, options, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                if (attempt > 1) {
                    console.log(`   🔄 Tentativa ${attempt}/${maxRetries}`);
                }
                const result = await this.internalScrape(browser, url, options);
                if (result.markdown.length < 50) {
                    throw new Error('Conteúdo insuficiente capturado');
                }
                return result;
            }
            catch (error) {
                if (attempt === maxRetries)
                    throw error;
                const delay = Math.pow(2, attempt) * 1000;
                console.log(`   ⏳ Erro: ${error.message}. Aguardando ${delay / 1000}s...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    // ============================================================================
    // 🚀 MÉTODO PRINCIPAL
    // ============================================================================
    async scrapeUrl(url, options) {
        this.visitedUrls.clear();
        const browser = await this.initBrowser();
        const institutionalPages = {};
        const debug = options?.debug || false;
        console.log(`🚀 Iniciando scraping master em: ${url}`);
        const mainPage = await this.scrapeWithRetry(browser, url, options);
        this.visitedUrls.add(url);
        if (debug) {
            console.log('📊 RESULTADO PÁGINA PRINCIPAL:');
            console.log(`  - Markdown: ${mainPage.markdown.length} chars`);
            console.log(`  - Links: ${mainPage.links.length}`);
            console.log(`  - Emails: ${mainPage.contactInfo.emails.join(', ') || 'Nenhum'}`);
        }
        const linksToVisit = mainPage.links
            .filter((link) => link.internal && link.score > 0 && !this.visitedUrls.has(link.url))
            .slice(0, 12);
        console.log(`🔍 Detectados ${linksToVisit.length} links institucionais.`);
        for (const link of linksToVisit) {
            if (this.visitedUrls.has(link.url))
                continue;
            console.log(`\n 📂 [Score: ${link.score}] ${link.text}`);
            console.log(`    ${link.url}`);
            await this.randomDelay(1500, 3500);
            try {
                const subData = await this.scrapeWithRetry(browser, link.url, {
                    ...options,
                    waitUntil: 'domcontentloaded',
                    timeout: 20000
                });
                this.visitedUrls.add(link.url);
                institutionalPages[link.url] = {
                    url: link.url,
                    title: subData.metadata.title,
                    markdown: subData.markdown
                };
                console.log(`    ✅ ${subData.markdown.length} caracteres`);
            }
            catch (err) {
                console.error(`    ❌ ${err.message}`);
            }
        }
        return {
            url: mainPage.url,
            metadata: mainPage.metadata,
            contactInfo: mainPage.contactInfo,
            storeInfo: mainPage.storeInfo,
            institutionalPages,
            stats: {
                pagesScraped: this.visitedUrls.size,
                totalInstitutional: Object.keys(institutionalPages).length
            }
        };
    }
    // ============================================================================
    // 🛠️ SCRAPING INTERNO
    // ============================================================================
    async internalScrape(browser, url, options) {
        const page = await browser.newPage();
        try {
            // Remove sinais de automação
            // Injeta o polyfill como string para evitar que o próprio transpiler (tsx/esbuild) precise dele
            await page.evaluateOnNewDocument('window.__name = (t, v) => Object.defineProperty(t, "name", { value: v, configurable: true });');
            await page.evaluateOnNewDocument(() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
            });
            await this.configurePage(page);
            await page.goto(url, {
                waitUntil: options?.waitUntil || 'networkidle2',
                timeout: options?.timeout || 30000
            });
            await this.waitForDynamicContent(page);
            const html = await page.content();
            const $ = cheerio.load(html);
            const domData = await this.extractContactInfoFromDOM(page);
            const dynamicLinks = await this.extractInstitutionalLinks(page, url);
            const baseUrlObj = new URL(url);
            const allLinks = [];
            dynamicLinks.forEach((link) => {
                const score = this.scoreInstitutionalLink(link.url, link.text, link.context);
                allLinks.push({
                    url: link.url,
                    text: link.text,
                    score,
                    internal: link.internal
                });
            });
            const bodyText = await page.evaluate(() => document.body.innerText);
            const cheerioEmails = this.extractEmails(bodyText);
            const allEmails = [...new Set([...cheerioEmails, ...domData.emails])];
            const cnpjMatch = (bodyText + domData.cnpjText).match(/[0-9]{2}[.]?[0-9]{3}[.]?[0-9]{3}[/]?[0-9]{4}[-/]?[0-9]{2}/);
            return {
                url,
                markdown: this.getPageMarkdown($),
                metadata: {
                    title: $('title').text().trim(),
                    description: $('meta[name="description"]').attr('content') || '',
                    siteName: $('meta[property="og:site_name"]').attr('content') || ''
                },
                contactInfo: {
                    emails: allEmails,
                    phones: [...new Set([
                            ...domData.phones,
                            ...(bodyText.match(/[(]?[0-9]{2}[)]?\s?[0-9]{4,5}[-\s]?[0-9]{4}/g) || [])
                        ])],
                    socialMedia: this.extractSocialMedia($),
                    addresses: [],
                    contactLinks: allLinks.filter(l => l.score > 0)
                },
                storeInfo: {
                    cnpj: cnpjMatch?.[0],
                    name: $('meta[property="og:site_name"]').attr('content') || $('title').text().split('|')[0].trim()
                },
                links: allLinks
            };
        }
        finally {
            await page.close();
        }
    }
    // Extrai redes sociais
    extractSocialMedia($) {
        const social = {};
        $('a[href]').each((i, el) => {
            const href = $(el).attr('href') || '';
            if (href.includes('facebook.com/') && !social.facebook)
                social.facebook = href;
            else if (href.includes('instagram.com/') && !social.instagram)
                social.instagram = href;
            else if ((href.includes('twitter.com/') || href.includes('x.com/')) && !social.twitter)
                social.twitter = href;
            else if (href.includes('linkedin.com/') && !social.linkedin)
                social.linkedin = href;
            else if (href.includes('youtube.com/') && !social.youtube)
                social.youtube = href;
            else if ((href.includes('wa.me/') || href.includes('whatsapp.com/') || href.includes('api.whatsapp.com')) && !social.whatsapp)
                social.whatsapp = href;
        });
        return social;
    }
    // Browser Management
    findChromeExecutable() {
        const paths = [
            process.env.PUPPETEER_CACHE_DIR ? `${process.env.PUPPETEER_CACHE_DIR}/chrome` : null,
            '/usr/bin/google-chrome-stable',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        ].filter(Boolean);
        for (const p of paths) {
            if (fs.existsSync(p))
                return p;
        }
        return undefined;
    }
    async initBrowser() {
        if (!this.browser) {
            this.browser = await puppeteer.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--window-size=1920,1080',
                    '--start-maximized'
                ],
                executablePath: this.findChromeExecutable()
            });
        }
        return this.browser;
    }
    async closeBrowser() {
        if (this.browser) {
            await this.browser.close();
            this.browser = null;
        }
    }
}
export const scraperService = new WebScraperService();
