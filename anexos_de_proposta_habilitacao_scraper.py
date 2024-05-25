from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time
import os
import requests
from utils import clean_cnpj
from downloader import download_file
import logging

# ensure the base URL is correct for downloading the files
BASE_URL = 'http://comprasnet.gov.br/livre/pregao/'

class PropostaComprasNetScraper:
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

    def scrape_anexos_de_proposta_habilitacao(self, uasg, numero):
        driver = self.initialize_webdriver()
        proposta_habilitacao_data = []

        try:
            driver.get('http://comprasnet.gov.br/livre/pregao/ata0.asp')
            driver.find_element(By.NAME, 'co_uasg').send_keys(uasg)
            driver.find_element(By.NAME, 'numprp').send_keys(numero)
            driver.find_element(By.XPATH, "//input[@value='OK']").click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table tbody tr td a')))
            driver.find_element(By.CSS_SELECTOR, 'table tbody tr td a').click()

            # check for "Anexos de Proposta/Habilitacao" button
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@value='Anexos de Proposta/Habilitação']")))
                driver.find_element(By.XPATH, "//input[@value='Anexos de Proposta/Habilitação']").click()
                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                driver.switch_to.window(driver.window_handles[1])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table')))
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table')

                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # skip header row
                        start_time = time.time()
                        cols = row.find_all('td')
                        if len(cols) == 4:
                            fornecedor = cols[0].text.strip()
                            anexo_link_element = cols[1].find('a')
                            anexo = anexo_link_element.text.strip() if anexo_link_element else 'No link found'
                            anexo_link = BASE_URL + anexo_link_element['href'] if anexo_link_element else 'No link found'
                            tipo = cols[2].text.strip()
                            enviado_em = cols[3].text.strip()

                            # ensure valid data
                            if fornecedor == "Fornecedor" or tipo == "Tipo" or enviado_em == "Enviado em:":
                                continue

                            # check if the download is insecure
                            insecure_download = "No"
                            file_downloaded = "No"
                            try:
                                # attempt a request to check the SSL certificate
                                response = requests.head(anexo_link, timeout=5)
                                if response.status_code != 200:
                                    insecure_download = "Yes"
                            except requests.exceptions.SSLError:
                                insecure_download = "Yes"
                            except requests.exceptions.RequestException:
                                insecure_download = "Yes"

                            # only append if all fields are complete
                            if fornecedor and anexo_link != 'No link found' and enviado_em:
                                clean_cnpj_value = clean_cnpj(fornecedor.split()[0])  # extract CNPJ
                                filename = f'{uasg}_{numero}_{tipo}_{clean_cnpj_value}_{anexo}'
                                if insecure_download == "No":
                                    try:
                                        download_file(anexo_link, os.path.join('AnexosDePropostaHabilitacao', tipo, filename))
                                        file_downloaded = "Yes"
                                    except Exception as e:
                                        logging.error(f"File download failed for {anexo_link}: {e}")

                                proposta_habilitacao_data.append([uasg, numero, fornecedor, filename, anexo_link, tipo, enviado_em, insecure_download, file_downloaded])

                                print(f"Final Entry Added: UASG={uasg}, Numero={numero}, Fornecedor={fornecedor}, Anexo={filename}, Anexo Link={anexo_link}, Tipo={tipo}, Enviado em={enviado_em}, Insecure Download={insecure_download}, File Downloaded={file_downloaded}")

                            else:
                                print(f"Incomplete Entry Skipped: UASG={uasg}, Numero={numero}, Fornecedor={fornecedor}, Anexo={anexo}, Anexo Link={anexo_link}, Tipo={tipo}, Enviado em={enviado_em}, Insecure Download={insecure_download}, File Downloaded={file_downloaded}")

                        # check if the processing time exceeds 5 minutes
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 300:
                            logging.warning(f"Processing time exceeded for {uasg} {numero}, stopping early.")
                            break

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                print(f"Error processing {uasg} {numero} (Anexos de Proposta/Habilitacao): {e}")
            finally:
                driver.quit()

        except Exception as e:
            print(f"Error processing {uasg} {numero} (Anexos de Proposta/Habilitacao): {e}")
        finally:
            driver.quit()

        print("Final Entries in proposta_habilitacao_data:")
        for entry in proposta_habilitacao_data:
            print(entry)

        return proposta_habilitacao_data

# # test with a sample UASG and numero licitacao
# if __name__ == "__main__":
#     scraper = ComprasNetScraper()
#     proposta_habilitacao_data = scraper.scrape_anexos_de_proposta_habilitacao('120635', '762020')
#     for entry in proposta_habilitacao_data:
#         print(entry)