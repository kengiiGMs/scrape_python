
import markdownify 
from bs4 import BeautifulSoup

def html_para_markdown(html):
    """
    Converte conteudo html para markdown
    """
    html_organizado = BeautifulSoup(html, 'html.parser')
    # Extrai apenas o conteúdo da tag <main>, se existir
    main_tag = html_organizado.find('main')
    if main_tag:
        html_organizado = main_tag
    # Remove todas as tags <a> (links)
    for a in html_organizado.find_all('a'):
        a.unwrap()
    # Não é mais necessário remover header/footer, pois só o <main> será usado

    try:
        markdown = markdownify.markdownify(
            str(html_organizado),
            heading_style="ATX"
        )
        return markdown
    except RecursionError:
        return "[ERRO: RecursionError ao converter HTML para Markdown]"
    except Exception as e:
        return f"[ERRO ao converter HTML para Markdown: {e}]"
