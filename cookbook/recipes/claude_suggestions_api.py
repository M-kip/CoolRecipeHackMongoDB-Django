import json
import os
from dotenv import load_dotenv
import pprint as pp
from google import genai
from google.genai import types
from google.api_core import retry
# Load environment variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "your-google-api-key")
# Ensure GOOGLE_API_KEY is set
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in your .env file.")
# Ensure genai is installed: pip install google-genai
# Ensure dotenv is installed: pip install python-dotenv
def get_claude_suggestions(user_ingredients, similar_recipes, max_suggestions=4):
    """
    Get meal suggestions from Claude based on available ingredients and similar recipes

    Args:
        user_ingredients (list): List of ingredients provided by the user
        similar_recipes (list): List of similar recipes found by vector search
        max_suggestions (int): Maximum number of suggestions to return

    Returns:
        list: List of meal suggestions from Claude
    """
    # Ensure user_ingredients is a list
    if not isinstance(user_ingredients, list):
        raise ValueError("user_ingredients must be a list")
    # Prepare the prompt for Claude
    prompt = f"""I have these ingredients: {", ".join(user_ingredients)}


    Based on these ingredients, I need `{max_suggestions}` meal suggestions. 
    Here are some similar recipes from my database that might help you:

    {json.dumps(similar_recipes, indent=2)}

    For each suggestion, please:
    1. Provide a recipe name
    2. List the ingredients I have that can be used
    3. Suggest substitutions for any missing ingredients
    4. Give a brief description of how to prepare it
    5. Mention difficulty level (easy, medium, hard)

    Be friendly, practical, and focus on using what I have available with minimal extra ingredients. 
    Keep your answer concise and focused on the meal suggestions.
    """

    is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})

    # Set up a retry helper. This allows you to "Run all" without worrying about per-minute quota.
    genai.models.Models.generate_content = retry.Retry(
        predicate=is_retriable)(genai.models.Models.generate_content)

    # The Python SDK uses a Client object to make requests to the API. 
    # The client lets you control which back-end to use (between the Gemini API and Vertex AI) and handles authentication (the API key).
    client = genai.Client(api_key=GOOGLE_API_KEY)
    chat = client.chats.create(model='gemini-2.0-flash', history=[],)
    response = chat.send_message(prompt)
    suggestions_text=response.text
    # Split the suggestions - we'll assume each suggestion starts with a recipe name and number
    raw_suggestions = []
    current_suggestion = ""

    for line in suggestions_text.split("\n"):
        # Check if this line starts a new suggestion
        if line.strip() and (
            line.strip()[0].isdigit() and line.strip()[1:3] in [". ", ") "]
        ):
            if current_suggestion:
                raw_suggestions.append(current_suggestion.strip())
            current_suggestion = line
        else:
            current_suggestion += "\n" + line

    # Add the last suggestion
    if current_suggestion:
        raw_suggestions.append(current_suggestion.strip())

    # Limit to max_suggestions
    return raw_suggestions[:max_suggestions]