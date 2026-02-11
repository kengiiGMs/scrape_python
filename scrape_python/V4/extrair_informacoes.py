from bs4 import BeautifulSoup 
import re

def extrair_links(html_formatado):
    """Extrai todos os links da página"""
    links = []
    for a in html_formatado.find_all('a', href=True):
        links.append(a['href'])
    return links

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
    
    # Busca em todos os links
    # Busca todos os componentes a que tem href
    for a in html_formatado.find_all('a', href=True):
        url = a['href'] # Pega apenas o href do link
        # Verifica se ta dentro da lista de padrões
        for rede, padrao in padroes.items():
            #Se tiver bota dentro do array redes
            if re.search(padrao, url, re.I):
                redes[rede].append(url)
    #dict comprehension remove as chaves que ficaram vazias, retornando apenas os que tem itens
    return {k: v for k, v in redes.items() if v} 

def validar_cnpj(cnpj):
    """Valida CNPJ usando dígitos verificadores"""
    # Remove pontuação
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj_limpo) != 14:
        return False
    
    # Rejeita CNPJs com todos dígitos iguais
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False
    
    # Converte para lista de inteiros
    cnpj_numeros = [int(d) for d in cnpj_limpo]
    
    # Calcula primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(cnpj_numeros[i] * pesos1[i] for i in range(12))
    digito1 = 0 if (soma1 % 11) < 2 else 11 - (soma1 % 11)
    
    if digito1 != cnpj_numeros[12]:
        return False
    
    # Calcula segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(cnpj_numeros[i] * pesos2[i] for i in range(13))
    digito2 = 0 if (soma2 % 11) < 2 else 11 - (soma2 % 11)
    
    return digito2 == cnpj_numeros[13]

def extrair_cnpj(html_formatado):
    """Extrai CNPJ da página COM validação"""
    texto = html_formatado.get_text()
    padrao = r'\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}'
    cnpjs_encontrados = re.findall(padrao, texto) # Retorna todos os textos que seguem o padrao
    
    # ✅ Filtra apenas CNPJs válidos
    cnpjs_validos = [cnpj for cnpj in cnpjs_encontrados if validar_cnpj(cnpj)]
    
    return cnpjs_validos

def extrair_formas_pagamento(html_formatado):
    """Extrai formas de pagamento mencionadas"""
    formas = []
    keywords = [
        'pix', 'boleto', 'cartão de crédito', 'cartão de débito',
        'visa', 'mastercard', 'elo', 'american express',
        'paypal', 'mercado pago', 'pagseguro', 'crédito', 'débito'
    ]
    
    texto = html_formatado.get_text().lower()
    
    for keyword in keywords:
        if keyword in texto:
            formas.append(keyword) # Se tiver algum keyword no texto bota dentro do array
    
    # Também busca por classes/alt de imagens
    for img in html_formatado.find_all('img', alt=True):
        alt = img['alt'].lower()
        for keyword in keywords:
            if keyword in alt and keyword not in formas:
                formas.append(keyword)
    
    return list(set(formas))  # Remove duplicatas

def extrair_metadados(html_formatado):
    """Extrai title e metadados relevantes"""
    dados = {}
    
    # Title da página
    if html_formatado.title:
        dados['title'] = html_formatado.title.string
    
    # Meta tags importantes
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


def extrair_informacoes_estruturadas(html):
    """
    Extrai informações estruturadas do HTML já capturado
    """
    html_formatado = BeautifulSoup(html, 'html.parser')
    
    resultado = {
        'metadados': extrair_metadados(html_formatado),
        'links': extrair_links(html_formatado),
        'redes_sociais': extrair_redes_sociais(html_formatado),
        'cnpj': extrair_cnpj(html_formatado),
        'formas_pagamento': extrair_formas_pagamento(html_formatado),
    }
    
    return resultado
