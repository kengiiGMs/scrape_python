
import markdownify 
from bs4 import BeautifulSoup

def html_para_markdown(html):
    """
    Converte conteudo html para markdown
    """
    html_organizado = BeautifulSoup(html, 'html.parser')

    markdown = markdownify.markdownify(
        str(html_organizado),
        heading_style="ATX"
    )

    return markdown
