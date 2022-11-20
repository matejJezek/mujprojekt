"""
Selenium modul pro přidání pojištěnců.
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

jmeno = [
    'Jakub', 'Jan', 'Tomáš', 'Matyáš', 'Adam', 'Filip', 'Vojtěch',
    'Lukáš', 'Martin', 'Matěj', 'Ondřej', 'Daniel', 'David', 'Dominik',
    'Antonín', 'Michal', 'Petr', 'Štěpán', 'Tobiáš', 'Marek'
]
prijmeni = [
    'Novák', 'Svoboda', 'Novotný', 'Dvořák', 'Černý', 'Procházka',
    'Kučera', 'Veselý', 'Krejčí', 'Horák', 'Němec', 'Pokorný', 'Pospíšil',
    'Hájek', 'Král', 'Jelínek', 'Růžička', 'Beneš', 'Fiala', 'Sedláček'
]
ulice = [
    'Adamova', 'Bochánkova', 'Nad Propastí', 'Pod Horizontem',
    'Za Rohem', 'Pražská', 'Moskevská', 'Zahradní',
    'Chlebová', 'Husitská', 'Václava Havla',
    'U Lesíka', 'Zahradní', 'Akátová', 'Albrechtická', 'Vínová',
    'Alšova', 'Prokopova', 'Okrajová', 'Okružní'
]
mesto = [
    'Adamov', 'Albrechtice', 'Arnoltice', 'Bavorov', 'Bavory',
    'Bechlín', 'Beroun', 'Cítoliby', 'Čestlice', 'Dlažkovice',
    'Dobrochov', 'Dolní Hluboká', 'Dubnice', 'Hořovice', 'Chlumec',
    'Komárov', 'Krásno', 'Lipenec', 'Martinice', 'Oloví'
]

fotografie = [
    "/Users/admin/Dropbox/projekt_ITnetwork/fotografie/gorilla-1515755021D78.jpg",
    "/Users/admin/Dropbox/projekt_ITnetwork/fotografie/monkey-gaze.jpg",
    "/Users/admin/Dropbox/projekt_ITnetwork/fotografie/orangutan.jpg",
    "/Users/admin/Dropbox/projekt_ITnetwork/fotografie/turanga-leela-3757930_1280.png"
]

# !!! Změň kolik pojištěnců se má přidat.
pocet_pojistencu = 28

for i in range(pocet_pojistencu):
    driver.get("http://localhost:8000/evidence_pojisteni/novy_pojistenec/%5B'pojistenci_index'%5D")

    jmeno_ = random.choice(jmeno)
    prijmeni_ = random.choice(prijmeni)
    ulice_ = f'{random.choice(ulice)} {random.randint(1, 999)}'
    mesto_ = random.choice(mesto)
    psc = random.randint(10000, 99999)
    cislo_do_emailu = random.randint(0, 99999)
    email = f'email{cislo_do_emailu}@email.cz'
    telefon = random.randint(100000000, 999999999)
    fotografie_ = random.choice(fotografie)

    driver.find_element(By.NAME, "jmeno").send_keys(jmeno_)
    driver.find_element(By.NAME, "prijmeni").send_keys(prijmeni_)
    driver.find_element(By.NAME, "ulice").send_keys(ulice_)
    driver.find_element(By.NAME, "mesto").send_keys(mesto_)
    driver.find_element(By.NAME, "psc").send_keys(psc)
    driver.find_element(By.NAME, "email").send_keys(email)

    # disable the OS file picker
    driver.execute_script("""
        document.addEventListener('click', function(evt) {
        if (evt.target.type === 'file')
            evt.preventDefault();
        }, true)
        """)

    driver.find_element(By.ID, 'id_fotografie').send_keys(fotografie_)
    driver.find_element(By.NAME, "telefon").send_keys(telefon, Keys.ENTER)

    time.sleep(0.5)