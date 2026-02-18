from bs4 import BeautifulSoup 
from extratores_informacoes.cnpj import extrair_cnpj
from extratores_informacoes.formas_pagamento import extrair_formas_pagamento
from extratores_informacoes.link import extrair_links
from extratores_informacoes.metadados import extrair_metadados
from extratores_informacoes.redes_sociais import extrair_redes_sociais

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
