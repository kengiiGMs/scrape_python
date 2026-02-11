from playwright.sync_api import sync_playwright 

def iniciar_playwright(url):
    """
    Faz scraping de uma URL usando Playwright
    """
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            pagina = navegador.new_page()
            
            pagina.goto(url, wait_until='networkidle', timeout=30000) #30s
            
            pagina.wait_for_timeout(2000) #2s
            
            conteudo_html = pagina.content()

        return True, conteudo_html

    except Exception as e:
        print(f"❌ Playwright falhou: {e}")
        return False, None