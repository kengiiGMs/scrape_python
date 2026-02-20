from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.scrape_playwright import iniciar_playwright
from scrapers.scrape_request import iniciar_request

def processar_scrape_completo(url):
    print("🔍 Tentando com Requests ...")
    status, html = iniciar_request(url)

    if not status or html is None:
        print("⚠️ Falha no Request , usando Playwright...")
        status, html = iniciar_playwright(url)
        if not status or html is None:
            print("⚠️ Falha playwright")
            return False, None

    print("✅ Sucesso com raspagem!")

    # Adiciona a página principal como a primeira da lista
    paginas = [{
        'link': {'texto': 'Página Principal', 'url': url},
        'html': html,
        'status': True
    }]

    print("🔄️ Capturando links das páginas")
    html_formatado = BeautifulSoup(html, 'html.parser')

    links_http = []
    urls_vistas = {url}
    if url.endswith('/'):
        urls_vistas.add(url[:-1])
    else:
        urls_vistas.add(url + '/')

    termos_ignorados = ['facebook', 'whatsapp', 'instagram', 'youtube', 'twitter', 'x.com', 'pinterest', 'wa.me', 'linkedin']

    header = html_formatado.find('header')
    footer = html_formatado.find('footer')
    links_a = []
    if header:
        links_header = header.find_all('a', href=True)
        if links_header:
            print("🔄️ Capturando links no header")
            links_a = links_header
    if not links_a and footer:
        links_footer = footer.find_all('a', href=True)
        if links_footer:
            print("🔄️ Capturando links no footer")
            links_a = links_footer
    if not links_a:
        print("🔄️ Erro no header e no footer ou nenhum link encontrado, Capturando links da pagina toda!")
        links_a = html_formatado.find_all('a', href=True)

    for link in links_a:
        if len(links_http) >= 20:
            break
        href = link['href']
        # Ignora links que contenham '#'
        if '#' in href:
            continue
        url_completa = urljoin(url, href)
        # Filtra apenas URLs que começam com http ou https
        if url_completa.startswith(('http://', 'https://')):
            url_lower = url_completa.lower()
            if any(termo in url_lower for termo in termos_ignorados):
                continue
            if url_completa not in urls_vistas:
                urls_vistas.add(url_completa)
                links_http.append({
                    'texto': link.get_text().strip(),
                    'url': url_completa
                })
                print(f"{link.get_text()}: {url_completa}")

    print('\n🔄️ Iniciando Scrape dos links das páginas coletadas\n')

    for link in links_http:
        print(f"Iniciando scrape do link {link['texto']}")
        print("🔍 Tentando com Requests ...")
        status, html = iniciar_request(link['url'])

        if not status or html is None:
            print("⚠️ Falha no Request , usando Playwright...")
            status, html = iniciar_playwright(link['url'])
            if not status or html is None:
                print("⚠️ Falha playwright")
                paginas.append({'link': link, 'html': None, 'status': False})
                continue

        print("✅ Sucesso com raspagem!")

        paginas.append({
            'link': link,
            'html': html,
            'status': True
        })

        print(f"⚠️ Finalizando procedimento de scrape para o link: {link['texto']}\n")

    return True, paginas