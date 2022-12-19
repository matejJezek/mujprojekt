"""
Selenium modul pro přidání událostí.
"""
import time
import lorem
import random
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

s = Service('./chromedriver')
driver = webdriver.Chrome(service=s)

driver.get("http://localhost:8000/prihlasit_uzivatele/")

driver.find_element(By.NAME, "email").send_keys('admin@pj.cz')
driver.find_element(By.NAME, "heslo").send_keys('admin', Keys.ENTER)

# !!! Změň kolik událostí se má přidat.
pocet_udalosti = 1

# !!! Změň počet pojištění, kterým se přiřazují dané události.
# Tento údaj vybírá náhodně id pojištění v rozsahu
# 1 až 'max_id_pojistence'.
max_id_pojisteni = 117

for i in range(pocet_udalosti):
    driver.get("http://localhost:8000/nova_udalost/%5B'udalosti_index'%5D/None")

    pojisteni = f'id pojištění: {random.randint(1, max_id_pojisteni)}'
    castka = random.randint(1, 99) * 1000
    predmet = lorem.sentence()
    datum = (
        f'{str(random.randint(1, 28))}.{str(random.randint(1, 12))}.202{str(random.randint(3, 9))}'
    )
    popis = lorem.paragraph()

    driver.find_element(By.NAME, "pojisteni").send_keys(pojisteni)
    driver.find_element(By.NAME, "castka").send_keys(castka)
    driver.find_element(By.NAME, "datum").send_keys(datum)
    driver.find_element(By.NAME, "popis").send_keys(popis)
    driver.find_element(By.NAME, "predmet").send_keys(predmet, Keys.ENTER)

time.sleep(5)