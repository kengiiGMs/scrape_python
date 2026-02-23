from modos.scrape_unico import processar_scrape_unico
from modos.scrape_completo import processar_scrape_completo
from ferramentas.converter import html_para_markdown
from ferramentas.salvamento import salvar_arquivo_local
from ferramentas.nome_arquivo import gerar_nome_arquivo_da_url
from ferramentas.limpeza import limpar_markdown
import json

if __name__ == "__main__":
    print("=== Web Scraper para Markdown ===\n")

    url = input("Digite a URL da página: ")
    
    print("=== Oque deseja fazer com essa URL? ===\n")
    modo = int(input("Digite 1 - Para o scrape de uma página única\nDigite 2 - Para o scrape de várias páginas\nEscolha: "))
    
    print("\nProcessando...\n")
    while modo != 9:
        match modo:
            case 1:
                status, html_processado = processar_scrape_unico(url)
            
                if status and html_processado:
                    conteudo_bruto = html_para_markdown(html_processado['html'])
                    conteudo_pagina = limpar_markdown(conteudo_bruto)
                    markdown=({
                        "link": html_processado['link'], 
                        "conteudo": conteudo_pagina, 
                    })
                    print("\n=== SCRAPPE DAS PÁGINAS FINALIZADO ===\n")

                    conteudo_completo = ""
                    conteudo_completo += f"\n{'='*40}\n"
                    conteudo_completo += f"TÍTULO: {markdown['link']['texto']}\n"
                    conteudo_completo += f"LINK: {markdown['link']['url']}\n"
                    conteudo_completo += f"{'='*40}\n\n"
                    conteudo_completo += "--- CONTEÚDO PRINCIPAL IDENTIFICADO ---\n\n"
                    conteudo_completo += str(markdown['conteudo']) + "\n\n"
                    # Salvar em arquivo (opcional)
                    salvar_arquivo = input("\nDeseja salvar em arquivo? (s/n): ")
                    if salvar_arquivo.lower() == 's':
                        nome_arquivo_unico = f"{gerar_nome_arquivo_da_url(url)}_relatorio_completo_unico"
                        salvar_arquivo_local(conteudo=conteudo_completo, nome_arquivo=nome_arquivo_unico)
                    break
                else:
                    print("❌ Erro não foi possível raspar a página!")
            case 2: 
                status, html_processado = processar_scrape_completo(url)
                print("\n=== SCRAPPE DAS PÁGINAS FINALIZADO ===\n")
                if status and html_processado:
                    markdown = [] 

                    for paginas_html in html_processado:
                        if paginas_html['status'] == True:
                            conteudo_bruto = html_para_markdown(paginas_html['html'])
                            conteudo_pagina = limpar_markdown(conteudo_bruto)
                            markdown.append({
                                "link": paginas_html['link'], 
                                "conteudo": conteudo_pagina, 
                            })
                    
                    # Salvar em arquivo (opcional)
                    salvar_arquivo = input("\nDeseja salvar os arquivo? (s/n): ")
                    if salvar_arquivo.lower() == 's':
                        salvar_arquivos_unico = input("\nDeseja salvar os arquivos em um único arquivo (s) ou um arquivo para cada página (n)? (s/n): ")
                        if salvar_arquivos_unico.lower() == 's':
                            conteudo_completo = ""
                            for arquivo in markdown:
                                conteudo_completo += f"\n{'='*40}\n"
                                conteudo_completo += f"TÍTULO: {arquivo['link']['texto']}\n"
                                conteudo_completo += f"LINK: {arquivo['link']['url']}\n"
                                conteudo_completo += f"{'='*40}\n\n"
                                conteudo_completo += "--- CONTEÚDO PRINCIPAL IDENTIFICADO ---\n\n"
                                conteudo_completo += str(arquivo['conteudo']) + "\n\n"
                            nome_arquivo_unico = f"{gerar_nome_arquivo_da_url(url)}_relatorio_completo_multi"
                            salvar_arquivo_local(conteudo=conteudo_completo, nome_arquivo=nome_arquivo_unico)
                        else:
                            for idx, arquivo in enumerate(markdown, 1):
                                # Tenta usar o texto do link, se não existir, usa o índice
                                texto_link = arquivo['link'].get('texto') if isinstance(arquivo['link'], dict) and 'texto' in arquivo['link'] else f'pagina_{idx}'
                                nome_arquivo = f"{gerar_nome_arquivo_da_url(url)}_{texto_link}"
                                conteudo = f"{'='*40}\nTÍTULO: {texto_link}\n{'='*40}\n\n--- CONTEÚDO PRINCIPAL IDENTIFICADO ---\n\n{arquivo['conteudo']}\n\n"
                                salvar_arquivo_local(conteudo=conteudo, nome_arquivo=nome_arquivo)
                    break
                else:
                    print("❌ Erro não foi possível raspar a página!")

            case 9: 
                break

            case _: 
                print("Comando desconhecido")
        modo = int(input("Digite 1 - Para o scrape de uma página única\nDigite 2 - Para o scrape de várias páginas\nEscolha: "))
