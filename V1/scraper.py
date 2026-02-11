import requests # Fazer as requisição HTTP (como um navegador)
from bs4 import BeautifulSoup # Parse do html buscado (html bagunçado em algo organizado)
import markdownify # Transformar em markdown (converter para markdown)
import os #Interage com o sistema operacional, gerenciar arquivos e pastas
from datetime import datetime #Trabalhar com datas e horas

def scrape_markdown(url):
    """
    Faz scraping de uma URL e converte para Markdown
    """
    try:
        # Faz a requisição HTTP
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'} #Passa script no header para evitar o bloqueio da requisição (tipo uma mascara que diz que é um navegador firefox windows SO 64 e não um script python)
        html = requests.get(url, headers=headers)
        html.raise_for_status() # Verifica o status, se dar erro ja cai exception
        #print(html.text)         # (HTML puro)
        # Parse do HTML
        html_organizado = BeautifulSoup(html.content, 'html.parser') # Transforma o html bagunçado em algo organizado
   
        # Converte para Markdown
        markdown = markdownify.markdownify(
            str(html_organizado), 
            heading_style="ATX"
        ) # Converte o html em string e depois para markdown (o heading_style significa que os titulos serão # em vez de sublinhados) 
        
        return markdown
        
    except requests.exceptions.RequestException as e:
        return f"Erro ao acessar a URL: {e}"
    except Exception as e:
        return f"Erro ao processar: {e}"

# Programa principal (se tiver executando esse arquivo diretamente executa o código abaixo)
if __name__ == "__main__":
    print("=== Web Scraper para Markdown ===\n")
    
    url = input("Digite a URL da página: ")
    
    print("\nProcessando...\n")
    resultado = scrape_markdown(url)
    
    print("=== RESULTADO EM MARKDOWN ===\n")
    print(resultado)
    
    # Salvar em arquivo (opcional)
    salvar = input("\nDeseja salvar em arquivo? (s/n): ")
    if salvar.lower() == 's':
        pasta = 'resultados' #Pasta

        os.makedirs(pasta, exist_ok=True) #Cria pasta se ela não existir (os.makedirs)

        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S') #Pegar data, hora atual para gerar o nome do arquivo

        arquivo = os.path.join(pasta, f'{timestamp}.md') # caminho completo do arquivo (os.path.join junta os componentes, gerando o caminho compativel com windows)

        with open(arquivo, 'w', encoding='utf-8') as f:
            # abre o arquivo em modo de escrita 'w' + with garante que o arquivo sera fechado automaticamente
            f.write(resultado)
        print(f"Salvo em '{arquivo}'")
