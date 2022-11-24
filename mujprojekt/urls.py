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
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from . import settings
from django.conf.urls.static import static

favicon_view = RedirectView.as_view(
    url=settings.STATIC_URL + 'evidence_pojisteni/favicon.ico',
    permanent=True
)

urlpatterns = [
    # Pro tvorbu dokumentace.
    path(
        'admin/doc/',
        include('django.contrib.admindocs.urls')
    ),

    # Cesta ke správě databáze.
    path(
        'admin/',
        admin.site.urls
    ),

    # Cesta k aplikaci 'evidence_pojisteni' (neboli k modulu, který
    # konfiguruje její URL cesty).
    path(
        '',
        include('evidence_pojisteni.urls')
    ),

    #     path(
    #     'http://pojistovna-jezek-5973.rostiapp.cz/',
    #     include('evidence_pojisteni.urls')
    # ),

    re_path(
        r'^favicon\.ico$',
        favicon_view
    ),
]

# Pro práci s fotografiemi
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

# Přesměrování z neexistující URL adresy aplikace.
handler404 = 'evidence_pojisteni.views.chyba_404'