from urllib.parse import urlparse

def gerar_nome_arquivo_da_url(url):
    """
    Gera nome de arquivo baseado na URL
    """
    parsed = urlparse(url)
    
    # Extrai o domínio sem subdomínios (www, etc)
    dominio = parsed.netloc.replace('www.', '').split('.')[0]
    
    # Extrai o path e limpa
    path = parsed.path.strip('/').replace('/', '_')
    
    # Se não houver path, usa apenas o domínio
    if not path:
        return dominio
    
    # Combina domínio + path
    nome_arquivo = f"{dominio}_{path}"
    
    # Remove caracteres especiais e limita tamanho
    nome_arquivo = "".join(c for c in nome_arquivo if c.isalnum() or c in ('_', '-'))
    
    return nome_arquivo
