# game/models.py
import uuid
from django.db import models

class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    outline = models.JSONField()
    current_level = models.IntegerField(default=1)
    choices_history = models.JSONField(default=list)
    # Cache for background images: maps scene_description to {image_name, url, prompt}
    bg_cache = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Game {self.pk} - Level {self.current_level}"

class LevelData(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='levels')
    level_number = models.IntegerField()
    role = models.CharField(max_length=20)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'level_number')

    def __str__(self):
        return f"Game {self.game.pk} Level {self.level_number} ({self.role})"