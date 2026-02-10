import requests 
from bs4 import BeautifulSoup 
import markdownify 
import os 
from datetime import datetime 
from playwright.sync_api import sync_playwright 
from extrair_informacoes import extrair_informacoes_estruturadas
import json # Trabalhar com json (contexto atual: Converter um objeto json para string)

def scrape_request(url):
    """
    Faz scraping de uma URL usando request
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        } #AppleKit = motor de navegador apple (incluido para funfar e ser compativel em sites da apple)
        resposta = requests.get(url, headers=headers, timeout=10)
        resposta.raise_for_status()

        html = resposta.text
        
        # verifica tamanho E conteúdo real (validando o html puro com css e js)
        if len(html) < 500:
            return False, None
            
        # detecta se tem muito pouco texto
        html_organizado = BeautifulSoup(html, 'html.parser') 
        texto = html_organizado.get_text(strip=True) #strip=True Remove espaços em brancos e quebras de linhas
        
        if len(texto) < 200: 
            print("⚠️  Pouco conteúdo detectado (provável estrutura clientSide)")
            return False, None
        
        return True, html 
        
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
            ) #Chromiun = navegador de busca open source usado como base no chrome
            pagina = navegador.new_page()
            
            pagina.goto(url, wait_until='networkidle', timeout=30000) #30s
            
            pagina.wait_for_timeout(2000) #2s
            
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

def salvar(conteudo, nome_arquivo, nome_pasta= "resultados"):
    """
    Salva conteudo em um arquivo local
    """
    pasta = nome_pasta
    os.makedirs(pasta, exist_ok=True) 
    nome_recebido = nome_arquivo
    
    if nome_recebido is None:
        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        arquivo = os.path.join(pasta, f'{timestamp}.md')
    else:
        arquivo = os.path.join(pasta, f'{nome_arquivo}.md') 

    with open(arquivo, 'w', encoding='utf-8') as f:
        #isInstance = Verifica se o objeto é de um tipo especifico (valida se o conteúdo é um dicionário)
        if isinstance(conteudo, dict):
            f.write(json.dumps(conteudo, indent=2, ensure_ascii=False)) #Converte json em string, indentação de 2, tratamento utf-8
        else:
            f.write(conteudo)
    print(f"✅ Salvo em '{arquivo}'")

def processar(url):
    print("🔍 Tentando com Requests ...")
    status, html = scrape_request(url)

    if not status or html is None:
        print("⚠️ Falha no Request , usando Playwright...")
        status, html = scrape_playwright(url)
        
        if not status or html is None:
            print("⚠️ Falha playwright")
            return False, None
    else:
        print("✅ Sucesso com raspagem!")

        print("🔄️ Tentando capturar informações SOBRE a página")

        informacoes_da_pagina = extrair_informacoes_estruturadas(html)
    
    return True, html, informacoes_da_pagina

if __name__ == "__main__":
    print("=== Web Scraper para Markdown ===\n")
    
    url = input("Digite a URL da página: ")
    
    print("\nProcessando...\n")
    status, html_processado, informacoes_da_pagina = processar(url)
    
    if status and html_processado:
        print("\n=== RESULTADO EM MARKDOWN ===\n")
        markdown = html_para_markdown(html_processado)
        print(markdown)

        print("\n=== INFORMAÇÕES DA PÁGINA CAPTURADAS ===\n")
        print(informacoes_da_pagina)
        
        # Salvar em arquivo (opcional)
        salvar_arquivo = input("\nDeseja salvar em arquivo? (s/n): ")
        if salvar_arquivo.lower() == 's':
            salvar(conteudo=markdown, nome_arquivo=None)
            salvar(conteudo=informacoes_da_pagina, nome_arquivo="informacoes")
    else:
        print("❌ Erro não foi possível raspar a página!")