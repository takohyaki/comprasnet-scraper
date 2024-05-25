import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from anexos_de_proposta_habilitacao_scraper import PropostaComprasNetScraper
from anexo_dos_itens_scraper import ItensComprasNetScraper
from downloader import setup_directories
import logging
import os

setup_directories()

logging.basicConfig(filename='scraper.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

# load UASG and numero licitacao from list.txt
uasg_numero_list = []
with open('list.txt', 'r') as file:
    next(file)  # skip header
    for line in file:
        if line.strip(): # skip empty lines
            uasg, numero = line.strip().split(',')
            uasg_numero_list.append((uasg, numero))

proposta_scraper = PropostaComprasNetScraper()
itens_scraper = ItensComprasNetScraper()

# excel file paths
anexo_itens_file = 'AnexoDosItens.xlsx'
proposta_habilitacao_file = 'AnexosDePropostaHabilitacao.xlsx'

# initialize Excel files with headers if they do not exist
def initialize_excel_file(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)

initialize_excel_file(anexo_itens_file, ['Uasg', 'Num Licitacao', 'Item', 'CNPJ/CPF', 'Razão Social/Nome', 'Anexo', 'Anexo Link', 'Enviado em'])
initialize_excel_file(proposta_habilitacao_file, ['Uasg', 'Num Licitacao', 'Fornecedor', 'Anexo', 'Anexo Link', 'Tipo', 'Enviado em', 'Insecure Download', 'File Downloaded'])

# function to append a row to the excel file as it scrapes
def append_to_excel(file_path, data):
    workbook = load_workbook(file_path)
    sheet = workbook.active
    for row in dataframe_to_rows(pd.DataFrame([data]), index=False, header=False):
        sheet.append(row)
    workbook.save(file_path)

for uasg, numero in uasg_numero_list:
    try:
        # scrape items
        items_data = itens_scraper.scrape_anexo_dos_itens(uasg, numero)
        proposal_data = proposta_scraper.scrape_anexos_de_proposta_habilitacao(uasg, numero)
        
        # append data to the Excel files
        for item in items_data:
            append_to_excel(anexo_itens_file, item)
        
        for proposal in proposal_data:
            append_to_excel(proposta_habilitacao_file, proposal)
        
    except Exception as e:
        logging.error(f"Error processing {uasg} {numero}: {e}")

logging.info("Data extraction and file download completed.")
