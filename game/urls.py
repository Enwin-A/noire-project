# game/urls.py
from django.urls import path
from .views import NewGameView, NextLevelView, HeadlineView

urlpatterns = [
    path('new_game/', NewGameView.as_view(), name='new_game'),
    path('next_level/', NextLevelView.as_view(), name='next_level'),
    path('headline/', HeadlineView.as_view(), name='headline'),
]