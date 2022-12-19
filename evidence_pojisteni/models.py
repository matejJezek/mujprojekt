from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings

# Create your models here.

class Pojistenec(models.Model):
    jmeno = models.CharField(
        max_length=50, verbose_name='Jméno'
    )
    prijmeni = models.CharField(
        max_length=50, verbose_name='Příjmení'
    )
    ulice = models.CharField(
        max_length=255, verbose_name='Ulice a číslo popisné'
    )
    mesto = models.CharField(
        max_length=255, verbose_name='Město'
    )
    psc = models.CharField(
        max_length=20, verbose_name='PSČ'
    )
    email = models.EmailField(
        max_length=255, verbose_name='Email', unique=True
    )
    telefon = models.CharField(
        max_length=50, verbose_name='Telefon', blank=True
    )
    fotografie = models.ImageField(
        upload_to='images', blank=True
    )

    def __str__(self):
        return "id pojištěnce: {}".format(self.id)

    class Meta:
        verbose_name = 'Pojištěnec'
        verbose_name_plural = 'Pojištěnci'

class Typ_pojisteni(models.Model):
    typ = models.CharField(
        max_length=255, verbose_name="Typ", primary_key=True
    )

    def __str__(self):
        return "{}".format(self.typ)

    class Meta:
        verbose_name = "Typ pojištění"
        verbose_name_plural = "Typy pojištění"

class Pojisteni(models.Model):
    pojistenec = models.ForeignKey(
        to=Pojistenec, on_delete=models.CASCADE,
        verbose_name="Pojištěnec"
    )
    typ = models.ForeignKey(
        to=Typ_pojisteni, on_delete=models.SET_DEFAULT,
        default="Nezařazeno", verbose_name="Typ pojištění"
    )
    castka = models.PositiveBigIntegerField(
        verbose_name="Částka (Kč)"
    )
    predmet = models.CharField(
        max_length=255, verbose_name="Předmět pojištění"
    )
    platnost_od = models.DateField(
        verbose_name="Platnot od"
    )
    platnost_do = models.DateField(
        verbose_name="Platnot do"
    )

    def __str__(self):
        return "id pojištění: {}".format(self.id)

    class Meta:
        verbose_name = "Pojištění"
        verbose_name_plural = "Pojištění"

class Udalost(models.Model):
    pojistenec = models.ForeignKey(
        to=Pojistenec, on_delete=models.CASCADE, verbose_name="Pojištěnec"
    )
    pojisteni = models.ForeignKey(
        to=Pojisteni, on_delete=models.CASCADE, verbose_name="Pojištění"
    )
    castka = models.PositiveBigIntegerField(
        verbose_name="Částka (Kč)"
    )
    predmet = models.CharField(
        max_length=255, verbose_name="Předmět události"
    )
    datum = models.DateField(
        verbose_name="datum"
    )
    popis = models.TextField(
        verbose_name='Popis události'
    )

    def __str__(self):
        return "id události: {}".format(self.id)

    class Meta:
        verbose_name = "Událost"
        verbose_name_plural = "Události"

class Clanek(models.Model):
    nazev = models.CharField(
        max_length=255,
        verbose_name='Název'
    )
    vytvoreno = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Vytvořeno'
    )
    aktualizovano = models.DateTimeField(
        auto_now=True,
        verbose_name='Naposledy změněno'
    )
    obsah = models.TextField(
        verbose_name='Obsah'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='clanky',
        on_delete=models.CASCADE,
        verbose_name='Autor'
    )
    
    class Meta:
        ordering = ['-vytvoreno']
        verbose_name = "Článek"
        verbose_name_plural = "Články"

class UzivatelManager(BaseUserManager):
    def create_user(self, email, heslo):
        if not email:
            raise ValueError('Uživatel musí mít emailovou adresu.')
        
        uzivatel = self.model(email=self.normalize_email(email))

        uzivatel.set_password(heslo)
        uzivatel.save(using=self._db)
        return uzivatel

    def create_superuser(self, email, heslo):
        uzivatel = self.create_user(email, heslo)
        uzivatel.je_admin = True
        uzivatel.save(using=self._db)
        return uzivatel

class Uzivatel(AbstractBaseUser):
    email = models.EmailField(
        max_length=255, unique=True
    )
    je_admin = models.BooleanField(
        default=False
    )
    # Pokud se přidá nový pojištěnec, zaregistruje ho aplikace jako
    # uživatele, kde pole 'pojistenec' slouží jako cizí klíč.
    pojistenec = models.OneToOneField(
        to=Pojistenec, on_delete=models.CASCADE, null=True,
        verbose_name="Pojištěnec", blank=True
    )

    class Meta:
        verbose_name = "Uživatel"
        verbose_name_plural = "Uživatelé"

    objects = UzivatelManager()
    USERNAME_FIELD = "email"
    
    def __str__(self):
        return "email: {}".format(self.email)

    @property
    def is_staff(self):
        return self.je_admin
    
    def has_perm(self, perm, obj=None):
        return True
    
    def has_module_perms(self, app_label):
        return True