import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API key present: {bool(api_key)}")

client = genai.Client(api_key=api_key)

try:
    models = list(client.models.list())
    model_names = [m.name for m in models]
    print(f"Total models available: {len(model_names)}")
    flash_models = [m for m in model_names if "flash" in m.lower()]
    print("Flash models:", flash_models)
except Exception as e:
    print(f"Error listing models: {e}")

