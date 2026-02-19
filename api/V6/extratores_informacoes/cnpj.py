import re #manipular padrões de texto em strings

def validar_cnpj(cnpj):
    """Valida CNPJ usando dígitos verificadores"""
    cnpj_limpo = re.sub(r'\D', '', cnpj)

    if len(cnpj_limpo) != 14:
        return False
    
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False
    
    cnpj_numeros = [int(d) for d in cnpj_limpo]
    
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(cnpj_numeros[i] * pesos1[i] for i in range(12))
    digito1 = 0 if (soma1 % 11) < 2 else 11 - (soma1 % 11)
    
    if digito1 != cnpj_numeros[12]:
        return False
    
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(cnpj_numeros[i] * pesos2[i] for i in range(13))
    digito2 = 0 if (soma2 % 11) < 2 else 11 - (soma2 % 11)
    
    return digito2 == cnpj_numeros[13]

def extrair_cnpj(html_formatado):
    """Extrai CNPJ da página COM validação"""
    texto = html_formatado.get_text()
    padrao = r'\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}'
    cnpjs_encontrados = re.findall(padrao, texto) 
    
    cnpjs_validos = [cnpj for cnpj in cnpjs_encontrados if validar_cnpj(cnpj)]
    
    return cnpjs_validos
