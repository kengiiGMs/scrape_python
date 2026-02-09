from playwright.sync_api import sync_playwright # Automação de navegador para lidar com JavaScript
from bs4 import BeautifulSoup # Parse do html buscado (html bagunçado em algo organizado)
import markdownify # Transformar em markdown (converter para markdown)
import os # Interage com o sistema operacional, gerenciar arquivos e pastas
from datetime import datetime # Trabalhar com datas e horas

def scrape_markdown(url):
    """
    Faz scraping de uma URL e converte para Markdown usando Playwright
    """
    try:
        # Inicia o Playwright não o navegador (with = fecha tudo automaticamente) 
        with sync_playwright() as p:

            browser = p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled']) # Inicia o navegador em modo headless (true = sem interface visual, só no back) args é algo para falar que não é um robo

            page = browser.new_page()# Criando uma página nova

            page.goto(url, wait_until='networkidle')  #.goto = Navega até a página e wait_util=networkindle,  wait_until = até quando esperar para ter a pagina como carregada? (networkindle = até o JavaScript/Ajax ter carregado, load = padrão, domcontentload = css e html)

            page.click('#onetrust-accept-btn-handler')

            #REMOVER A MODAL
            page.evaluate('''
                const modal = document.querySelector('#onetrust-consent-sdk');
                if (modal) modal.remove();
                document.body.style.overflow = 'auto';
            ''')

            html_content = page.content() # Pega o HTML completo já renderizado com JavaScript

            # Fecha o navegador
            browser.close()

        # Parse do HTML
        html_organizado = BeautifulSoup(html_content, 'html.parser')

        # Converte para Markdown
        markdown = markdownify.markdownify(
            str(html_organizado),
            heading_style="ATX"
        )

        return markdown

    except Exception as e:
        return f"Erro ao processar: {e}"

# Programa principal (se tiver executando esse arquivo diretamente executa o código abaixo)
if __name__ == "__main__":
    print("=== Web Scraper para Markdown (com Playwright) ===\n")

    url = input("Digite a URL da página: ")

    print("\nProcessando...\n")

    resultado = scrape_markdown(url)

    print("=== RESULTADO EM MARKDOWN ===\n")
    print(resultado)

    # Salvar em arquivo (opcional)
    salvar = input("\nDeseja salvar em arquivo? (s/n): ")

    if salvar.lower() == 's':
        pasta = 'resultados'
        os.makedirs(pasta, exist_ok=True)

        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        arquivo = os.path.join(pasta, f'{timestamp}.md')

        # f é um objeto(o arquivo) vem da função open 
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(resultado) # f é o arquivo e escrevemos nele

        print(f"Salvo em '{arquivo}'")