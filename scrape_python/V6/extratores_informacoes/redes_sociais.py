import re

def extrair_redes_sociais(html_formatado):
    """Extrai links de redes sociais"""
    redes = {
        'instagram': [],
        'facebook': [],
        'linkedin': [],
        'twitter': [],
        'youtube': []
    }
    
    # Padrões de URLs comuns
    padroes = {
        'instagram': r'instagram\.com/[\w\.]+',
        'facebook': r'facebook\.com/[\w\.]+',
        'linkedin': r'linkedin\.com/(company|in)/[\w\-]+',
        'twitter': r'(twitter|x)\.com/[\w]+',
        'youtube': r'youtube\.com/(c|channel|user)/[\w\-]+'
    }
    
    for a in html_formatado.find_all('a', href=True):
        url = a['href'] 

        for rede, padrao in padroes.items():
            if re.search(padrao, url, re.I):
                redes[rede].append(url)
    
    return {k: v for k, v in redes.items() if v} 