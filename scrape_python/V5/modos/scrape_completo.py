from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.scrape_playwright import iniciar_playwright
from scrapers.scrape_request import iniciar_request
from extratores_informacoes.main import extrair_informacoes_estruturadas
from ferramentas.nome_arquivo import gerar_nome_arquivo_da_url


def processar_scrape_completo(url):
    palavras = ['sobre', 'pagamento', 'garantia', 'contato', 'empresa', 
            'about', 'payment', 'contact', 'warranty', 'troca']
    
    print("🔍 Tentando com Requests ...")
    status, html = iniciar_request(url)

    if not status or html is None:
        print("⚠️ Falha no Request , usando Playwright...")
        status, html = iniciar_playwright(url)
        
        if not status or html is None:
            print("⚠️ Falha playwright")
            return False, None
    
    print("✅ Sucesso com raspagem!")

    print("🔄️ Capturando links das páginas")
    html_formatado = BeautifulSoup(html, 'html.parser')

    links_http = []

    urls_vistas = set() 
    
    for link in html_formatado.find_all('a', href=True):
        url_completa = urljoin(url, link['href'])
        
        # Filtra apenas URLs que começam com http ou https
        if url_completa.startswith(('http://', 'https://')):
             if url_completa not in urls_vistas:
                if any(palavra in url_completa.lower() for palavra in palavras):
                    urls_vistas.add(url_completa)
                    links_http.append({
                        'texto': link.get_text().strip(),
                        'url': url_completa
                    })
                    print(f"{link.get_text()}: {url_completa}")
    print('\n🔄️ Iniciando Scrape dos links das páginas coletadas\n')
    paginas = []

    for link in links_http:
        print(f"Iniciando scrape do link {link['texto']}")
        print("🔍 Tentando com Requests ...")
        status, html = iniciar_request(link['url'])

        if not status or html is None:
            print("⚠️ Falha no Request , usando Playwright...")
            status, html = iniciar_playwright(link['url'])
            
            if not status or html is None:
                print("⚠️ Falha playwright")
                paginas.append({'link': link, 'html': None, 'extrair_informacoes_estruturadas': None})
                continue
        
        print("✅ Sucesso com raspagem!")
        
        print("🔄️ Tentando capturar informações SOBRE a página")

        informacoes_da_pagina = extrair_informacoes_estruturadas(html)
        nome_arquivo_gerado = gerar_nome_arquivo_da_url(link['url'])

        paginas.append({'link': link, 'html': html, 'extrair_informacoes_estruturadas': informacoes_da_pagina, 'nome': nome_arquivo_gerado})

        print(f"⚠️ Finalizando procedimento de scrape para o link: {link['texto']}\n")
        
    return True, paginas