from django import forms
from .models import Pojistenec, Pojisteni, Udalost, Uzivatel

class Pojistenec_formular (forms.ModelForm):
    class Meta:
        model = Pojistenec
        fields = [
            "jmeno", "prijmeni", "ulice", "mesto", "psc",
            "email", "telefon", "fotografie"
        ]
        widgets = {
            'jmeno': forms.TextInput(
                attrs={'placeholder': 'Karel'}
            ),
            'prijmeni': forms.TextInput(
                attrs={'placeholder': 'Novák'}
            ),
            'ulice': forms.TextInput(
                attrs={'placeholder': 'U Lesíka 615'}
            ),
            'mesto': forms.TextInput(
                attrs={'placeholder': 'Praha 2'}
            ),
            'psc': forms.TextInput(
                attrs={'placeholder': '12345'}
            ),
            'email': forms.EmailInput(
                attrs={'placeholder': 'karel.novak@email.cz'}
            ),
            'telefon': forms.TextInput(
                attrs={'placeholder': '606636939'}
            )
        }

class DateInput(forms.DateInput):
    input_type = 'date'

class Pojisteni_formular(forms.ModelForm):
    platnost_od = forms.DateField(
        widget=DateInput
    )
    platnost_do = forms.DateField(
        widget = forms.DateInput(
            attrs={'type': 'date'}
        )
    )
    
    class Meta:
        model = Pojisteni
        fields = [
            'pojistenec', 'typ', 'castka', 'predmet',
            'platnost_od', 'platnost_do'
        ]
        widgets = {
            'castka': forms.NumberInput(
                attrs={'placeholder': '3000000'}
            ),
            'predmet': forms.TextInput(
                attrs={'placeholder': 'Automobil Škoda Octavia'}
            ),
        }

class Udalost_formular(forms.ModelForm):
    datum = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date'}
        )
    )
    
    class Meta:
        model = Udalost
        fields=[
            'pojisteni', 'castka', 'predmet', 'datum', 'popis'
        ]
        widgets = {
            'castka': forms.NumberInput(
                attrs={'placeholder': '5000'}
            ),
            'predmet': forms.TextInput(
                attrs={'placeholder': 'Poškrábané dveře'}
            ),
        }

class Uzivatel_prihlaseni_formular(forms.Form):
    email = forms.EmailField(
        label='Email'
    )
    heslo = forms.CharField(
        widget=forms.PasswordInput()
    )
    
    class Meta:
        fields = ["email", "heslo"]