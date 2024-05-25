import requests
import os

def download_file(url, filename):
    response = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(response.content)

def setup_directories():
    os.makedirs('AnexoDosItens', exist_ok=True)
    os.makedirs('AnexosDePropostaHabilitacao/Proposta', exist_ok=True)
    os.makedirs('AnexosDePropostaHabilitacao/Habilitação', exist_ok=True)