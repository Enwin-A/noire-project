# game/utils.py
import os
import json
import uuid
import requests
from io import BytesIO
from PIL import Image
import openai  # pylint: disable=no-member
from django.conf import settings

# Configure API key
openai.api_key = settings.OPENAI_API_KEY

# Helper to call OpenAI ChatCompletion using v1 interface
def call_openai_chat(messages, max_tokens=1000, temperature=0.7):
    # pylint: disable=no-member
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content

# Generate story outline
def generate_story_outline():
    system_msg = {'role': 'system', 'content': (
        "You are a story designer for a noir dialogue-driven game set in 1940s New York. "
        "Generate an overarching story outline with 10 levels, alternating roles between detective and journalist starting with detective at level 1. "
        "Include historical context, fictional characters, a central mystery evolving over levels, key branching points. "
        "Return JSON with key 'levels': list of 10 items: each with 'level_number', 'role', 'summary', and optionally 'key_characters'."
    )}
    content = call_openai_chat([system_msg], max_tokens=1000)
    try:
        outline = json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{'); end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                outline = json.loads(content[start:end+1])
            except:
                raise ValueError("Failed parse outline: " + content)
        else:
            raise ValueError("Failed parse outline: " + content)
    return outline

# Generate level dialogue tree
def generate_level_content(outline, choices_history, level_number):
    levels = outline.get('levels') or []
    level_outline = next((lvl for lvl in levels if lvl.get('level_number') == level_number), None)
    if not level_outline:
        raise ValueError(f"Level {level_number} not in outline")
    role = level_outline.get('role')
    summary = level_outline.get('summary')
    prompt_text = (
        "You are a narrative engine generating a dialogue-based branching game level in JSON format for a noir game. "
        "Set in 1940s New York. "
        f"Generate a dialogue tree for level {level_number} as role {role}. "
        f"Outline summary: {summary}. "
        "Consider previous choices for coherence and NPC biases. "
        "Each node must have: 'id', 'speaker', 'text', 'choices': list of { 'text', 'next_id' }, and 'scene_description' for background context. "
        "Do NOT hardcode image names; use scene_description only. "
        "Ensure 5-10 decision points. Return JSON with 'level_number','role','dialogue_nodes', and 'start_node'."
    )
    system_msg = {'role': 'system', 'content': prompt_text}
    user_msg = {'role': 'user', 'content': json.dumps({'outline': outline, 'choices_history': choices_history, 'current_level': level_number})}
    content = call_openai_chat([system_msg, user_msg], max_tokens=2000)
    # Parsing helper inside function
    def try_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None
    level_content = try_parse(content)
    if level_content is None:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1:
            substring = content[start:end+1] if end != -1 else content[start:]
            # Balance braces
            open_braces = substring.count('{')
            close_braces = substring.count('}')
            if open_braces > close_braces:
                substring += '}' * (open_braces - close_braces)
            level_content = try_parse(substring)
    if level_content is None:
        raise ValueError(f"Failed parse level {level_number}: " + content)
    level_content.setdefault('level_number', level_number)
    level_content.setdefault('role', role)
    # Ensure each node has non-empty text
    for node in level_content.get('dialogue_nodes', []):
        if not node.get('text') or not node['text'].strip():
            desc = node.get('scene_description', '').strip()
            node['text'] = desc or "..."
    return level_content

# Generate headline
def generate_headline(outline, choices_history, level_number):
    system_msg = {'role': 'system', 'content': (
        "You are a 1940s newspaper headline writer in New York. "
        f"Given the story outline and choices up to level {level_number}, produce a sensational newspaper headline summarizing this level's events and player's impact. "
        "Return one-line headline."
    )}
    user_msg = {'role': 'user', 'content': json.dumps({'outline': outline, 'choices_history': choices_history, 'current_level': level_number})}
    content = call_openai_chat([system_msg, user_msg], max_tokens=100)
    return content.strip().strip('"')

# Generate background prompt
def generate_dynamic_background_prompt(level_number, level_summary, node_context=None):
    system_msg = {'role': 'system', 'content': (
        "You are an AI assistant generating pixel-art prompts for a 1940s New York noir game. "
        "Given level number and summary, and optionally node context (e.g., 'office at night'), produce a pixel-art prompt: 16-bit style, limited palette (4-8 colors), no anti-aliasing, hard edges, dithering, dramatic chiaroscuro, noir atmosphere, aspect ratio 16:9. "
        "Suggest filename 'bg_<level>_<slug>.png'. Return JSON with 'prompt' and 'image_name'."
    )}
    user_content = {'level_number': level_number, 'level_summary': level_summary}
    if node_context:
        user_content['node_context'] = node_context
    user_msg = {'role': 'user', 'content': json.dumps(user_content)}
    content = call_openai_chat([system_msg, user_msg], max_tokens=200)
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{'); end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                result = json.loads(content[start:end+1])
            except:
                prompt = f"1940s New York noir pixel art level {level_number}: {level_summary}, scene: {node_context or 'generic'}, 16-bit, limited palette, no AA, hard edges, dithering, chiaroscuro --ar 16:9"
                slug = (node_context.lower().replace(' ', '_') if node_context else f"lvl{level_number}")
                image_name = f"bg_{level_number}_{slug}_{uuid.uuid4().hex[:6]}.png"
                result = {'prompt': prompt, 'image_name': image_name}
        else:
            prompt = f"1940s New York noir pixel art level {level_number}: {level_summary}, scene: {node_context or 'generic'}, 16-bit, limited palette, no AA, hard edges, dithering, chiaroscuro --ar 16:9"
            slug = (node_context.lower().replace(' ', '_') if node_context else f"lvl{level_number}")
            image_name = f"bg_{level_number}_{slug}_{uuid.uuid4().hex[:6]}.png"
            result = {'prompt': prompt, 'image_name': image_name}
    return result

# Generate sprite prompt
def generate_dynamic_sprite_prompt(character_name, character_description):
    system_msg = {'role': 'system', 'content': (
        "You are an AI assistant generating pixel-art sprite prompts for 1940s noir game. "
        "Given character name and description, produce prompt for 32x32 sprite sheet (idle/walk/talk), no anti-aliasing, hard edges, limited palette, dithering, chiaroscuro. "
        "Suggest filename 'sprite_<slug>.png'. Return JSON with 'prompt' and 'image_name'."
    )}
    user_msg = {'role': 'user', 'content': json.dumps({'name': character_name, 'description': character_description})}
    content = call_openai_chat([system_msg, user_msg], max_tokens=200)
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{'); end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                result = json.loads(content[start:end+1])
            except:
                prompt = f"Pixel art 32x32 sprite for {character_name}: {character_description}, no AA, hard edges, limited palette, dithering, chiaroscuro"
                slug = character_name.lower().replace(' ', '_')
                image_name = f"sprite_{slug}_{uuid.uuid4().hex[:6]}.png"
                result = {'prompt': prompt, 'image_name': image_name}
        else:
            prompt = f"Pixel art 32x32 sprite for {character_name}: {character_description}, no AA, hard edges, limited palette, dithering, chiaroscuro"
            slug = character_name.lower().replace(' ', '_')
            image_name = f"sprite_{slug}_{uuid.uuid4().hex[:6]}.png"
            result = {'prompt': prompt, 'image_name': image_name}
    return result

# Generate and save image via OpenAI Image API using v1 interface; smaller size for speed
def generate_and_save_image(prompt, image_name, is_background=True):
    # pylint: disable=no-member
    if is_background:
        gen_size = "512x512"; final_size = (800, 600)
    else:
        gen_size = "256x256"; final_size = (32, 32)
    try:
        response = openai.images.generate(prompt=prompt, n=1, size=gen_size)
        image_url = response.data[0].url
        res = requests.get(image_url); res.raise_for_status()
        img = Image.open(BytesIO(res.content)).convert('RGBA')
        img = img.resize(final_size, Image.NEAREST)
        save_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, image_name)
        img.save(save_path)
        return True, None
    except Exception as e:
        return False, str(e)