from modos.scrape_unico import processar_scrape_unico
from modos.scrape_completo import processar_scrape_completo
from ferramentas.converter import html_para_markdown
from ferramentas.salvamento import salvar_arquivo_local
from ferramentas.nome_arquivo import gerar_nome_arquivo_da_url

if __name__ == "__main__":
    print("=== Web Scraper para Markdown ===\n")

    url = input("Digite a URL da página: ")
    
    print("=== Oque deseja fazer com essa URL? ===\n")
    modo = int(input("Digite 1 - Para o scrape de uma página única\nDigite 2 - Para o scrape de várias páginas\nEscolha: "))
    
    print("\nProcessando...\n")
    while modo != 9:
        match modo:
            case 1:
                status, html_processado, informacoes_da_pagina, nome_arquivo_gerado = processar_scrape_unico(url)
            
                if status and html_processado:
                    print("\n=== RESULTADO EM MARKDOWN ===\n")
                    markdown = html_para_markdown(html_processado)
                    print(markdown)

                    print("\n=== INFORMAÇÕES DA PÁGINA CAPTURADAS ===\n")
                    print(informacoes_da_pagina)
                    
                    # Salvar em arquivo (opcional)
                    salvar_arquivo = input("\nDeseja salvar em arquivo? (s/n): ")
                    if salvar_arquivo.lower() == 's':
                        salvar_arquivo_local(conteudo=markdown, nome_arquivo=nome_arquivo_gerado)
                        salvar_arquivo_local(conteudo=informacoes_da_pagina, nome_arquivo=f"{nome_arquivo_gerado}_informacoes")
                    break
                else:
                    print("❌ Erro não foi possível raspar a página!")
            case 2: 
                status, html_processado = processar_scrape_completo(url)
                print("\n=== SCRAPPE DAS PÁGINAS FINALIZADO ===\n")
                if status and html_processado:
                    markdown = [] 
                    
                    for paginas_html in html_processado:
                        markdown.append({"link": paginas_html['link'], "pagina": html_para_markdown(paginas_html['html']), "informacoes": paginas_html['extrair_informacoes_estruturadas'], "nome": paginas_html['nome']})
                    # Salvar em arquivo (opcional)
                    salvar_arquivo = input("\nDeseja salvar os arquivo? (s/n): ")
                    if salvar_arquivo.lower() == 's':
                        for arquivos in markdown:
                            if arquivos['pagina'] != None:
                                salvar_arquivo_local(conteudo=arquivos['pagina'], nome_arquivo=arquivos['nome'])
                                salvar_arquivo_local(
                                    conteudo=arquivos['informacoes'], 
                                    nome_arquivo=f"{arquivos['nome']}_informacoes"
                                )
                    break
                else:
                    print("❌ Erro não foi possível raspar a página!")

            case 9: 
                break

            case _: 
                print("Comando desconhecido")
        modo = int(input("Digite 1 - Para o scrape de uma página única\nDigite 2 - Para o scrape de várias páginas\nEscolha: "))