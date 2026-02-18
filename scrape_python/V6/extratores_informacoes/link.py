def extrair_links(html_formatado):
    """Extrai todos os links da página"""
    links = []
    for a in html_formatado.find_all('a', href=True):
        links.append(a['href'])
    return links