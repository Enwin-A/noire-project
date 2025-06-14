# game/utils.py
import os
import json
import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

# Helper to call OpenAI ChatCompletion
def call_openai_chat(messages, max_tokens=1000, temperature=0.7):
    response = openai.ChatCompletion.create(
        model="gpt-4",  # or 'gpt-3.5-turbo' if GPT-4 not available
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response['choices'][0]['message']['content']

# Generate the overarching story outline for 10 levels
def generate_story_outline():
    system_msg = {
        'role': 'system',
        'content': (
            "You are a story designer for a noir dialogue-driven game set in 1940s New York. "
            "Generate an overarching story outline with 10 levels, alternating roles between detective and journalist starting with detective at level 1. "
            "Include historical context elements where appropriate, fictional characters, a central mystery that evolves over levels, and key branching points. "
            "Return the outline in JSON format with keys: 'levels', which is a list of 10 items; each item is an object with: 'level_number' (1-10), 'role' ('detective' or 'journalist'), 'summary' (a brief paragraph describing the focus of that level, the main event or investigation or scoop), and optionally 'key_characters' (list of important NPC names for that level)."
        )
    }
    # No user message needed
    messages = [system_msg]
    content = call_openai_chat(messages, max_tokens=1000)
    print(content, flush=True)  # REMOVE ALL PRINT STATEMENTS BEFORE PRODUCTION 

    # Expect content to be JSON; parse
    try:
        outline = json.loads(content)
    except json.JSONDecodeError:
        # If invalid JSON, attempt to extract JSON substring
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                outline = json.loads(content[start:end+1])
            except:
                raise ValueError("Failed to parse story outline JSON: " + content)
        else:
            raise ValueError("Failed to parse story outline JSON: " + content)
    return outline

# Generate detailed dialogue tree for a level based on outline and past choices
def generate_level_content(outline, choices_history, level_number):
    # Find the outline entry for this level
    levels = outline.get('levels') or []
    level_outline = None
    for lvl in levels:
        if lvl.get('level_number') == level_number:
            level_outline = lvl
            break
    if not level_outline:
        raise ValueError(f"Level {level_number} not found in outline")
    role = level_outline.get('role')
    summary = level_outline.get('summary')
    # Prepare prompt
    system_msg = {
        'role': 'system',
        'content': (
            "You are a narrative engine generating a dialogue-based branching game level in JSON format for a noir game. "
            "The game is set in 1940s New York. "
            "You will generate a JSON object representing the dialogue tree for level {level_number}, where the player assumes the role of {role}. "
            "Use the following outline summary for this level: {summary}. "
            "Also consider the choices made in previous levels (provided) to maintain story coherence and NPC biases. "
            "Each dialogue node must have: 'id' (unique string), 'speaker' (e.g., character name or 'Narrator'), 'text' (dialogue content), and 'choices' which is a list of { 'text': 'option text', 'next_id': 'id_of_next_node' }. "
            "Ensure there are between 5 to 10 decision points (i.e., nodes with choices). Return the JSON only, with keys: 'level_number', 'role', 'background_description' (a short text describing what background image to show), 'dialogue_nodes' (list of nodes), and 'start_node' (id of the first node)."
            .format(level_number=level_number, role=role, summary=summary))
    }
    # Include previous choices for context
    user_msg = {
        'role': 'user',
        'content': json.dumps({
            'outline': outline,
            'choices_history': choices_history,
            'current_level': level_number,
        })
    }
    messages = [system_msg, user_msg]
    content = call_openai_chat(messages, max_tokens=2000)
    print(content, flush=True)  # REMOVE ALL PRINT STATEMENTS BEFORE PRODUCTION 

    # Parse JSON
    try:
        level_content = json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                level_content = json.loads(content[start:end+1])
            except:
                raise ValueError(f"Failed to parse level {level_number} JSON: " + content)
        else:
            raise ValueError(f"Failed to parse level {level_number} JSON: " + content)
    # Attach level_number and role explicitly if missing
    level_content.setdefault('level_number', level_number)
    level_content.setdefault('role', role)
    return level_content

# Generate a headline summary for the level's events based on outline and choices
def generate_headline(outline, choices_history, level_number):
    # Prepare a prompt for a catchy 1940s newspaper headline
    system_msg = {
        'role': 'system',
        'content': (
            "You are a 1940s newspaper headline writer in New York. "
            "Given the story outline and the choices the player made up to level {level_number}, produce a sensational, era-appropriate newspaper headline summarizing the events of this level and the player's impact. "
            "Return just the headline text (one line)."
            .format(level_number=level_number)
        )
    }
    user_msg = {
        'role': 'user',
        'content': json.dumps({
            'outline': outline,
            'choices_history': choices_history,
            'current_level': level_number,
        })
    }
    messages = [system_msg, user_msg]
    content = call_openai_chat(messages, max_tokens=100)
    # Return as plain text
    return content.strip().strip('"')