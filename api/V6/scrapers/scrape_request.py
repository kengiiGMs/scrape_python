import requests 
from bs4 import BeautifulSoup

def iniciar_request(url):
    """
    Faz scraping de uma URL usando request
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resposta = requests.get(url, headers=headers, timeout=10)
        resposta.raise_for_status()

        resposta.encoding = resposta.apparent_encoding
        html = resposta.text

        
        if len(html) < 500:
            return False, None
            
        html_organizado = BeautifulSoup(html, 'html.parser') 
        texto = html_organizado.get_text(strip=True)
        
        if len(texto) < 200: 
            print("⚠️  Pouco conteúdo detectado (provável estrutura clientSide)")
            return False, None
        
        return True, html 
        
    except Exception as e:
        print(f"❌ Request falhou: {e}")
        return False, None