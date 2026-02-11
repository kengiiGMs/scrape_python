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
            formas.append(keyword) 
    
    for img in html_formatado.find_all('img', alt=True):
        alt = img['alt'].lower()
        for keyword in keywords:
            if keyword in alt and keyword not in formas:
                formas.append(keyword)
    
    return list(set(formas))