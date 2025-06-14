# game/urls.py
from django.urls import path
from .views import NewGameView, NextLevelView, HeadlineView, GenerateBackgroundView, GenerateSpriteView

urlpatterns = [
    path('new_game/', NewGameView.as_view(), name='new_game'),
    path('next_level/', NextLevelView.as_view(), name='next_level'),
    path('headline/', HeadlineView.as_view(), name='headline'),
    path('generate_background/', GenerateBackgroundView.as_view(), name='generate_background'),
    path('generate_sprite/', GenerateSpriteView.as_view(), name='generate_sprite'),
]