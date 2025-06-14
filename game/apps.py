from django.apps import AppConfig


from django.apps import AppConfig
import os

class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'

    def ready(self):
        # On server start in DEBUG, clear generated images except specified defaults, and auto-generate defaults if missing
        from django.conf import settings
        from .utils import generate_and_save_image
        import os
        if settings.DEBUG:
            img_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
            if os.path.isdir(img_dir):
                # Define default images and their prompts
                defaults = {
                    'default_detective_office.png': "16-bit pixel art of a 1940s detective office: wooden desk with typewriter, dim lamp, files strewn, venetian blinds casting shadows, noir atmosphere, limited grayscale palette, hard edges, chiaroscuro",
                    'default_newsroom.png': "16-bit pixel art of a 1940s newspaper newsroom: rows of desks with typewriters, journalists at work, overhead lamps, bulletin boards with headlines, sepia-toned noir style, limited palette, hard edges"
                }
                # Remove non-default generated images
                keep = set(defaults.keys()) | {'placeholder_bg.png'}
                for fname in os.listdir(img_dir):
                    if fname not in keep:
                        file_path = os.path.join(img_dir, fname)
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except Exception:
                            pass
                # Generate default images if missing
                for fname, prompt in defaults.items():
                    path = os.path.join(img_dir, fname)
                    if not os.path.isfile(path):
                        # Attempt generation; smaller size for speed
                        try:
                            # Use 512x512 generation and resize to 800x600
                            success, err = generate_and_save_image(prompt, fname, is_background=True)
                            if not success:
                                # Could log error
                                pass
                        except Exception:
                            pass
