# game/views.py
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Game, LevelData
from .serializers import LevelDataSerializer
from .utils import (
    generate_story_outline, generate_level_content, generate_headline,
    generate_dynamic_background_prompt, generate_dynamic_sprite_prompt, generate_and_save_image
)

@method_decorator(csrf_exempt, name='dispatch')
class NewGameView(APIView):
    def post(self, request):
        try:
            outline = generate_story_outline()
        except Exception as e:
            return Response(
                {'error': 'Failed to generate story outline: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        game = Game.objects.create(outline=outline, current_level=1, choices_history=[])
        try:
            level_content = generate_level_content(outline, [], 1)
        except Exception as e:
            return Response(
                {'error': 'Failed generate level1: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        LevelData.objects.create(
            game=game,
            level_number=1,
            role=level_content.get('role', 'detective'),
            content=level_content
        )
        level_summary = next(
            (lvl['summary'] for lvl in outline.get('levels', []) if lvl.get('level_number') == 1),
            ''
        )
        return Response({
            'game_id': str(game.pk),
            'level': level_content,
            'level_summary': level_summary
        })

@method_decorator(csrf_exempt, name='dispatch')
class NextLevelView(APIView):
    def post(self, request):
        data = request.data
        game_id = data.get('game_id')
        choices_path = data.get('choices_path')
        if not game_id or choices_path is None:
            return Response(
                {'error': 'game_id and choices_path required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            game = Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Invalid game_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        current_level = game.current_level
        game.choices_history.append({'level': current_level, 'path': choices_path})
        next_level = current_level + 1
        if next_level > 10:
            return Response({'message': 'Game completed! No more levels.'})
        try:
            level_content = generate_level_content(
                game.outline,
                game.choices_history,
                next_level
            )
        except Exception as e:
            return Response(
                {'error': f'Failed generate level{next_level}: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        game.current_level = next_level
        game.save()
        LevelData.objects.create(
            game=game,
            level_number=next_level,
            role=level_content.get('role', ''),
            content=level_content
        )
        level_summary = next(
            (lvl['summary'] for lvl in game.outline.get('levels', []) if lvl.get('level_number') == next_level),
            ''
        )
        return Response({'level': level_content, 'level_summary': level_summary})

@method_decorator(csrf_exempt, name='dispatch')
class HeadlineView(APIView):
    def post(self, request):
        data = request.data
        game_id = data.get('game_id')
        choices_path = data.get('choices_path')
        if not game_id or choices_path is None:
            return Response(
                {'error': 'game_id and choices_path required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            game = Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Invalid game_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        temp_history = list(game.choices_history)
        temp_history.append({
            'level': game.current_level,
            'path': choices_path
        })
        try:
            headline = generate_headline(
                game.outline,
                temp_history,
                game.current_level
            )
        except Exception as e:
            return Response(
                {'error': 'Failed generate headline: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({'headline': headline})

@method_decorator(csrf_exempt, name='dispatch')
class GenerateBackgroundView(APIView):
    def post(self, request):
        data = request.data
        game_id = data.get('game_id')
        level_number = data.get('level_number')
        scene_description = data.get('scene_description')
        level_summary = data.get('level_summary')
        if not game_id or level_number is None or level_summary is None:
            return Response(
                {'error': 'game_id, level_number and level_summary required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            game = Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            return Response({'error': 'Invalid game_id'}, status=status.HTTP_400_BAD_REQUEST)

        # Check cache first
        cache_key = f"lvl{level_number}:{scene_description}"
        cache_entry = game.bg_cache.get(cache_key)
        if cache_entry:
            return Response(cache_entry)

        # Fallback default based on level
        default_map = {1: 'default_detective_office.png', 2: 'default_newsroom.png'}
        default_image = default_map.get(level_number, 'placeholder_bg.png')
        default_url = f'/static/images/{default_image}'
        response_payload = {
            'prompt': None,
            'image_name': default_image,
            'url': default_url
        }

        try:
            bg_info = generate_dynamic_background_prompt(
                level_number,
                level_summary,
                node_context=scene_description
            )
            prompt = bg_info.get('prompt')
            image_name = bg_info.get('image_name')
            success, err = generate_and_save_image(
                prompt,
                image_name,
                is_background=True
            )
            if success:
                response_payload = {
                    'prompt': prompt,
                    'image_name': image_name,
                    'url': f'/static/images/{image_name}'
                }
        except Exception:
            pass

        # Update cache and save
        game.bg_cache[cache_key] = response_payload
        game.save(update_fields=['bg_cache'])
        return Response(response_payload)

@method_decorator(csrf_exempt, name='dispatch')
class GenerateSpriteView(APIView):
    def post(self, request):
        data = request.data
        character_name = data.get('character_name')
        character_description = data.get('character_description')
        if not character_name or not character_description:
            return Response(
                {'error': 'character_name and character_description required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            sp = generate_dynamic_sprite_prompt(
                character_name,
                character_description
            )
            prompt = sp.get('prompt')
            image_name = sp.get('image_name')
            success, err = generate_and_save_image(
                prompt,
                image_name,
                is_background=False
            )
            if not success:
                return Response(
                    {'error': 'Sprite gen failed: ' + err},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            url_path = f'/static/images/{image_name}'
            return Response({'prompt': prompt, 'image_name': image_name, 'url': url_path})
        except Exception as e:
            return Response(
                {'error': 'Sprite prompt/gen failed: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )