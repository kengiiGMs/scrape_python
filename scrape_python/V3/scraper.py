import requests 
from bs4 import BeautifulSoup 
import markdownify 
import os 
from datetime import datetime 
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import re
import uuid 


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
        
        # Verifica tamanho E conteudo real
        if len(html) < 500:
            return False, None
            
        # Detecta se tem muito pouco texto (sinal de SPA)
        soup = BeautifulSoup(html, 'html.parser')
        texto = soup.get_text(strip=True)
        
        if len(texto) < 200:  # Muito pouco texto = precisa JS
            print("[AVISO] Pouco conteudo detectado (provavel SPA)")
            return False, None
        
        return True, html
        
    except Exception as e:
        print(f"[ERRO] Request falhou: {e}")
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
            
            # Espera carregar completamente
            pagina.goto(url, wait_until='networkidle', timeout=30000)
            
            # Aguarda mais um pouco para JS executar
            pagina.wait_for_timeout(2000)
            
            conteudo_html = pagina.content()

        return True, conteudo_html

    except Exception as e:
        print(f"[ERRO] Playwright falhou: {e}")
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


def sanitizar_dominio(url):
    """
    Extrai e sanitiza dominio da URL para nome de arquivo
    """
    parsed = urlparse(url)
    dominio = parsed.netloc or parsed.path
    # Remove www. e sanitiza caracteres
    dominio = re.sub(r'^www\.', '', dominio)
    dominio = re.sub(r'[^\w\-]', '-', dominio)
    return dominio.strip('-')


def salvar_markdown_nomeado(markdown, url, pasta_destino=None):
    """
    Salva markdown com nome padronizado: dominio_YYYY-MM-DD_sufixo.md
    Retorna (caminho_completo, nome_arquivo_sem_extensao)
    """
    if pasta_destino is None:
        pasta_destino = 'resultados'
    
    os.makedirs(pasta_destino, exist_ok=True)
    
    dominio = sanitizar_dominio(url)
    data = datetime.now().strftime('%Y-%m-%d')
    sufixo = str(uuid.uuid4())[:8]
    nome_arquivo = f'{dominio}_{data}_{sufixo}'
    caminho = os.path.join(pasta_destino, f'{nome_arquivo}.md')
    
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"[OK] Salvo em '{caminho}'")
    return caminho, nome_arquivo


def salvar_markdown(markdown):
    """
    Salva conteudo markdown em um arquivo local (formato legado timestamp)
    """
    pasta = 'resultados'
    os.makedirs(pasta, exist_ok=True) 
    timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S') 
    arquivo = os.path.join(pasta, f'{timestamp}.md') 

    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"[OK] Salvo em '{arquivo}'")


def processar(url):
    print("[1] Tentando com Requests (rapido)...")
    status, html = scrape_request(url)

    if not status or html is None:
        print("[AVISO] Request insuficiente, usando Playwright...")
        status, html = scrape_playwright(url)
        
        if not status or html is None:
            print("[ERRO] Falhou playwright")
            return False, None
    else:
        print("[OK] Sucesso com Requests!")
    
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
        print("[ERRO] Nao foi possivel raspar a pagina!")
