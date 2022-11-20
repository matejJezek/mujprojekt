# Generated by Django 4.1 on 2022-09-27 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evidence_pojisteni', '0008_rename_predmet_pojisteni_pojisteni_predmet_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='udalost',
            name='id_pojistence',
        ),
        migrations.AlterField(
            model_name='udalost',
            name='datum',
            field=models.DateField(verbose_name='datum'),
        ),
        migrations.AlterField(
            model_name='udalost',
            name='predmet',
            field=models.CharField(max_length=255, verbose_name='Předmět události'),
        ),
    ]