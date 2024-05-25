def clean_cnpj(cnpj):
    return cnpj.replace(".", "").replace("/", "").replace("-", "")
