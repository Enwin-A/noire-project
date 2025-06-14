# game/serializers.py
from rest_framework import serializers
from .models import LevelData

class LevelDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelData
        fields = ['level_number', 'role', 'content']