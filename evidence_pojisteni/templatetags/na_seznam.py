""" 
    Modul na_seznam obsahuje filtry pro práci s PYTHON objekty
v templates.
    filtr 'preved_na_seznam' vloží hodnotu proměnné do seznamu
a ten vrátí.
"""
from django import template

register = template.Library()

@register.filter
def preved_na_seznam(hodnota) -> list:
    """
    Vloží proměnnou do seznamu.
    """
    slovnik = [hodnota]
    return slovnik