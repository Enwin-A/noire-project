# game/views.py
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Game, LevelData
from .serializers import LevelDataSerializer
from .utils import generate_story_outline, generate_level_content, generate_headline

@method_decorator(csrf_exempt, name='dispatch')
class NewGameView(APIView):
    def post(self, request):
        # Start a new game: generate outline, then generate level 1
        try:
            outline = generate_story_outline()
        except Exception as e:
            return Response({'error': 'Failed to generate story outline: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Create Game
        game = Game.objects.create(outline=outline, current_level=1, choices_history=[])
        # Generate level 1 content
        try:
            level_content = generate_level_content(outline, [], 1)
        except Exception as e:
            return Response({'error': 'Failed to generate level 1: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Save LevelData
        LevelData.objects.create(game=game, level_number=1, role=level_content.get('role', 'detective'), content=level_content)
        # Respond with game_id and level content
        return Response({
            'game_id': str(game.id),
            'level': level_content,
        })

@method_decorator(csrf_exempt, name='dispatch')
class NextLevelView(APIView):
    def post(self, request):
        # Expects JSON: {'game_id': str, 'choices_path': [ {'node_id': ..., 'choice_text': ...}, ... ] }
        data = request.data
        game_id = data.get('game_id')
        choices_path = data.get('choices_path')
        if not game_id or choices_path is None:
            return Response({'error': 'game_id and choices_path are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({'error': 'Invalid game_id'}, status=status.HTTP_400_BAD_REQUEST)
        # Append this level's choices to history
        current_level = game.current_level
        game.choices_history.append({'level': current_level, 'path': choices_path})
        # Increment level
        next_level = current_level + 1
        if next_level > 10:
            return Response({'message': 'Game completed! No more levels.'})
        # Generate next level content
        try:
            level_content = generate_level_content(game.outline, game.choices_history, next_level)
        except Exception as e:
            return Response({'error': f'Failed to generate level {next_level}: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Save updated game state
        game.current_level = next_level
        game.save()
        # Save LevelData
        LevelData.objects.create(game=game, level_number=next_level, role=level_content.get('role', ''), content=level_content)
        # Return next level content
        return Response({
            'level': level_content,
        })

@method_decorator(csrf_exempt, name='dispatch')
class HeadlineView(APIView):
    def post(self, request):
        # Expects JSON: {'game_id': str, 'choices_path': [ ... ] }
        data = request.data
        game_id = data.get('game_id')
        choices_path = data.get('choices_path')
        if not game_id or choices_path is None:
            return Response({'error': 'game_id and choices_path are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({'error': 'Invalid game_id'}, status=status.HTTP_400_BAD_REQUEST)
        # Temporarily form a new history including this level for summary
        temp_history = list(game.choices_history)
        temp_history.append({'level': game.current_level, 'path': choices_path})
        try:
            headline = generate_headline(game.outline, temp_history, game.current_level)
        except Exception as e:
            return Response({'error': 'Failed to generate headline: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'headline': headline})