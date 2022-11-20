from django.contrib import admin
from .models import Uzivatel, UzivatelManager, Pojistenec, Pojisteni
from .models import Typ_pojisteni, Udalost
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
# Register your models here.

class Novy_uzivatel_Formular(forms.ModelForm):
    heslo = forms.CharField(label='heslo', widget=forms.PasswordInput)

    class Meta:
        model = Uzivatel
        fields = ['email', 'heslo', 'pojistenec', 'je_admin']

    def save(self, commit=True):
        if self.is_valid():
            user = super().save(commit=False)
            user.set_password(self.cleaned_data["heslo"])

            if commit:
                user.save()
            return user

class Upravit_uzivatele_Formular(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Uzivatel
        fields = ['email', 'password', 'pojistenec', 'je_admin']

    def __init__(self, *args, **kwargs):
        super(Upravit_uzivatele_Formular, self).__init__(*args, **kwargs)
        #self.Meta.fields.remove('password')

class Uzivatel_admin(UserAdmin):
    form = Upravit_uzivatele_Formular
    add_form = Novy_uzivatel_Formular

    list_display = ['email', 'je_admin']
    list_filter = ['je_admin']
    fieldsets = (
        (None, {'fields': ['email', 'password', 'pojistenec']}),
        ('Permissions', {'fields': ['je_admin']}),
    )

    add_fieldsets = (
        (None, {'fields': ['email', 'heslo', 'pojistenec']}),
        ('Permissions', {'fields': ['je_admin']}),
    )
    search_fields = ['email']
    ordering = ['email']
    filter_horizontal = []
    
# Registrace modelu 'Uzivatel'. Tento model slouží pro správu uživatelů
# aplikace 'evidence_pojisteni'.
admin.site.register(Uzivatel, Uzivatel_admin)
admin.site.register(Pojistenec)
admin.site.register(Pojisteni)
admin.site.register(Typ_pojisteni)
admin.site.register(Udalost)
