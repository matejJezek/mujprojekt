# Generated by Django 4.1 on 2022-09-22 11:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evidence_pojisteni', '0006_typ_pojisteni_alter_pojistenec_email_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pojisteni',
            name='id_pojistenec',
        ),
        migrations.AddField(
            model_name='pojisteni',
            name='id_pojistence',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='evidence_pojisteni.pojistenec', verbose_name='id pojištěnce'),
        ),
        migrations.AlterField(
            model_name='pojisteni',
            name='typ',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='evidence_pojisteni.typ_pojisteni', verbose_name='Typ pojištění'),
        ),
    ]
