import os 
import json
from datetime import datetime 

def salvar_arquivo_local(conteudo, nome_arquivo, nome_pasta= "resultados"):
    """
    Salva conteudo em um arquivo local
    """
    pasta = nome_pasta
    os.makedirs(pasta, exist_ok=True) 
    nome_recebido = nome_arquivo
    
    if nome_recebido is None:
        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        arquivo = os.path.join(pasta, f'{timestamp}.md')
    else:
        arquivo = os.path.join(pasta, f'{nome_arquivo}.md') 

    with open(arquivo, 'w', encoding='utf-8') as f:
        if isinstance(conteudo, dict):
            f.write(json.dumps(conteudo, indent=2, ensure_ascii=False))
        else:
            f.write(conteudo)
    print(f"✅ Salvo em '{arquivo}'")