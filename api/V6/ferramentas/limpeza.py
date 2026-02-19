import re

def limpar_markdown(texto):
    """
    Realiza a limpeza do texto markdown:
    1. Remove imagens (incluindo base64).
    2. Remove links (mantendo apenas o texto âncora).
    3. Remove linhas vazias excessivas.
    """
    if not texto:
        return ""

    # 1. Remover imagens: ![alt](url)
    # Explicação regex: 
    # !\[.*?\] -> Começa com !, seguido de [qualquer coisa] (lazy)
    # \(.*?\) -> Seguido de (qualquer coisa) (lazy) - isso pega a URL/base64
    texto = re.sub(r'!\[.*?\]\(.*?\)', '', texto, flags=re.DOTALL)

    # 2. Remover links: [texto](url) -> texto
    # Explicação regex:
    # \[([^\]]+)\] -> Captura o texto âncora dentro de []
    # \([^\)]+\) -> Ignora a parte da URL dentro de ()
    texto = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)

    # 3. Remover linhas vazias excessivas
    # Substitui 3 ou mais quebras de linha por apenas 2
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    
    # Remover espaços em branco no início e fim
    return texto.strip()
