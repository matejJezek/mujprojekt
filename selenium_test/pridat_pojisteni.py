"""
Selenium modul pro přidání pojištění.
"""
import time
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import random

s = Service('./chromedriver')
driver = webdriver.Chrome(service=s)

driver.get("http://localhost:8000/evidence_pojisteni/prihlasit_uzivatele/")

driver.find_element(By.NAME, "email").send_keys('admin@pj.cz')
driver.find_element(By.NAME, "heslo").send_keys('admin', Keys.ENTER)

typ = [
    'Pojištění hmotného majetku',
    'Pojištění nehmotného majetku'
]
predmet = [
    [
        'Automobil', 'Motocykl', 'Obytný dům', 'Stavební pozemek',
        'Garáž', 'Jachta', 'Server', 'Nákladní automobil',
        'Jízdní kolo', 'Zemědělský pozemek', 'Továrna',
        'Nemocnice', 'Školní budova', 'Traktor', 'Sekačka na trávu'
    ],
    [
        'Text písně', 'Melodie písně', 'Scénář filmu', 'Hudba k filmu',
        'Námět knihy', 'Text básně', 'Obraz', 'Patent žárovky',
        'Počítačový software'
    ]
]

# !!! Změň kolik pojištění se má přidat.
pocet_pojisteni = 120

# !!! Změň počet pojištěnců, kterým se přiřazují daná pojištění.
# Tento údaj vybírá náhodně id pojištěnců v rozsahu
# 1 až 'max_id_pojistence'.
max_id_pojistence = 28

for i in range(pocet_pojisteni):
    driver.get("http://localhost:8000/evidence_pojisteni/nove_pojisteni/%5B'pojisteni_index'%5D/None")

    pojistenec = f'id pojištěnce: {random.randint(1, max_id_pojistence)}'
    cislo = random.randint(0, 1)
    typ_ = typ[cislo]
    castka = random.randint(1, 99) * 100000
    predmet_ = random.choice(predmet[cislo])
    platnost_od = f'{str(random.randint(1, 30))}.11.2022'
    platnost_do = (
        f'{str(random.randint(1, 28))}.{str(random.randint(1, 12))}.202{str(random.randint(3, 9))}'
    )
    driver.find_element(By.NAME, "pojistenec").send_keys(pojistenec)
    driver.find_element(By.NAME, "typ").send_keys(typ_)
    driver.find_element(By.NAME, "castka").send_keys(castka)
    driver.find_element(By.NAME, "platnost_od").send_keys(platnost_od)
    driver.find_element(By.NAME, "platnost_do").send_keys(platnost_do)
    driver.find_element(By.NAME, "predmet").send_keys(predmet_, Keys.ENTER)

    time.sleep(0.5)