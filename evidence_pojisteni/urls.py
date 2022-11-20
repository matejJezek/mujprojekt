"""mujprojekt URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from . import views
from django.urls import path

urlpatterns = [
    # Index, o aplikaci
    path('', views.index, name='index'),
    path('o_aplikaci/', views.o_aplikaci, name='o_aplikaci'),
    
    # Pojistenci
    path(
        'pojistenci_index/<seradit_podle>',
        views.Pojistenci_index.as_view(),
        name='pojistenci_index' 
    ),
    path(
        'novy_pojistenec/<adresy_presmerovani>',
        views.Novy_pojistenec.as_view(),
        name='novy_pojistenec'
    ),
    path(
        'upravit_pojistence/<adresy_presmerovani>/<primarni_klice>',
        views.Upravit_pojistence.as_view(),
        name='upravit_pojistence'
    ),
    path(
        'detail_pojistence/<adresy_presmerovani>/<primarni_klice>/<seradit_podle>',
        views.Detail_pojistence.as_view(),
        name='detail_pojistence'
    ),

    # Pojisteni
    path(
        'pojisteni_index/<seradit_podle>',
        views.Pojisteni_index.as_view(),
        name='pojisteni_index'
    ),
    path(
        'nove_pojisteni/<adresy_presmerovani>/<primarni_klice>',
        views.Nove_pojisteni.as_view(),
        name='nove_pojisteni'
    ),
    path(
        'upravit_pojisteni/<adresy_presmerovani>/<primarni_klice>',
        views.Upravit_pojisteni.as_view(),
        name='upravit_pojisteni'
    ),
    path(
        'detail_pojisteni/<adresy_presmerovani>/<primarni_klice>/<seradit_podle>',
        views.Detail_pojisteni.as_view(),
        name='detail_pojisteni'
    ),

    # Udalosti
    path(
        'udalosti_index/<seradit_podle>',
        views.Udalosti_index.as_view(),
        name='udalosti_index'
    ),
    path(
        'nova_udalost/<adresy_presmerovani>/<primarni_klice>',
        views.Nova_udalost.as_view(),
        name='nova_udalost'
    ),
    path(
        'upravit_udalost/<adresy_presmerovani>/<primarni_klice>',
        views.Upravit_udalost.as_view(),
        name='upravit_udalost'
    ),
    path(
        'detail_udalosti/<adresy_presmerovani>/<primarni_klice>',
        views.Detail_udalosti.as_view(),
        name='detail_udalosti'
    ),

    # Uzivatel
    path(
        'prihlasit_uzivatele/',
        views.Prihlasit_uzivatele.as_view(),
        name='prihlasit_uzivatele'
    ),
    path(
        'odhlasit_uzivatele/',
        views.odhlasit_uzivatele,
        name='odhlasit_uzivatele'
    ),
]