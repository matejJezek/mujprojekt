# Generated by Django 4.1.3 on 2022-12-07 11:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('evidence_pojisteni', '0025_remove_clanek_vlastnik_clanek_autor'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='clanek',
            options={'ordering': ['-vytvoreno'], 'verbose_name': 'Článek', 'verbose_name_plural': 'Články'},
        ),
    ]