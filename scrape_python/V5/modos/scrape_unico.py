from scrapers.scrape_playwright import iniciar_playwright
from scrapers.scrape_request import iniciar_request
from extratores_informacoes.main import extrair_informacoes_estruturadas
from ferramentas.nome_arquivo import gerar_nome_arquivo_da_url

def processar_scrape_unico(url):
    print("🔍 Tentando com Requests ...")
    status, html = iniciar_request(url)

    if not status or html is None:
        print("⚠️ Falha no Request , usando Playwright...")
        status, html = iniciar_playwright(url)
        
        if not status or html is None:
            print("⚠️ Falha playwright")
            return False, None, None, None
    
    print("✅ Sucesso com raspagem!")

    print("🔄️ Tentando capturar informações SOBRE a página")

    informacoes_da_pagina = extrair_informacoes_estruturadas(html)
    nome_arquivo_gerado = gerar_nome_arquivo_da_url(url)
    
    
    return True, html, informacoes_da_pagina, nome_arquivo_gerado