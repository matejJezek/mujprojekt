from copy import copy, deepcopy
from distutils.log import error
import math
import os
from .models import Uzivatel, Pojistenec, Pojisteni, Udalost, Clanek
from .forms import Pojistenec_formular, Pojisteni_formular, Udalost_formular
from .forms import Uzivatel_prihlaseni_formular
from .serializers import Clanek_serializer, Autor_serializer
from django.shortcuts import render, redirect, get_object_or_404
from django.http import request, QueryDict
from django.views import generic
from django.contrib import messages
from django.core.paginator import Paginator, Page
from django.contrib.auth import login, logout, authenticate
from rest_framework.response import Response
from rest_framework import permissions, renderers, viewsets, status, views
from rest_framework.reverse import reverse
from rest_framework.decorators import action, renderer_classes
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from rest_framework.views import APIView
from rest_framework.decorators import api_view

# Create your views here.

# ----------------------------------------------------------------------------
# ------------------------------ F U N K C E ---------------------------------
# ----------------------------------------------------------------------------

def generuj_adresy_presmerovani(
        adresy_presmerovani: list,
        primarni_klice: list,
        adresa_pridat: str = None
        ) -> list:
    """
    Generuje seznam adres přesměrování a upravuje dle potřeby seznam
primárních klíčů.
    Aplikace si adresy přesměrování předává mezi jednotlivými views
(pohledy) a templates jako seznam, kde na indexu 0 je stránka
navštívená jako první a na indexu -1 je stránka navštívená jako
poslední. Stránky v seznamu reprezentuje jejich textové pojmenování.
Např. 'detail_pojistence'.

    :param adresy_presmerovani list: Adresy presměrování slouží pro
průchod aplikací přes tlačítko 'Zpět' nebo pro jiný přechod na
předchozí stránku. Například po vymazání objektu nebo ze stránky
upravit a podobně.
    :param primarni_klice list: Primární klíče náležící objektům
na které proběhne přesměrování směrem zpět.
    :param pridat str: Obsahuje stránku, která se má přidat do adres
přesměrování, defaults to None.
    :return list: Dvourozměrný list. Seznam adres přesměrování
a seznam primárních klíčů
    """

    # Převede textový řetězec na seznam odstraněním uvozovek. Předávání
    # seznamu mezi views (pohledy) probíhá v textové podobě přes url
    # adresu.
    adresy_presmerovani = eval(adresy_presmerovani)

    # Kontrola, zda přidáváme na konec seznamu novou adresu
    # přesměrování. 'None' je v případě, kdy ze stránky nelze jít na
    # novou stránku.Např. z 'upravit pojištěnce' lze pouze na předchozí
    # stránku. Pokud 'pridat' není 'None', obsahuje textový řetězec
    # s názvem stránky.
    if adresa_pridat:

        # Zde se nacházíme, pokud je možné z dané stránky jít na
        # stránku jinou než předchozí.
        # Adresu aktuální stránky do seznamu adres přesměrování
        # přidáme v případě, že už není na poslední pozici v seznamu.
        # Toto nastane pokud se např. na stránku 'detail pojištěnce'
        # vrátíme ze stránky 'upravit pojištěnce' nebo kterékoliv
        # jiné.
        try:
            if adresy_presmerovani[-1] != adresa_pridat:
                adresy_presmerovani.append(adresa_pridat)

        # Pokud v seznamu adres přesměrování není žádná položka,
        # přídá se do něj adresa aktuální stránky.
        except:
            adresy_presmerovani.append(adresa_pridat)

    # Pokud nepřidáme při návratu do detailu objektu znovu textovou
    # reprezentaci jeho stránky, odebereme poslední primární klíč,
    # který jsme využily například při úpravě objektu a vrátili
    # se zpět do detailu objektu nadřazeného a tedy znovu
    # nezadávali jeho adresu do adres k přesměrování.
    #
    # Blok try-except pro případ, 'adresy_presmerovani' nebo
    # 'primarni_klice' budou tytpu None.
    try:
        if len(adresy_presmerovani) < len(primarni_klice):
            primarni_klice.pop()
    except:
        pass

    return [adresy_presmerovani, primarni_klice]

def jdi_na_detail_upravit(request: object, adresa: str,
        adresy_presmerovani: list, primarni_klice: list) -> object:
    """
    Jednotný přístup pro přesměrování aplikace směrem dopředu na
detail objektu nebo upravit objekt z výčtu objektů.

    :param request object: Objekt HTTP požadavku.
    :param adresa str: Adresa kam se aplikace přesměruje.
    :param adresy_presmerovani list: List adres, kde už aplikace byla.
    :param primarni_klice list: List primárních klíčů objektů, kde už
aplikace byla.
    :return object: Objekt HTTP odpovědi s přesměrováním da požadovanou
stránku.
    """

    if request.POST[adresa]:
        pk_objektu = int(request.POST[adresa])
        primarni_klice.append(pk_objektu)

        if (adresa == 'detail_udalosti') or ('upravit' in adresa):
            return redirect(adresa, adresy_presmerovani, primarni_klice)

        else:
            return redirect(
                adresa, adresy_presmerovani, primarni_klice, '-id'
            )

def presmeruj(
        request: object, adresy_presmerovani: list,
        primarni_klice: list = None, pridano: bool = False,
        zustat: bool = False, zpet: bool = False, odstraneno: bool = False,
        seradit_podle: str = '-id'
        ) -> object:
    """
    Rozhoduje, na jaký view (pohled), se aplikace přesměruje na základě
adres přesměrování směrem dozadu (stisk tlačítka zpět, smazání objektu
a přesměrování na objekt vlastníka, úprava objektu, ...).

    :param request object: Objekt HTTP dotazu.
    :param adresy_presmerovani list: Adresy presměrování slouží pro
průchod aplikací přes tlačítko 'Zpět' nebo pro jiný přechod na
předchozí stránku. Například po vymazání objektu nebo ze stránky
upravit a podobně.
    :param primarni_klice list: Obsahuje seznam primárních klíčů
navštívených objektů. Slouží jak pro zobrazení detailu správného
(chtěného) objektu (čili vpřed, klíč se předává před přechodem na
nové wievs), tak pro historii procházení, čili přesměrování na
předchozí stránku (čili zpět), defaults to None.
    :param pridano bool: Obsahuje informaci o tom, zda došlo
k přidání stránky do seznamu adres přesměrování ('True') či
nikoliv ('False'), defaults to False.
    :param zustat bool: informuje, zda chceme po provedení akce zůstat
na té samé stránce, na které se akce vykonala ('True', 'False'),
defaults to False.
    :param zpet bool: Informuje, zda uživatel klikl na tlačítko zpět
('True') nebo přesměrování probíhá z jiného důvodu ('False'),
defaults to False.
    :param odstraneno bool: Pokud smežeme objekt v jeho detailu,
potřebujeme se přesměrovat na předchozí stránku.
    :param seradit_podle str: Informace, podle kterého sloupečku se má
seřadit tabulka s výčtem objektů (pojištěnci, pojištění nebo události,
...), defaults to '-id'.
    :return object: Přesměrování na views (pohledy) na základě adres
přesměrování.
    """

    # Pokud jsme adresu přesměrování nepřidávali, je jedno, jestli jsme
    # klikli na tlačítko zpět nebo ne, stránku na kterou se
    # přesměrujeme bude v seznamu vždy ta poslední přidaná.
    #
    # Např. z 'upravit_objekt' zpet do 'detail_objektu'.
    index = -1

    # Pokud jsme však atuální stránku přidávali do adres přesměrování,
    # je třeba v případě potřeby přesměrovat na předposlední stránku
    # v seznamu, protože ta poslední je ta aktuální.
    #
    # Např. smazání objektu a tedy návrat na předchozí stránku.
    if pridano:
        index = -2

        # Pokud ovšem například mažeme pojištění v detailu pojištěnce,
        # přejeme si zůstat po aktualizaci v detailu pojištěnce, tedy
        # na té aktuální stránce, čili té poslední v seznamu.
        if zustat:
            index = -1

    # Blok 'try–except' pro zachycení neplatného indexu v seznamu.
    try:

        # Vytvoříme kopii seznamu primárních klíčů. Pokud jsme
        # přihlášeni v roli pojištěnce a zmáčkneme tlačítko zpět
        # v detailu pojištěnce poté, co jsme do něj vstoupily přes
        # 'šablonu' (tlačítko v menu),
        # je třeba aby se neodebral poslední
        # a jediný primární klíč ze seznamu primárních klíčů,
        # protože pak by aplikace neměla informaci o tom,
        # čí detail má zobrazit (tedy zůstat na místě)
        # a přesměrovala by aplikaci na úvodní stránku.
        primarni_klice_ = copy(primarni_klice)

        # Pokud přesměrováváme tlačítkem 'Zpět', je třeba aktuální
        # stránku odebrat ze seznamu adres přesměrování a přesměrovat
        # na stránku s indexem -1. To samé, pokud odebereme objekt
        # a vracíme se na předcházející stránku.
        if zpet or odstraneno:
            adresy_presmerovani.pop()
            primarni_klice.pop()
            index = -1

        if adresy_presmerovani[index] == 'pojistenci_index':
            return redirect('pojistenci_index', seradit_podle)

        elif adresy_presmerovani[index] == 'pojisteni_index':
            return redirect('pojisteni_index', seradit_podle)

        elif adresy_presmerovani[index] == 'udalosti_index':
            return redirect('udalosti_index', seradit_podle)

        elif adresy_presmerovani[index] == 'detail_pojistence':
            return redirect('detail_pojistence', adresy_presmerovani,
                            primarni_klice, seradit_podle)

        elif adresy_presmerovani[index] == 'detail_udalosti':
            return redirect('detail_udalosti', adresy_presmerovani,
                            primarni_klice)

        elif adresy_presmerovani[index] == 'detail_pojisteni':
            return redirect('detail_pojisteni', adresy_presmerovani,
                            primarni_klice, seradit_podle)

        elif adresy_presmerovani[index] == '':
            return redirect('detail_pojistence', adresy_presmerovani,
                            primarni_klice_, seradit_podle)

        # Pokud nenastane ani jedna z výše uvedených možností, vyvolá
        # se error, abychom se dostali do bloku 'except' a využili
        # stejného kódu, jako kdyby nebyla k dispozici stránka
        # v seznamu adres přesměrování na kterou se lze přesměrovat.
        raise error

    except:
        messages.error(
            request, """Přesměrování není funkční. Dojde
            (došlo) k přesměrování na úvodní stránku."""
        )
        return redirect('index')

def zobraz_stranku(
        request: object, adresa_stranky: str,
        slovnik_k_odeslani: dict = None, seradit_co: str = None,
        seradit_podle: str = None, trida_objektu: object = None,
        django_rest: bool = False
        ) -> object:
    """
    Generuje objekt 'response' s přesměrováním na
příslušný 'template' (stránku) včetně nastavených COOKIES.
    Funkce byla vytvořena při implementaci COOKIES do
jednotlivých views (pohledy), protože bylo příliž velké množství
opakujícího se kódu.
    COOKIES jsou využívány pro řazení jednotlivých objektů při jejich
výčtu. COOKIES si pamatují, jak si uživatel jednotlivé výčty seřadil
a seřadí mu je při příští návštěvě stránky stejně.

    :param request object: Objekt HTTP dotazu.
    :param adresa_stranky: skrývá textový řetězec s adresou stránky,
kterou budeme zobrazovat.
    :param slovnik_k_odeslani: obsahuje slovník s objekty,
který posíláme do příslušného 'template' (stránky), defaults to None.
    :param seradit_co: určuje, jaký výčet chceme seřadit, jedná se
o textový řetězec, defaults to None.
    :param seradit_podle: skrývá textový řetězec určující podle
jakého sloupečku řadíme a jestli směrem nahoru nebo dolů
(např. 'prijmeni' nebo '-prijmeni'), defaults to None.
    :param trida_objektu: obsahuje objekt, který chceme seřadit,
defaults to None.
    :param django_rest bool: informace, zda požadavek na zobrazení
stránky přišel z pohledu konstruovaného frameworkem Django Rest.
    :return object: Objekt HTTP odpovědi.
    """

    # Pokud se chystáme zobrazit stránku, kde není co řadit a tudíž ani
    # načítat výčet dat z dabáze, je úloha snadná a rovnou zobrazíme
    # stránku.
    if not seradit_co:

        # Pokud dotaz na zobrazení stránky přišel z funkcionality
        # frameworku Django Rest.
        if django_rest:
            return Response(slovnik_k_odeslani, template_name=adresa_stranky)

        return render(request, adresa_stranky, slovnik_k_odeslani)

    # Proměnná 'seradit_podle' obsahuje znak '0', pokud řazení vzešlo
    # jako požadavek od uživatele. Automaticky je výčet řazen podle
    # '-id', v takovém případě proměnná 'seradit_podle' neobsahuje
    # znak '0' a hodnota se neuloží do COOKIES.
    # proměnná 'seradit_podle_puvodni' obsahuje původní hodnotu
    # 'seradit_podle', tedy včetně znaku '0', pokud je přítomen.
    if seradit_podle == '0':
        seradit_podle = '-id'
    seradit_podle_puvodni = seradit_podle

    # Pokud požadavek na řazení neodeslal uživatel.
    if '0' not in seradit_podle:

        # Pokud to (výčet objektů), co chceme seřadit už má uloženou
        # hodnotu jako COOKIE.
        if seradit_co in request.COOKIES:

            # Tak do proměnné 'seradit_podle' načteme hodotu
            # z COOKIE.
            seradit_podle = request.COOKIES[seradit_co]

    # Pokud požadavek na řazení odeslal uživatel.
    else:

        # Tak do proměnné 'seradit_podle' uložíme hodotu
        # z 'seradit_podle' bez znaku '0'.
        seradit_podle = seradit_podle.replace('0', '')

        # A zároveň jí uložíme do slovníku COOKIES, který obsahuje
        # objekt 'request'. To nám zajistí přítomnost dané COOKIE už
        # při prvním zobrazení stránky.
        # Tento krok ovšem COOKIE neuloží do COOKIES natrvalo.
        request.COOKIES[seradit_co] = seradit_podle

    # Proměnnou 'seradit_podle_raw' použijeme na řazení objektů v SQL
    # raw dotazu. Musíme odstranit znak '-' a nahradit ho 'DESC'
    # nebo 'ASC' nakonec ORDER BY.
    seradit_podle_raw = seradit_podle.replace('-', '')
    if '-' in seradit_podle:
        smer = 'DESC'
    else:
        smer = 'ASC'

    # Proměnná 'pocet_objektu_na_stranku' udává, kolik chceme mít na
    # jedné stránce objektů.
    pocet_objektu_na_stranku = 4

    # Pokud jsme klikly na nějakou stránku (číslo stránky) pod výčtem
    # objektů, spočteme, kolik objektů se musí v databázi přeskočit,
    # abychom získaly pouze objetky na příslušné stránce. Pokud jsme na
    # číslo stránky neklikly, ale do výčtu přišly z jiné URL zobrazíme
    # stránku 1 a tedy přeskočíme v databázi 0 objektů.
    if request.GET.get('page'):
        preskocit_objektu = (
            int(request.GET.get('page')) - 1
        ) * pocet_objektu_na_stranku
    else:
        preskocit_objektu = 0
    
    # Blok podmínek, které určují, co řadíme a do proměnné
    # 'objekty_na_stranku' nám ukládá seřazené objekty podle daných
    # kritérií v počtu na danou stránku.
    # raw SQL dotazy jsou zde využity, protože přednastavené databázové
    # metody v DJANGU nenabízí možnost OFFSETU v databázi.
    if seradit_co == 'seradit_pojistenci_index':
        pocet_objektu_celkem = trida_objektu.objects.count()
        objekty_na_stranku = trida_objektu.objects.raw(
            f"""
            SELECT id
            FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
            ORDER BY {seradit_podle_raw} {smer}
            LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
            """
        )
    
    elif seradit_co == 'seradit_clanky_index':

        if 'text_hledat' in request.COOKIES:
            text_hledat = request.COOKIES['text_hledat']

            pocet_objektu_celkem = len(trida_objektu.objects.raw(
                    f"""
                    SELECT clanek.id
                    FROM evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual AS virt
                    JOIN evidence_pojisteni_{trida_objektu.__name__.lower()} AS clanek ON clanek.id = virt.rowid
                    WHERE evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual
                    MATCH {"'{}'".format(text_hledat)}
                    """
                ))

            if seradit_podle_raw == 'email':
                objekty_na_stranku = trida_objektu.objects.raw(
                    f"""
                    SELECT clanek.id
                    FROM evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual AS virt
                    JOIN evidence_pojisteni_{trida_objektu.__name__.lower()} AS clanek ON clanek.id = virt.rowid
                    JOIN evidence_pojisteni_uzivatel AS uzivatel ON clanek.autor_id = uzivatel.id
                    WHERE evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual
                    MATCH {"'{}'".format(text_hledat)}
                    ORDER BY uzivatel.{seradit_podle_raw} {smer}
                    LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                    """
                )

            else:
                objekty_na_stranku = trida_objektu.objects.raw(
                    f"""
                    SELECT clanek.id
                    FROM evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual AS virt
                    JOIN evidence_pojisteni_{trida_objektu.__name__.lower()} AS clanek ON clanek.id = virt.rowid
                    WHERE evidence_pojisteni_{trida_objektu.__name__.lower()}_virtual
                    MATCH {"'{}'".format(text_hledat)}
                    ORDER BY clanek.{seradit_podle_raw} {smer}
                    LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                    """
                )
        else:
            pocet_objektu_celkem = trida_objektu.objects.count()

            if seradit_podle_raw == 'email':
                objekty_na_stranku = trida_objektu.objects.raw(
                    f"""
                    SELECT clanek.id
                    FROM evidence_pojisteni_{trida_objektu.__name__.lower()} AS clanek
                    JOIN evidence_pojisteni_uzivatel AS uzivatel ON clanek.autor_id = uzivatel.id
                    ORDER BY {seradit_podle_raw} {smer}
                    LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                    """
                )
                
            else:
                objekty_na_stranku = trida_objektu.objects.raw(
                    f"""
                    SELECT id
                    FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
                    ORDER BY {seradit_podle_raw} {smer}
                    LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                    """
                )

    elif seradit_co == 'seradit_autori_index':
        pocet_objektu_celkem = trida_objektu.objects.filter(je_admin=True).count()

        if seradit_podle_raw == 'pocet_clanku':
            seradit_podle_raw = 'count(autor_id)'
            
            objekty_na_stranku = trida_objektu.objects.raw(
                f"""
                SELECT autor_id AS id
                FROM evidence_pojisteni_clanek
                GROUP BY autor_id
                ORDER BY {seradit_podle_raw} {smer}
                LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                """
            )

        else:
            objekty_na_stranku = trida_objektu.objects.raw(
                f"""
                SELECT id
                FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
                WHERE id IN (
                    SELECT autor_id
                    FROM evidence_pojisteni_clanek
                    GROUP BY autor_id
                )
                ORDER BY {seradit_podle_raw} {smer}
                LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                """
            )

    elif (seradit_co == 'seradit_pojisteni_index' or
          seradit_co == 'seradit_udalosti_index'):

        if request.user.je_admin:
            pocet_objektu_celkem = trida_objektu.objects.count()
            objekty_na_stranku = trida_objektu.objects.raw(
                f"""
                SELECT id
                FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
                ORDER BY {seradit_podle_raw} {smer}
                LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                """
            )

        elif request.user.pojistenec:
            pocet_objektu_celkem = trida_objektu.objects.filter(
                pojistenec_id=request.user.pojistenec.id
            ).count()
            objekty_na_stranku = trida_objektu.objects.raw(
                f"""
                SELECT id
                FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
                WHERE pojistenec_id = {request.user.pojistenec.id}
                ORDER BY {seradit_podle_raw} {smer}
                LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
                """
            )

    elif seradit_co == 'seradit_detail_pojistence__pojisteni':
        pojistenec_id = slovnik_k_odeslani['pojistenec'].id
        pocet_objektu_celkem = trida_objektu.objects.filter(
            pojistenec_id = pojistenec_id
        ).count()
        objekty_na_stranku = trida_objektu.objects.raw(
            f"""
            SELECT id
            FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
            WHERE pojistenec_id = {pojistenec_id}
            ORDER BY {seradit_podle_raw} {smer}
            LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
            """
        )

    elif seradit_co == 'seradit_detail_pojisteni__udalosti':
        pojisteni_id = slovnik_k_odeslani['pojisteni'].id
        pocet_objektu_celkem = trida_objektu.objects.filter(
            pojisteni_id = pojisteni_id
        ).count()
        objekty_na_stranku = trida_objektu.objects.raw(
            f"""
            SELECT id FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
            WHERE pojisteni_id = {pojisteni_id}
            ORDER BY {seradit_podle_raw} {smer}
            LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
            """
        )

    elif seradit_co == 'seradit_detail_autora__clanky':
        autor_id = slovnik_k_odeslani['autor']['id']
        pocet_objektu_celkem = trida_objektu.objects.filter(
            autor_id = autor_id
        ).count()
        objekty_na_stranku = trida_objektu.objects.raw(
            f"""
            SELECT id FROM evidence_pojisteni_{trida_objektu.__name__.lower()}
            WHERE autor_id = {autor_id}
            ORDER BY {seradit_podle_raw} {smer}
            LIMIT {preskocit_objektu}, {pocet_objektu_na_stranku}
            """
        )

    # Pokud je objekt součástí funkcionality Django REST, aplikujeme na
    # něj před odesláním serializer.
    if django_rest:
        if (seradit_co == 'seradit_clanky_index' or
            seradit_co == 'seradit_detail_autora__clanky'):

            serializer = Clanek_serializer(
                objekty_na_stranku,
                many=True,
                context={'request': request}
            )

        if seradit_co == 'seradit_autori_index':

            serializer = Autor_serializer(
                objekty_na_stranku, 
                many=True,
                context={'request': request}
            )

        objekty_na_stranku = serializer.data

    # Proměnnou 'slovnik_k_odeslani' doplníme o proměnnou
    # 'stranka_obj', tato proměnná obsahuje objekt třídy 'Page', který
    # vrátí funkce 'strankuj'.
    slovnik_k_odeslani.update(
        {
            'stranka_obj': strankuj(
                request, objekty_na_stranku, pocet_objektu_celkem,
                pocet_objektu_na_stranku
            )
        }
    )

    # Objektu 'response' přiřadíme požadavek na zobrazení 'templete'.
    response = render(request, adresa_stranky, slovnik_k_odeslani)

    # Pokud přišel požadavek na seřazení výčtu od uživatele.
    if '0' in seradit_podle_puvodni:
        # Tak uložíme informaci o seřazení do COOKIES.
        response.set_cookie(seradit_co, seradit_podle)
    return response

def generuj_presmerovani(request: object, adresy_presmerovani: list,
        primarni_klice: list, adresa_pridat: str = None,
        pridano: bool = False, zustat: bool = False, zpet: bool = False,
        odstraneno: bool = False) -> object:
    """
    Vygeneruje adresy presměrování a vrátí objekt response
s přesměrováním na požadovanou stránku.

    :param request object: Objekt HTTP dotazu.
    :param adresy_presmerovani list: Adresy přesměrování směrem zpět.
    :param primarni_klice list: Primární klíče náležící objektu na
dané adrese.
    :param adresa_pridat str: Adresa, která se přidá nakonec seznamu
adres pro zpětný průchod aplikací.
    :param pridano bool: Informace, zda jsme přidaly adresu nakonec
seznamu adres pro zpětný průchod aplikací.
    :return object: Přesměrování na příslušnou stránku.
    """

    adresy_presmerovani_pk = generuj_adresy_presmerovani(
            adresy_presmerovani, primarni_klice, adresa_pridat
        )

    presmerovani = presmeruj(
            request, adresy_presmerovani_pk[0], adresy_presmerovani_pk[1],
            pridano, zustat, zpet, odstraneno
        )

    return presmerovani

def strankuj(
        request: object, objekty_na_stranku: dict, pocet_objektu_celkem: int,
        pocet_objektu_na_stranku: int
        ) -> object:
    """
    Generuje objekt třídy 'Page'. Obsahuje mírně upravený 'paginator'
('stránkovač'), který je upraven tak, že má předem připravené jen
takové objekty a v daném počtu, které se mají na dané stránce zobrazit.
Čili tuto práci jsme udělali za něj. Další jeho metody ale s radostí
využijeme.

    :param request object: Objekt HTTP dotazu.
    :param objekty_na_stranku dict: Dává funkci již připravený výčet
objetků, které se mají zobrazit na dané stránkce (čísle stránky).
    :param pocet_objektu_celkem int: je celkový počet objektů
v databázi.
    :param pocet_objektu_na_stranku int: udává, kolik chceme mít na
jedné stránce objektů.
    :return object: Objekt třídy 'Page'.
    """

    # Tímto zadáním nám paginátor do proměnné 'strankovac' uloží
    # instanci své třídy s informací, jaké všechny objekty chceme
    # 'stránkovat' ('objekty_na_stranku') a kolik jich chceme na
    # jednu stránku ('pocet_objektu_na_stranku').
    strankovac = Paginator(objekty_na_stranku, pocet_objektu_na_stranku)

    # Protože ale 'objekty_na_stranku' nejsou všechny objekty, které
    # chceme 'stránkovat', ale už připravené objekty na jednu danou
    # stránku, řekneme 'stránkovači', kolik objektů máme celkem na
    # všechny stránky dohromady.
    strankovac.count = pocet_objektu_celkem

    # Zjistíme z požadavku od uživatele, na které stránce se nacházíme.
    cislo_stranky = request.GET.get('page')

    # Pokud uživatel nezadal stránku, dostaneme 'None'. To ošetříme
    # tak, že se nám do proměnné 'cislo_stranky' uloží '1', aby šla
    # proměnná správně použít při deklaraci instance třídy 'Page'.
    if not cislo_stranky:
        cislo_stranky = 1

    # Do proměnné 'stranka_obj' uložíme instanci třídy 'Page'.
    stranka_obj = Page(objekty_na_stranku, int(cislo_stranky), strankovac)
    return stranka_obj

def zobraz_formular_znovu(
        request: object, formular: object, adresa_stranky: str, status: str
        ) -> object:
    """
    Pokud uživatel zadá nevalidní údaje do formuláře, zobrazí se mu
znovu stránka s formulářem a upozorní ho na chybu. Zde se týká pouze
formuláře pro tvorbu nového nebo úpravu stávajícího uživatele.

    :param request object: Objekt HTTP požadavku.
    :param formular object: Objekt s vyplněným formulářem.
    :param adresa_stranky str: Adresa stránky, která se bude
zobrazovat.
    :param status str: Textová informace o tom, zda nadpis stránky bude
'Nový' pojištěnec, nebo 'Upravit' pojištěnce.
    :return object: Objekt HTTP odpovědi s přesměrováním na
požadovanou stránku.
    """

    slovnik_k_odeslani = {'formular': formular, 'status': status}

    return zobraz_stranku(
        request, adresa_stranky, slovnik_k_odeslani
    )

# ----------------------------------------------------------------------------
# -------------------------------- V I E W S ---------------------------------
# ----------------------------------------------------------------------------

def chyba_403(request, reason=""):
    """
    Zavolá se v případě, že dojde k chybě přihlášení (CSRF_TOKEN).
    """

    adresa_stranky = "chyba_403.html"
    return render(request, adresa_stranky)

def chyba_404(request, exception):
    """
    Zavolá se v případě, že uživatel zadá neexistující
URL adresu aplikace.
    """

    adresa_stranky = "chyba_404.html"
    return render(request, adresa_stranky)

def chyba_500(request):
    """
    Zavolá se v případě, že nastane interní chyba aplikace.
    """

    adresa_stranky = "chyba_500.html"
    return render(request, adresa_stranky)
    
def index(request: object) -> object:
    """
    Přesměruje na úvodní stránku aplikace.

    :param request object: Objekt HTTP dotazu.
    :return object: Přesměruje na úvodní stránku aplikace.
    """

    adresa_stranky = "evidence_pojisteni/index.html"
    return zobraz_stranku(request, adresa_stranky)

def o_aplikaci(request: object) -> object:
    """
    Přesměruje na stránku 'o_aplikaci'.

    :param request object: Objekt HTTP dotazu.
    :return object: Přesměruje na stránku 'o_aplikaci'.
    """

    adresa_stranky = "evidence_pojisteni/o_aplikaci.html"
    return zobraz_stranku(request, adresa_stranky)

def blog_index(request: object) -> object:
    """
    Přesměruje na stránku 'blog_index'.

    :param request object: Objekt HTTP dotazu.
    :return object: Přesměruje na stránku 'blog_index'.
    """

    adresa_stranky = "evidence_pojisteni/blog_index.html"
    return zobraz_stranku(request, adresa_stranky)

class AutorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset automatically provides `list` and `retrieve` actions.
    """
    queryset = Uzivatel.objects.filter(je_admin=True)
    serializer_class = Autor_serializer
    renderer_classes=[renderers.TemplateHTMLRenderer]

    def retrieve(self, request, pk, format=None):

        try:
            autor = self.get_object()
        except:
            messages.error(
                request, """Autor neexistuje! Nelze
                zobrazit jeho detail."""
            )
            return redirect('uzivatel-list')

        serializer = Autor_serializer(
            autor,
            context={'request': request}
        )

        return zobraz_stranku(
            request,
            adresa_stranky='evidence_pojisteni/detail_autora.html',
            slovnik_k_odeslani={
                'autor': serializer.data
            },
            trida_objektu=Clanek,
            seradit_co='seradit_detail_autora__clanky',
            seradit_podle='-id',
            django_rest=True 
        )

    def list(self, request, format=None):

        return zobraz_stranku(
            request,
            adresa_stranky='evidence_pojisteni/autori_index.html',
            slovnik_k_odeslani={},
            seradit_co='seradit_autori_index',
            seradit_podle='-id',
            trida_objektu=Uzivatel,
            django_rest=True
        )

class ClanekViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.

    Additionally we also provide an extra `highlight` action.
    """
    queryset = Clanek.objects.all()
    serializer_class = Clanek_serializer
    permission_classes = [
                            IsAdminOrReadOnly,
                            IsOwnerOrReadOnly
                         ]
    template_name = 'evidence_pojisteni/clanky_index.html'
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.TemplateHTMLRenderer
        ]

    def retrieve(self, request, pk, format=None):

        try:
            clanek = self.get_object()
        except:
            messages.error(
                request, """Článek neexistuje! Nelze
                zobrazit jeho detail."""
            )
            return redirect('clanek-list')

        serializer_clanek = Clanek_serializer(
            clanek,
            context={'request': request}
        )

        return Response(
            {
                'clanek': serializer_clanek.data,
                'serializer_clanek': serializer_clanek
            },
            template_name='evidence_pojisteni/detail_clanku.html'
        )

    def list(self, request, format=None):

        serializer_clanek = Clanek_serializer(
            None,
            context={'request': request}
        )

        return zobraz_stranku(
            request,
            adresa_stranky='evidence_pojisteni/clanky_index.html',
            slovnik_k_odeslani={
                'serializer_clanek': serializer_clanek
            },
            trida_objektu=Clanek,
            seradit_co='seradit_clanky_index',
            seradit_podle='-id',
            django_rest=True,
        )

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

class Pojistenci_index(generic.ListView):
    """Pohled pro stránku 'Pojištěnci'."""

    adresa_stranky = 'evidence_pojisteni/pojistenci_index.html'
    adresy_presmerovani = ['pojistenci_index']

    def get(self, request, seradit_podle):
        
        # Pokud je uživatel přihlášen jako administrátor, zobrazí se
        # při daném poždavku stránka 'Pojištěnci', pokud ne, zobrazí se
        # při požadavku úvodní stránka.
        if request.user.is_authenticated:

            if request.user.je_admin:
                slovnik_k_odeslani = {
                    'adresy_presmerovani': self.adresy_presmerovani,
                }

                return zobraz_stranku(
                    request, self.adresa_stranky,
                    slovnik_k_odeslani, 'seradit_pojistenci_index',
                    seradit_podle, Pojistenec
                )
        return redirect('index')

    def post(self, request, seradit_podle):
        if request.user.is_authenticated:
            presmerovani = presmeruj(request, self.adresy_presmerovani)

            if request.user.je_admin:

                if 'seradit' in request.POST:

                    if request.POST['seradit']:
                        seradit_podle = request.POST['seradit']
                        return redirect('pojistenci_index',
                            seradit_podle + '0'
                        )

                elif 'detail_pojistence' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojistence',
                        self.adresy_presmerovani, [0]
                    )

                elif ('odstranit' in request.POST and
                      'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění pojištěnce
                        zaškrtni potvrzovací políčko vedle
                        tlačítka 'Odstranit'."""
                    )

                elif 'odstranit' in request.POST:
                    if request.POST['odstranit']:
                        pk_pojistence = request.POST['odstranit']

                        try:
                            pojistenec = Pojistenec.objects.get(
                                pk = pk_pojistence
                            )
                        except:
                            messages.error(
                                request, """Pojištěnec {}
                                neexistuje! Nelze ho odstranit.
                                """.format(pk_pojistence)
                            )
                            return presmerovani

                        # Pokud se nám podaří načíst pojištěnce
                        # z databáze, odstraníme ho a odstraníme
                        # i jeho fotografii ze složky 'media/images/'.
                        #
                        # Podmínka určuje, že zkusíme mazat fotografii
                        # pouze, pokud je k dispozici.
                        # pojistenec.fotografie != False z důvodu, že
                        # vymazaná fotografie ze sekce 'Upravit' má
                        # stále název 'False' a pro Django existuje jako
                        # bool hodnota 'True'.
                        if (pojistenec.fotografie 
                            and pojistenec.fotografie != 'False'):

                            try:
                                os.remove(pojistenec.fotografie.path)
                            except:
                                messages.error(
                                    request, """Nepodařilo se odstranit
                                    fotografii pojištěnce ze složky."""
                                )

                        pojistenec.delete()
                        messages.success(
                            request, """Byl odstraněn pojištěnec {}
                            ({} {}) .""".format(
                                pk_pojistence, pojistenec.jmeno,
                                pojistenec.prijmeni
                            )
                        )

                elif 'upravit_pojistence' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'upravit_pojistence',
                        self.adresy_presmerovani, [0]
                    )
                return presmerovani
        return redirect('index')

class Novy_pojistenec(generic.edit.CreateView):
    """Pohled obsluhující tvorbu nového pojištěnce."""

    trida_formulare = Pojistenec_formular
    adresa_stranky = 'evidence_pojisteni/novy_pojistenec.html'
    primarni_klice = [0]

    def get(self, request, adresy_presmerovani):
        if request.user.is_authenticated:

            if request.user.je_admin:
                formular = self.trida_formulare(None)
                slovnik_k_odeslani = {"formular": formular, 'status': 'novy'}
                return zobraz_stranku(request, self.adresa_stranky,
                    slovnik_k_odeslani
                )

        return redirect('index')

    def post(self, request, adresy_presmerovani):
        if request.user.is_authenticated:
            adresy_presmerovani_pk = generuj_adresy_presmerovani(
                adresy_presmerovani, [0]
            )

            presmerovani = presmeruj(request, adresy_presmerovani_pk[0])

            if request.user.je_admin:

                if "zpet" in request.POST:
                    messages.info(request, "Pojištěnec nebyl vytvořen.")
                    return presmerovani

                formular = self.trida_formulare(request.POST, request.FILES)

                if formular.is_valid():
                    pojistenec = formular.save()

                    # Uloží pojištěnce jako uživatele.
                    uzivatel = Uzivatel()
                    uzivatel.email = pojistenec.email
                    uzivatel.pojistenec = pojistenec
                    uzivatel.set_password(str(pojistenec.pk))

                    # Pokud se nepodaří uložit pojištěnce jako
                    # uživatele, došlo k zadání emailu, který využívá
                    # administrátor aplikace nebo jiný uživatel,
                    # který není v roli pojištěnce.
                    try:
                        uzivatel.save()
                    except:
                        pojistenec.delete()
                        messages.error(
                            request, """Pojištěci se nepovedlo vytvořit
                            uživatelský účet. Akce byla zrušena
                            a pojištěnec nebyl vytvořen. Pravděpodobně
                            byl zadán email, který využívá jiný
                            uživatel aplikace."""
                        )

                        return zobraz_formular_znovu(
                            request, formular, self.adresa_stranky, 'novy'
                        )

                    messages.success(
                        request, """Byl vytvořen pojištěnec {}
                        ({} {}) včetně jeho uživatelského účtu.""".format(
                            pojistenec.pk, pojistenec.jmeno,
                            pojistenec.prijmeni
                        )
                    )

                    return presmerovani
                return zobraz_formular_znovu(
                    request, formular, self.adresa_stranky, 'novy'
                )
        return redirect('index')

class Upravit_pojistence(generic.edit.CreateView):
    """
    Pohled obsluhující úpravu pojištěnce. Je využit stejný formulář
i stejná stránka jako u tvorby nového pojištěnce.
    """

    trida_formulare = Pojistenec_formular
    adresa_stranky = 'evidence_pojisteni/novy_pojistenec.html'

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice
            )

            # Možnost upravit sebe sama má i přihlášený pojištěnec.
            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):

                try:
                    pojistenec = Pojistenec.objects.get(
                        pk = pk_pojistence
                    )
                except:
                    messages.error(
                        request, """Pojištěnec {} neexistuje! Nelze ho
                        upravit.""".format(pk_pojistence)
                    )
                    return presmerovani

                # Do formuláře k úpravě uložíme hodnoty daného pojištěnce.
                formular = self.trida_formulare(instance = pojistenec)
                slovnik_k_odeslani = {
                    'formular': formular, 'status': 'upravit',
                    'pk': pk_pojistence
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice
            )

            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):

                if "zpet" in request.POST:
                    messages.info(request, "Pojištěnec nebyl upraven.")
                    return presmerovani

                try:
                    pojistenec = Pojistenec.objects.get(pk = pk_pojistence)
                except:
                    messages.error(
                        request, """Pojištěnec {} neexistuje! Nelze
                        ho upravit.""".format(pk_pojistence)
                    )
                    return presmerovani

                # Do proměnné formulář se uloží nejen příchozí hodnoty
                # z formuláře od uživatele, ale i hodnoty, které
                # obsahoval daný pojištěnec před úpravou, aby bylo
                # možné zkontrolovat, zda došlo k nějaké změně.
                # Tato informace ovlivňuje nejen zprávu, kterou dostane
                # uživatel, ale i to, které údaje se v databázi přepíší,
                # aby se nepřepisovaly pokaždé automaticky všechny.
                formular = self.trida_formulare(
                        request.POST.copy(), request.FILES.copy(), initial = {
                            'jmeno': pojistenec.jmeno,
                            'prijmeni': pojistenec.prijmeni,
                            'ulice': pojistenec.ulice,
                            'mesto': pojistenec.mesto,
                            'psc': pojistenec.psc,
                            'email': pojistenec.email,
                            'telefon': pojistenec.telefon,
                            'fotografie': pojistenec.fotografie
                        }
                )

                # Pokud uživatel nezměnil při úpravě pojištěnce jeho
                # email a odešle formulář, metoda 'formular.is_valid()'
                # Vrátí chybu, protože nedovolí do tabulky 'pojištěnec'
                # uložit duplicitní email. Najde ho totiž u daného
                # pojištěnce, u kterého provádíme úpravu. Toto ošetříme
                # tak, že email násilně ve formuláři změníme, aby
                # nebyl považován za duplicitní. Tato změna se
                # nepodepíše na proměnné 'formular.changed_data',
                # protože ta je naplněna již při inicializaci objektu
                # 'formular' výše. A protože níže je ošetřeno, aby se
                # do databáze přepsala pouze ta data, která byla ve
                # formuláři změněna, je nám úplně jedno, jaký email zde
                # nastavíme, musí být pouze zvolen tak, aby byl
                # s jistotou originální.
                if 'email' not in formular.changed_data:
                    formular.data['email'] = 'originalni_adresa@pj.cz'

                # Pokud uživatel změnil fotografii, vymaže se stará.
                #
                # Podmínka určuje, že zkusíme mazat fotografii pouze,
                # pokud je k dispozici.
                # pojistenec.fotografie != False z důvodu, že vymazaná
                # fotografie ze sekce 'Upravit' má stále název 'False'
                # a pro Django existuje jako bool hodnota 'True'.
                if ('fotografie' in formular.changed_data 
                    and pojistenec.fotografie
                    and pojistenec.fotografie != 'False'):

                    try:
                        os.remove(pojistenec.fotografie.path)
                    except:
                        messages.error(
                            request, """Nepodařilo se odstranit fotografii
                            pojištěnce ze složky."""
                        )

                # Pokud je formulář v pořádku, objektu upravovaného
                # pojištěnce se načtou data z formuláře.
                if formular.is_valid():
                    pojistenec.jmeno = formular.cleaned_data["jmeno"]
                    pojistenec.prijmeni = formular.cleaned_data["prijmeni"]
                    pojistenec.ulice = formular.cleaned_data["ulice"]
                    pojistenec.mesto = formular.cleaned_data["mesto"]
                    pojistenec.psc = formular.cleaned_data["psc"]
                    pojistenec.email = formular.cleaned_data["email"]
                    pojistenec.telefon = formular.cleaned_data["telefon"]
                    pojistenec.fotografie = formular.cleaned_data[
                        "fotografie"
                    ]

                    # Protože Django nemá databázovou funkci
                    # 'ON UPDATE', přepíše se změna emailu pojištěnce
                    # i do k němu příslušnému uživateli ručně.
                    if 'email' in formular.changed_data:
                        uzivatel = Uzivatel.objects.get(
                            pojistenec = pojistenec
                        )
                        uzivatel.email = formular.cleaned_data["email"]

                        # Pokud se nepodaří upravit pojištěnce jako
                        # uživatele, došlo k zadání emailu, který využívá
                        # administrátor aplikace nebo jiný uživatel,
                        # který není v roli pojištěnce.
                        try:
                            uzivatel.save(update_fields = ['email'])

                            # Do databáze u daného pojištěnce se
                            # přepíšou pouze ta data, která byla
                            # změněna.
                        except:
                            messages.error(
                                request, """Pojištěci se nepovedlo upravit
                                uživatelský účet. Akce byla zrušena
                                a pojištěnec nebyl upraven. Pravděpodobně
                                byl zadán email, který využívá jiný
                                uživatel aplikace."""
                            )

                            return zobraz_formular_znovu(
                                request, formular, self.adresa_stranky,
                                'upravit'
                            )
                    pojistenec.save(update_fields=formular.changed_data)

                    if formular.has_changed():
                        messages.success(
                            request, """Byl upraven pojištěnec {} ({} {}).
                            """.format(
                                pojistenec.pk, pojistenec.jmeno,
                                pojistenec.prijmeni
                            )
                        )

                    else:
                        messages.info(
                            request, """Pojištěnec nebyl upraven. Žádná
                            změna neproběhla."""
                        )
                    return presmerovani

                return zobraz_formular_znovu(
                    request, formular, self.adresa_stranky, 'upravit'
                )
        return redirect('index')

class Detail_pojistence(generic.DetailView):
    """Pohled obsluhující detail pojištěnce."""

    adresa_stranky = 'evidence_pojisteni/detail_pojistence.html'

    def get (self, request, adresy_presmerovani, primarni_klice,
             seradit_podle):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_pojistence', True
            )

            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):
                try:
                    pojistenec = Pojistenec.objects.get(pk = pk_pojistence)
                except:
                    messages.error(
                        request, """Pojištěnec {} neexistuje! Nelze
                        zobrazit jeho detail.""".format(pk_pojistence)
                    )
                    return presmerovani

                slovnik_k_odeslani = {
                    "pojistenec": pojistenec,
                    'adresy_presmerovani': adresy_presmerovani,
                    'primarni_klice': primarni_klice
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani,
                    'seradit_detail_pojistence__pojisteni', seradit_podle,
                    Pojisteni
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice,
             seradit_podle):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_pojistence', True,
                ('odstranit_pojisteni' in request.POST or
                 'odstranit_potvrzeni' not in request.POST),
                'zpet' in request.POST,
                ('odstranit_pojistence' in request.POST and
                 'odstranit_potvrzeni' in request.POST)
            )

            adresy_presmerovani_pk = generuj_adresy_presmerovani(
                adresy_presmerovani, primarni_klice,'detail_pojistence'
            )
            adresy_presmerovani_ = adresy_presmerovani_pk[0]
            primarni_klice_ = adresy_presmerovani_pk[1]

            # Přihlášený pojištěnec a administrátor mají možnost
            # v detailu pojištěnce ovládat tlačítko zpět, řadit výčet
            # pojištění a upravit pojištěnce.
            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):

                if 'upravit_pojistence' in request.POST:
                    return redirect(
                        'upravit_pojistence', adresy_presmerovani_, primarni_klice_
                    )

                elif "zpet" in request.POST:
                    return presmerovani

                elif 'seradit' in request.POST:
                    if request.POST['seradit']:
                        seradit_podle = request.POST['seradit']

                        return redirect(
                            'detail_pojistence', adresy_presmerovani_,
                            primarni_klice_, seradit_podle + '0')

                elif 'detail_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'detail_pojisteni', adresy_presmerovani_,
                        primarni_klice_
                    )

            # Zbytek funkcionality může vykonat pouze administrátor.
            if request.user.je_admin:

                if ('odstranit_pojistence' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění pojištěnce zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif "odstranit_pojistence" in request.POST:
                    try:
                        pojistenec = Pojistenec.objects.get(
                            pk = pk_pojistence
                        )

                    except:
                        messages.error(
                            request, """Pojištěnec {} neexistuje! Nelze ho
                            odstranit.""".format(pk_pojistence)
                        )
                        return presmerovani

                    # Pokud se nám podaří načíst pojištěnce z databáze,
                    # odstraníme ho a odstraníme i jeho fotografii ze
                    # složky 'media/images/'.
                    #
                    # Podmínka určuje, že zkusíme mazat fotografii
                    # pouze, pokud je k dispozici.
                    # pojistenec.fotografie != False z důvodu, že
                    # vymazaná fotografie ze sekce 'Upravit' má
                    # stále název 'False' a pro Django existuje jako
                    # bool hodnota 'True'.
                    if (pojistenec.fotografie 
                        and pojistenec.fotografie != 'False'):

                        try:
                            os.remove(pojistenec.fotografie.path)
                        except:
                            messages.error(
                                request, """Nepodařilo se odstranit fotografii
                                pojištěnce ze složky."""
                            )
                    pojistenec.delete()

                    messages.success(
                        request, """Byl odstraněn pojištěnec {} ({} {}).
                        """.format(
                            pk_pojistence, pojistenec.jmeno,
                            pojistenec.prijmeni
                        )
                    )
                    return presmerovani

                elif ('odstranit_pojisteni' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění pojištění zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif "odstranit_pojisteni" in request.POST:
                    if request.POST["odstranit_pojisteni"]:
                        pk_pojisteni = request.POST["odstranit_pojisteni"]

                        try:
                            pojisteni = Pojisteni.objects.get(
                                pk = pk_pojisteni
                            )

                        except:
                            messages.error(
                                request, """Pojištění {} neexistuje, nelze
                                jej vymazat!""". format(pk_pojisteni)
                            )
                            return presmerovani

                        pojisteni.delete()
                        messages.success(
                            request, """Bylo odstraněno pojištění {}
                            ({}, {} Kč)""".format(pk_pojisteni,
                                    pojisteni.typ.typ, pojisteni.castka
                            )
                        )

                elif 'upravit_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'upravit_pojisteni',
                        adresy_presmerovani_,
                        primarni_klice_
                    )

                elif "pridat_pojisteni" in request.POST:
                    return redirect(
                        'nove_pojisteni', adresy_presmerovani_,
                        primarni_klice_
                    )
                return presmerovani

        return redirect('index')

class Pojisteni_index(generic.ListView):
    """Pohled obsluhuje stránku 'Pojištění'."""

    adresa_stranky = 'evidence_pojisteni/pojisteni_index.html'
    adresy_presmerovani = ['pojisteni_index']

    def get(self, request, seradit_podle):
        if request.user.is_authenticated:

            if request.user.je_admin or request.user.pojistenec:
                slovnik_k_odeslani = {
                    'adresy_presmerovani': self.adresy_presmerovani
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani,
                    'seradit_pojisteni_index', seradit_podle, Pojisteni
                )
        return redirect('index')

    def post(self, request, seradit_podle):
        if request.user.is_authenticated:
            presmerovani = presmeruj(request, self.adresy_presmerovani)

            if request.user.je_admin or request.user.pojistenec:

                if 'seradit' in request.POST:

                    if request.POST['seradit']:
                        seradit_podle = request.POST['seradit']
                        return redirect(
                            'pojisteni_index', seradit_podle + '0'
                        )

                elif 'detail_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojisteni',
                        self.adresy_presmerovani, [0]
                    )

                elif 'detail_pojistence' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojistence',
                        self.adresy_presmerovani, [0]
                    )

            if request.user.je_admin:

                if ('odstranit' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění pojištění zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif 'odstranit' in request.POST:

                    if request.POST['odstranit']:
                        pk_pojisteni = request.POST['odstranit']

                        try:
                            pojisteni = Pojisteni.objects.get(
                                pk = pk_pojisteni
                            )

                        except:
                            messages.error(
                                request, """Pojištění {} neexistuje! Nelze
                                ho odstranit.""".format(pk_pojisteni)
                            )
                            return presmerovani

                        pojisteni.delete()
                        messages.success(
                            request, """Bylo odstraněno pojištění{}
                            ({}, {} Kč)""".format(
                                pk_pojisteni, pojisteni.typ.typ,
                                pojisteni.castka
                            )
                        )
                elif 'upravit_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'upravit_pojisteni',
                        self.adresy_presmerovani,
                        [0]
                    )
                return presmerovani

        return redirect('index')

class Nove_pojisteni(generic.edit.CreateView):
    """Pohled obsluhující tvorbu nového pojištění."""

    adresa_stranky = 'evidence_pojisteni/nove_pojisteni.html'
    trida_formulare = Pojisteni_formular

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            if request.user.je_admin:

                # Pokud tvoříme nové pojištění z detailu pojištěnce
                # (pk_pojistence != 0), předvyplníme ve formuláři
                # nového pojištění příslušnost k danému pojištěnci.
                # Toto pole rovněž uvedeme do stavu, aby ho nešlo
                # změnit.
                if pk_pojistence != 0:
                    formular = self.trida_formulare(initial = {
                        'pojistenec': pk_pojistence
                        }
                    )
                    p = formular.fields['pojistenec']
                    p.widget.attrs['disabled'] = 'disabled'

                else:
                    formular = self.trida_formulare(None)
                slovnik_k_odeslani = {'formular': formular, 'status': 'nove'}

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-1]
            except:
                pk_pojistence = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            if request.user.je_admin:
                if 'zpet' in request.POST:
                    messages.info(request, "Pojištění nebylo uloženo.")

                    return presmerovani

                hodnoty_formulare = request.POST.dict()

                # Pokud jsme do formuláře nového pojištění přistoupily
                # z detailu pojištěnce a odeslaly ho, neodeslal se nám
                # údaj o příslušnosti pojištění k pojištěnci, protože
                # pole bylo nastaveno na 'disabled'.
                # Musíme tedy nyní onu informaci doplnit.
                if pk_pojistence != 0:
                    hodnoty_formulare.update({'pojistenec': pk_pojistence})
                formular = self.trida_formulare(hodnoty_formulare)

                if formular.is_valid():
                    pojisteni = formular.save()
                    messages.success(
                        request, """Bylo uloženo pojištění {}
                        ({}, {} Kč)""".format(
                            pojisteni.pk, pojisteni.typ.typ,
                            pojisteni.castka
                        )
                    )
                    return presmerovani

                slovnik_k_odeslani = {'formular': formular, 'status': 'nove'}

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

class Upravit_pojisteni(generic.edit.CreateView):
    """
    Pohled obsluhující úpravu pojištění. Je využit stejný formulář
i stejná stránka jako u tvorby nového pojištění.
    """

    adresa_stranky = "evidence_pojisteni/nove_pojisteni.html"
    trida_formulare = Pojisteni_formular

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)
            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            if request.user.je_admin:
                try:
                    pojisteni = Pojisteni.objects.get(pk = pk_pojisteni)
                except:
                    messages.error(
                        request, """Pojištění {} neexistuje! Nelze ho
                        upravit.""".format(pk_pojisteni)
                    )
                    return presmerovani

                formular = self.trida_formulare(instance = pojisteni)
                slovnik_k_odeslani = {
                    'formular': formular, 'status': 'upravit',
                    'pk': pk_pojisteni
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)

            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            if request.user.je_admin:

                if 'zpet' in request.POST:
                    messages.info(request, "Pojištění nebylo upraveno.")
                    return presmerovani

                formular = self.trida_formulare(request.POST)

                if formular.is_valid():
                    try:
                        pojisteni = Pojisteni.objects.get(pk = pk_pojisteni)
                    except:
                        messages.error(
                            request, """Pojištění {} neexistuje! Nelze ho
                            upravit.""".format(pk_pojisteni)
                        )
                        return presmerovani

                    # Uloží pojištěnce příslušícího k danému pojištění před
                    # případnou změnou. Využijeme dále v kódu.
                    pojistenec = pojisteni.pojistenec

                    # Do proměnné formulář se uloží nejen příchozí
                    # hodnoty z formuláře od uživatele, ale i hodnoty,
                    # které obsahovalo dané pojištění před úpravou, aby
                    # bylo možné zkontrolovat, zda došlo k nějaké změně.
                    # Tato informace ovlivňuje nejen zprávu, kterou
                    # dostane uživatel, ale i to, které údaje se
                    # v databázi přepíší, aby se nepřepisovaly pokaždé
                    # automaticky všechny.
                    formular.initial = {
                        'pojistenec': pojisteni.pojistenec,
                        'typ': pojisteni.typ,
                        'castka': pojisteni.castka,
                        'predmet': pojisteni.predmet,
                        'platnost_od': pojisteni.platnost_od,
                        'platnost_do': pojisteni.platnost_do
                    }
        
                    pojisteni.pojistenec = formular.cleaned_data['pojistenec']
                    pojisteni.typ = formular.cleaned_data['typ']
                    pojisteni.castka = formular.cleaned_data['castka']
                    pojisteni.predmet = formular.cleaned_data['predmet']
                    pojisteni.platnost_od = formular.cleaned_data[
                        'platnost_od'
                    ]
                    pojisteni.platnost_do = formular.cleaned_data[
                        'platnost_do'
                    ]

                    # Uloží se pouze ty hodnoty, které byly změněny.
                    pojisteni.save(update_fields=formular.changed_data)

                    # Pokud jsme pojištění přiřadily jinému pojištěnci,
                    # změní se pojijištěnec i u všech pojistných
                    # událostí, které náleží danému pojištění.
                    if 'pojistenec' in formular.changed_data:
                        udalosti = Udalost.objects.filter(
                            pojistenec = pojistenec
                        )

                        for udalost in udalosti:
                            udalost.pojistenec = pojisteni.pojistenec
                            udalost.save(update_fields=['pojistenec'])

                    if formular.has_changed():
                        messages.success(
                            request, """Bylo upraveno pojištění {}
                            ({}, {} Kč)""".format(
                                pojisteni.pk, pojisteni.typ.typ,
                                pojisteni.castka
                            )
                        )

                    else:
                        messages.info(
                            request, """Pojištění nebylo upraveno. Žádná
                            změna neproběhla."""
                        )
                    return presmerovani

                slovnik_k_odeslani = {
                    'formular': formular, 'status': 'upravit'
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

class Detail_pojisteni(generic.DetailView):
    """Pohled obsluhující detail pojištění."""
    adresa_stranky = 'evidence_pojisteni/detail_pojisteni.html'

    def get(self, request, adresy_presmerovani, primarni_klice,
            seradit_podle):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-2]
            except:
                pk_pojistence = 0

            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_pojisteni', True,
            )

            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):

                try:
                    pojisteni = Pojisteni.objects.get(pk = pk_pojisteni)
                except:
                    messages.error(
                        request, """Pojištění {} neexistuje! Nelze
                        zobrazit jeho detail.""".format(pk_pojisteni)
                    )
                    return presmerovani

                # Pro zobrazení datumů měníme jejich formát,
                # aby lépe vypadaly.
                platnost = {
                    'od': pojisteni.platnost_od.strftime("%d.%m.%Y"),
                    'do': pojisteni.platnost_do.strftime("%d.%m.%Y")
                }

                slovnik_k_odeslani = {
                    'pojisteni': pojisteni,
                    'platnost': platnost,
                    'adresy_presmerovani': adresy_presmerovani,
                    'primarni_klice': primarni_klice
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani,
                    'seradit_detail_pojisteni__udalosti', seradit_podle,
                    Udalost
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice,
             seradit_podle):

        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojistence = primarni_klice[-2]
            except:
                pk_pojistence = 0

            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_pojisteni', True,
                ('odstranit_udalost' in request.POST or
                 'odstranit_potvrzeni' not in request.POST),
                'zpet' in request.POST,
                ('odstranit_pojisteni' in request.POST and
                 'odstranit_potvrzeni' in request.POST)
            )

            adresy_presmerovani_pk = generuj_adresy_presmerovani(
                adresy_presmerovani, primarni_klice, 'detail_pojisteni'
            )
            adresy_presmerovani_ = adresy_presmerovani_pk[0]
            primarni_klice_ = adresy_presmerovani_pk[1]

            if (request.user.je_admin or
                request.user.pojistenec.id == pk_pojistence):

                if 'zpet' in request.POST:
                    return presmerovani

                elif 'seradit' in request.POST:

                    if request.POST['seradit']:
                        seradit_podle = request.POST['seradit']

                        return redirect(
                            'detail_pojisteni', adresy_presmerovani_,
                            primarni_klice_, seradit_podle + '0'
                        )

                elif 'detail_pojistence' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojistence',
                        adresy_presmerovani_, primarni_klice_,
                    )

                elif 'detail_udalosti' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_udalosti',
                        adresy_presmerovani_, primarni_klice_,
                    )

            if request.user.je_admin:

                if ('odstranit_pojisteni' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění pojištění zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif 'odstranit_pojisteni' in request.POST:
                    try:
                        pojisteni = Pojisteni.objects.get(pk = pk_pojisteni)
                    except:
                        messages.error(
                            request, """Pojištění {} neexistuje! Nelze ho
                            odstranit.""".format(pk_pojisteni)
                        )
                        return presmerovani

                    pojisteni.delete()
                    messages.success(
                        request, """Bylo odstraněno pojištění {}
                        ({}, {} Kč)""".format(
                            pk_pojisteni, pojisteni.typ.typ,
                            pojisteni.castka
                        )
                    )

                elif 'upravit_pojisteni' in request.POST:
                    return redirect(
                        'upravit_pojisteni', adresy_presmerovani_,
                        primarni_klice_,
                    )

                elif 'pridat_udalost' in request.POST:
                    return redirect(
                        'nova_udalost', adresy_presmerovani_,
                        primarni_klice_,
                    )

                elif ('odstranit_udalost' in request.POST and
                      'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění události zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif 'odstranit_udalost' in request.POST:

                    if request.POST["odstranit_udalost"]:
                        pk_udalosti = request.POST["odstranit_udalost"]

                        try:
                            udalost = Udalost.objects.get(pk=pk_udalosti)
                        except:
                            messages.error(
                                request, """Událost {} neexistuje, nelze
                                jej vymazat!""". format(pk_udalosti)
                            )
                            return presmerovani

                        udalost.delete()
                        messages.success(
                            request, """Byla odstraněna událost {}
                            ({}, {} Kč)""".format(pk_udalosti,
                            udalost.predmet, udalost.castka)
                        )

                elif 'upravit_udalost' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'upravit_udalost', adresy_presmerovani_,
                        primarni_klice_,
                    )
                return presmerovani

        return redirect('index')

class Udalosti_index(generic.ListView):
    """Pohled obsluhuje stránku 'Události'."""

    adresa_stranky = 'evidence_pojisteni/udalosti_index.html'
    adresy_presmerovani = ['udalosti_index']

    def get(self, request, seradit_podle):
        if request.user.is_authenticated:

            if request.user.je_admin or request.user.pojistenec:
                slovnik_k_odeslani = {
                    'adresy_presmerovani': self.adresy_presmerovani
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani,
                    'seradit_udalosti_index', seradit_podle, Udalost
                )
        return redirect('index')

    def post(self, request, seradit_podle):
        if request.user.is_authenticated:
            presmerovani = presmeruj(request, self.adresy_presmerovani)

            if request.user.je_admin or request.user.pojistenec:

                if 'seradit' in request.POST:

                    if request.POST['seradit']:
                        seradit_podle = request.POST['seradit']
                        return redirect('udalosti_index', seradit_podle + '0')

                elif 'detail_udalosti' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_udalosti',
                        self.adresy_presmerovani, [0]
                    )

                elif 'detail_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojisteni',
                        self.adresy_presmerovani, [0]
                    )

                elif 'detail_pojistence' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojistence',
                        self.adresy_presmerovani, [0]
                    )

            if request.user.je_admin:

                if ('odstranit' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):

                    messages.info(
                        request, """Pro odstranění události zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif 'odstranit' in request.POST:

                    if request.POST['odstranit']:
                        pk = request.POST['odstranit']

                        try:
                            udalost = Udalost.objects.get(pk = pk)
                        except:
                            messages.error(
                                request, """Událost {} neexistuje! Nelze
                                ji odstranit.""".format(pk)
                            )
                            return presmerovani

                        udalost.delete()
                        messages.success(
                            request, """Byla odstraněna událost {}
                            ({}, {} Kč)""".format(
                                pk, udalost.predmet, udalost.castka
                            )
                        )

                elif 'upravit_udalost' in request.POST:
                    return jdi_na_detail_upravit(
                        request, 'upravit_udalost', self.adresy_presmerovani,
                        [0]
                    )
                return presmerovani

        return redirect('index')

class Nova_udalost(generic.edit.CreateView):
    """Pohled obsluhuje tvorbu nové události."""

    adresa_stranky = 'evidence_pojisteni/nova_udalost.html'
    trida_formulare = Udalost_formular

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:
            primarni_klice = eval(primarni_klice)

            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            if request.user.je_admin:

                # Pokud tvoříme novou událost z detailu pojištění
                # (pk_pojisteni != 0), předvyplníme ve formuláři nové
                # události příslušnost k danému pojištění. Toto pole
                # rovněž uvedeme do stavu, aby ho nešlo změnit.
                if pk_pojisteni != 0:
                    formular = self.trida_formulare(initial={
                        'pojisteni': pk_pojisteni
                        }
                    )
                    p = formular.fields['pojisteni']
                    p.widget.attrs['disabled'] = 'disabled'

                else:
                    formular = self.trida_formulare(None)
                slovnik_k_odeslani = {'formular': formular, 'status': 'nova'}

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )

        return redirect('index')
    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)

            try:
                pk_pojisteni = primarni_klice[-1]
            except:
                pk_pojisteni = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            if request.user.je_admin:

                if 'zpet' in request.POST:
                    messages.info(request, "Událost nebyla vytvořena.")
                    return presmerovani
                hodnoty_formulare = request.POST.dict()

                # Pokud jsme do formuláře nové události přistoupily
                # z detailu pojištění a odeslaly ho, neodeslal se nám
                # údaj o příslušnosti události k pojištění, protože
                # pole bylo nastaveno na 'disabled'.
                # Musíme tedy nyní onu informaci doplnit.
                if pk_pojisteni != 0:
                    hodnoty_formulare.update({'pojisteni': pk_pojisteni})
                formular = self.trida_formulare(hodnoty_formulare)

                if formular.is_valid():

                    # U Tvorby nebo úpravy pojistné události neurčujeme
                    # příslušnost k pojištěnci, ale pouze k pojištění.
                    # Musíme tedy tuto informaci doplnit.
                    udalost = formular.save(commit=False)
                    udalost.pojistenec = udalost.pojisteni.pojistenec
                    udalost.save()
                    messages.success(
                        request, """Byla uložena událost {}
                        ({}, {} Kč)""".format(
                            udalost.pk, udalost.predmet,
                            udalost.castka
                        )
                    )
                    return presmerovani

                slovnik_k_odeslani = {'formular': formular, 'status': 'nova'}

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

class Upravit_udalost(generic.edit.CreateView):
    """
    Pohled obsluhující úpravu události. Je využit stejný formulář
i stejná stránka jako u tvorby nové události.
    """

    adresa_stranky = "evidence_pojisteni/nova_udalost.html"
    trida_formulare = Udalost_formular

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)
            try:
                pk_udalosti = primarni_klice[-1]
            except:
                pk_udalosti = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            if request.user.je_admin:
                try:
                    udalost = Udalost.objects.get(pk = pk_udalosti)
                except:
                    messages.error(
                        request, """Událost {} neexistuje! Nelze jí
                        upravit.""".format(pk_udalosti)
                    )
                    return presmerovani

                formular = self.trida_formulare(instance = udalost)
                slovnik_k_odeslani = {
                    'formular': formular,
                    'status': 'upravit',
                    'pk': pk_udalosti
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)

            try:
                pk_udalosti = primarni_klice[-1]
            except:
                pk_udalosti = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
            )

            try:
                udalost = Udalost.objects.get(pk = pk_udalosti)
            except:
                messages.error(
                    request, """Událost {} neexistuje! Nelze ji upravit.
                    """.format(pk_udalosti)
                )
                return presmerovani

            if request.user.je_admin:

                if 'zpet' in request.POST:
                    messages.info(request, "Událost nebyla upravena.")
                    return presmerovani
                formular = self.trida_formulare(request.POST)

                if formular.is_valid():

                    # Do proměnné formulář se uloží nejen příchozí
                    # hodnoty z formuláře od uživatele, ale i hodnoty,
                    # které obsahovala daná událost před úpravou, aby
                    # bylo možné zkontrolovat, zda došlo k nějaké
                    # změně. Tato informace ovlivňuje nejen zprávu,
                    # kterou dostane uživatel, ale i to, které údaje se
                    # v databázi přepíší, aby se nepřepisovaly
                    # pokaždé automaticky všechny.
                    formular.initial = {
                        'pojisteni': udalost.pojisteni,
                        'castka': udalost.castka,
                        'predmet': udalost.predmet,
                        'datum': udalost.datum,
                        'popis': udalost.popis
                    }

                    udalost.pojistenec = formular.cleaned_data[
                        'pojisteni'
                    ].pojistenec
                    udalost.pojisteni = formular.cleaned_data['pojisteni']
                    udalost.castka = formular.cleaned_data['castka']
                    udalost.predmet = formular.cleaned_data['predmet']
                    udalost.datum = formular.cleaned_data['datum']
                    udalost.popis = formular.cleaned_data['popis']
                    upravit_pole = formular.changed_data

                    # Pokud byla událost přiřazena jinému pojištění,
                    # přidá se do změněných údajů také pojištěnec,
                    # aby se s ním počítalo při ukládání změněných údajů.
                    if 'pojisteni' in formular.changed_data:
                        upravit_pole = formular.changed_data.append(
                            'pojistenec'
                        )
                    udalost.save(update_fields=upravit_pole)

                    if formular.has_changed():
                        messages.success(
                            request, """Byla upravena událost {}
                            ({}, {} Kč)""".format(
                                udalost.pk, udalost.predmet,
                                udalost.castka
                            )
                        )

                    else:
                        messages.info(
                            request, """Událost nebyla upravena.
                            Žádná změna neproběhla."""
                        )
                    return presmerovani

                slovnik_k_odeslani = {
                    'formular': formular,
                    'status': 'upravit'
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

class Detail_udalosti(generic.DetailView):
    """Pohled obsluhující detail události."""

    adresa_stranky = 'evidence_pojisteni/detail_udalosti.html'

    def get(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)
            try:
                pk_udalosti = primarni_klice[-1]
            except:
                pk_udalosti = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_udalosti', True
            )

            try:
                udalost = Udalost.objects.get(pk = pk_udalosti)
            except:
                messages.error(
                    request, """Událost {} neexistuje! Nelze zobrazit její
                    detail.""".format(pk_udalosti)
                )
                return presmerovani

            if (request.user.je_admin or
                request.user.pojistenec == udalost.pojistenec):
                # Pro zobrazení datumů měníme jejich formát, aby lépe vypadaly.
                datum = udalost.datum.strftime("%d.%m.%Y")
                slovnik_k_odeslani = {
                    'udalost': udalost,
                    'datum': datum,
                    'adresy_presmerovani': adresy_presmerovani,
                    'primarni_klice': primarni_klice
                }

                return zobraz_stranku(
                    request, self.adresa_stranky, slovnik_k_odeslani
                )
        return redirect('index')

    def post(self, request, adresy_presmerovani, primarni_klice):
        if request.user.is_authenticated:

            primarni_klice = eval(primarni_klice)
            try:
                pk_udalosti = primarni_klice[-1]
            except:
                pk_udalosti = 0

            presmerovani = generuj_presmerovani(
                request, adresy_presmerovani, primarni_klice,
                'detail_udalosti', True,
                'odstranit_potvrzeni' not in request.POST,
                'zpet' in request.POST,
                ('odstranit_udalost' in request.POST and
                 'odstranit_potvrzeni' in request.POST)
            )

            adresy_presmerovani_pk = generuj_adresy_presmerovani(
                adresy_presmerovani, primarni_klice, 'detail_udalosti'
            )
            adresy_presmerovani_ = adresy_presmerovani_pk[0]
            primarni_klice_ = adresy_presmerovani_pk[1]

            try:
                udalost = Udalost.objects.get(pk = pk_udalosti)
            except:
                messages.error(
                    request, "Událost {} neexistuje!".format(pk_udalosti)
                )
                return presmerovani

            if (request.user.je_admin or
                request.user.pojistenec == udalost.pojistenec):

                if 'zpet' in request.POST:
                    return presmerovani

                elif 'detail_pojistence' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojistence',
                        adresy_presmerovani_, primarni_klice_
                    )

                elif 'detail_pojisteni' in request.POST:
                    return jdi_na_detail_upravit(request, 'detail_pojisteni',
                        adresy_presmerovani_, primarni_klice_
                    )

            if request.user.je_admin:

                if ('odstranit_udalost' in request.POST and
                    'odstranit_potvrzeni' not in request.POST):
                    messages.info(
                        request, """Pro odstranění události zaškrtni
                        potvrzovací políčko vedle tlačítka 'Odstranit'."""
                    )

                elif 'odstranit_udalost' in request.POST:
                    udalost.delete()
                    messages.success(
                        request, """Byla odstraněna událost {}
                        ({}, {} Kč)""".format(
                            pk_udalosti, udalost.predmet,
                            udalost.castka
                        )
                    )
                    return presmerovani

                elif 'upravit_udalost' in request.POST:
                    return redirect(
                        'upravit_udalost', adresy_presmerovani_,
                        primarni_klice_
                    )
                return presmerovani

        return redirect('index')

class Prihlasit_uzivatele(generic.edit.CreateView):
    """Pohled obsluhující přihlášení nového uživatele."""

    adresa_stranky = 'evidence_pojisteni/prihlasit_uzivatele.html'
    trida_formulare = Uzivatel_prihlaseni_formular

    def get(self, request):
        if request.user.is_authenticated:
            messages.info(
                request, """Nemůžeš se přihlásit, protože už jsi
                přihlášený. Nejrve se odhlaš."""
            )

        else:
            formular = self.trida_formulare(None)
            slovnik_k_odeslani = {"formular": formular}
            return zobraz_stranku(
                request, self.adresa_stranky, slovnik_k_odeslani
            )
        return redirect ('index')

    def post(self, request):
        if request.user.is_authenticated:
            messages.info(
                request, """Nemůžeš se přihlásit, protože už jsi
                přihlášený. Nejrve se odhlaš."""
            )
            return redirect("index")

        formular = self.trida_formulare(request.POST)

        if formular.is_valid():
            email = formular.cleaned_data["email"]
            heslo = formular.cleaned_data["heslo"]
            user = authenticate(email = email, password = heslo)

            if user:
                login(request, user)
                messages.success(
                    request, "Uživatel {} byl přihlášen.".format(
                        user.email
                    )
                )
                return redirect("index")

            else:
                messages.error(request, "Chybný email nebo heslo.")

        slovnik_k_odeslani = {"formular": formular}

        return zobraz_stranku(
            request, self.adresa_stranky, slovnik_k_odeslani
        )

def odhlasit_uzivatele(request):
    """Pohled obsluhující odhlášení uživatele."""

    if request.user.is_authenticated:
        email_uzivatele = request.user.email
        logout(request)
        messages.success(request, "Uživatel {} byl odhlášen.".format(
            email_uzivatele
            )
        )

    else:
        messages.info(
            request, "Nemůžeš se odhlásit, protože nejsi přihlášený."
        )
    return redirect('prihlasit_uzivatele')