def extrair_metadados(html_formatado):
    """Extrai title e metadados relevantes"""
    dados = {}
    
    if html_formatado.title:
        dados['title'] = html_formatado.title.string
    
    metas = {
        'description': html_formatado.find('meta', attrs={'name': 'description'}),
        'keywords': html_formatado.find('meta', attrs={'name': 'keywords'}),
        'og:title': html_formatado.find('meta', property='og:title'),
        'og:description': html_formatado.find('meta', property='og:description'),
    }
    
    for key, meta in metas.items():
        if meta and meta.get('content'):
            dados[key] = meta['content']
    
    return dados