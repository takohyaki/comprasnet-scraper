import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time
import os
from utils import clean_cnpj
from downloader import download_file

# ensure the base URL is correct for downloading the files
BASE_URL = 'http://comprasnet.gov.br/livre/pregao/'

class ItensComprasNetScraper:
    def __init__(self, retries=3, delay=5):
        self.retries = retries
        self.delay = delay

    def initialize_webdriver(self):
        for i in range(self.retries):
            try:
                driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
                return driver
            except WebDriverException as e:
                print(f"WebDriver initialization failed (attempt {i+1}/{self.retries}): {e}")
                time.sleep(self.delay)
        raise WebDriverException("Failed to initialize WebDriver after multiple attempts")

    def scrape_anexo_dos_itens(self, uasg, numero):
        driver = self.initialize_webdriver()
        anexo_itens_data = []

        try:
            driver.get('http://comprasnet.gov.br/livre/pregao/ata0.asp')
            driver.find_element(By.NAME, 'co_uasg').send_keys(uasg)
            driver.find_element(By.NAME, 'numprp').send_keys(numero)
            driver.find_element(By.XPATH, "//input[@value='OK']").click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table tbody tr td a')))
            driver.find_element(By.CSS_SELECTOR, 'table tbody tr td a').click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@value='Anexos dos Itens']")))
            driver.find_element(By.XPATH, "//input[@value='Anexos dos Itens']").click()
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
            driver.switch_to.window(driver.window_handles[1])
            
            table = None
            retries = 0

            while retries < 2 and table is None:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table')))
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table')
                
                if table is None:
                    print("Table not found in the pop-up, retrying...")
                    driver.find_element(By.XPATH, "//input[@value='Anexos dos Itens']").click()
                    retries += 1
                    time.sleep(2)  # Wait for a moment before retrying

            if table:
                rows = table.find_all('tr')
                item_number = ''
                item_name = ''
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 1 and 'Item:' in cols[0].text:
                        # Updated regex to match item numbers with or without a hyphen in front
                        match = re.match(r'Item: -?(\d+) - (.+)', cols[0].text.strip())
                        if match:
                            item_number, item_name = match.groups()
                    elif len(cols) == 4:
                        cnpj = cols[0].text.strip()
                        razao_social = cols[1].text.strip()
                        anexo_link_element = cols[2].find('a')
                        anexo = anexo_link_element.text.strip() if anexo_link_element else 'No link found'
                        anexo_link = BASE_URL + anexo_link_element['href'] if anexo_link_element else 'No link found'
                        enviado_em = cols[3].text.strip()

                        if cnpj == "CNPJ/CPF" or razao_social == "Razão Social/Nome" or enviado_em == "Enviado em:":
                            continue

                        # only append if all fields are complete
                        if item_number and item_name and cnpj and razao_social and anexo_link != 'No link found' and enviado_em:
                            anexo_itens_data.append([uasg, numero, f'Item: {item_number} - {item_name}', cnpj, razao_social, anexo, anexo_link, enviado_em])

                            clean_cnpj_value = clean_cnpj(cnpj)
                            filename = f'{uasg}_{numero}_Item{item_number}_{clean_cnpj_value}_{anexo}'
                            download_file(anexo_link, os.path.join('AnexoDosItens', filename))

                            print(f"Final Entry Added: UASG={uasg}, Numero={numero}, Item={item_number} - {item_name}, CNPJ={cnpj}, Razão Social={razao_social}, Anexo={anexo}, Anexo Link={anexo_link}, Enviado em={enviado_em}")
                        else:
                            print(f"Incomplete Entry Skipped: UASG={uasg}, Numero={numero}, Item={item_number} - {item_name}, CNPJ={cnpj}, Razão Social={razao_social}, Anexo={anexo}, Anexo Link={anexo_link}, Enviado em={enviado_em}")
            else:
                print("Table not found in the pop-up after retries")

            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"Error processing {uasg} {numero} (Anexos dos Itens): {e}")
        finally:
            driver.quit()

        print("Final Entries in anexo_itens_data:")
        for entry in anexo_itens_data:
            print(entry)

        return anexo_itens_data

# if __name__ == "__main__":
#     scraper = ComprasNetScraper()
#     anexo_data = scraper.scrape_anexo_dos_itens('40003', '292013')
#     for entry in anexo_data:
#         print(entry)
