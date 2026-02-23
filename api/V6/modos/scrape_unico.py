from scrapers.scrape_playwright import iniciar_playwright
from scrapers.scrape_request import iniciar_request

def processar_scrape_unico(url):
    print("🔍 Tentando com Requests ...")
    status, html = iniciar_request(url)

    if not status or html is None:
        print("⚠️ Falha no Request , usando Playwright...")
        status, html = iniciar_playwright(url)
        
        if not status or html is None:
            print("⚠️ Falha playwright")
            return False, None, None
    
    paginas = [{
        'link': {'texto': 'Página Principal', 'url': url},
        'html': html,
        'status': True
    }]
    print("✅ Sucesso com raspagem!")

    print("🔄️ Tentando capturar informações SOBRE a página")

    return True, paginas[0]