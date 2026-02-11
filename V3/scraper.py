import requests 
from bs4 import BeautifulSoup 
import markdownify 
import os 
from datetime import datetime 
from playwright.sync_api import sync_playwright 


def scrape_request(url):
    """
    Faz scraping de uma URL usando request
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        } 
        resposta = requests.get(url, headers=headers, timeout=10)
        resposta.raise_for_status()

        html = resposta.text
        
        # ✅ Verifica tamanho E conteúdo real
        if len(html) < 500:
            return False, None
            
        # ✅ Detecta se tem muito pouco texto (sinal de SPA)
        soup = BeautifulSoup(html, 'html.parser')
        texto = soup.get_text(strip=True)
        
        if len(texto) < 200:  # Muito pouco texto = precisa JS
            print("⚠️  Pouco conteúdo detectado (provável SPA)")
            return False, None
        
        return True, html  # ✅ Retorna string, não bytes
        
    except Exception as e:
        print(f"❌ Request falhou: {e}")
        return False, None


def scrape_playwright(url):
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
            
            # ✅ Espera carregar completamente
            pagina.goto(url, wait_until='networkidle', timeout=30000)
            
            # ✅ Aguarda mais um pouco para JS executar
            pagina.wait_for_timeout(2000)
            
            conteudo_html = pagina.content()

        return True, conteudo_html

    except Exception as e:
        print(f"❌ Playwright falhou: {e}")
        return False, None


def html_para_markdown(html):
    """
    Converte conteudo html para markdown
    """
    html_organizado = BeautifulSoup(html, 'html.parser')

    markdown = markdownify.markdownify(
        str(html_organizado),
        heading_style="ATX"
    )

    return markdown


def salvar_markdown(markdown):
    """
    Salva conteudo markdown em um arquivo local
    """
    pasta = 'resultados'
    os.makedirs(pasta, exist_ok=True) 
    timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S') 
    arquivo = os.path.join(pasta, f'{timestamp}.md') 

    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"✅ Salvo em '{arquivo}'")


def processar(url):
    print("🔍 Tentando com Requests (rápido)...")
    status, html = scrape_request(url)

    if not status or html is None:
        print("⚠️  Request insuficiente, usando Playwright...")
        status, html = scrape_playwright(url)
        
        if not status or html is None:
            print("❌ Falhou playwright")
            return False, None
    else:
        print("✅ Sucesso com Requests!")
    
    return True, html


if __name__ == "__main__":
    print("=== Web Scraper para Markdown ===\n")
    
    url = input("Digite a URL da página: ")
    
    print("\nProcessando...\n")
    status, html_processado = processar(url)
    
    if status and html_processado:
        print("\n=== RESULTADO EM MARKDOWN ===\n")
        markdown = html_para_markdown(html_processado)
        print(markdown)
        
        # Salvar em arquivo (opcional)
        salvar = input("\nDeseja salvar em arquivo? (s/n): ")
        if salvar.lower() == 's':
            salvar_markdown(markdown)
    else:
        print("❌ Erro: Não foi possível raspar a página!")
