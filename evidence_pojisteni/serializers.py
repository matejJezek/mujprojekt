from time import strftime
from rest_framework import serializers
from .models import Clanek, Uzivatel

class Autor_serializer(serializers.HyperlinkedModelSerializer):

    last_login = serializers.DateTimeField(
        read_only=True,
        format="%d.%m.%Y, %H:%M"
    )

    clanky = serializers.HyperlinkedRelatedField(
        many=True,
        view_name='clanek-detail',
        read_only=True
    )

    class Meta:
        model = Uzivatel
        fields = ['id', 'url', 'email', 'last_login', 'clanky']

class Clanek_serializer(serializers.HyperlinkedModelSerializer):

    id = serializers.ReadOnlyField()

    autor_email = serializers.ReadOnlyField(source='autor.email')

    vytvoreno = serializers.DateTimeField(
        read_only=True,
        format="%d.%m.%Y, %H:%M"
    )

    aktualizovano = serializers.DateTimeField(
        read_only=True,
        format="%d.%m.%Y, %H:%M"
    )

    class Meta:
        model = Clanek
        fields = '__all__'
        read_only_fields = ['autor']