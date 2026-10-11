import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

model = os.environ.get("EXTRACT_MODEL", "gemini-3.8-flash")
print(f"Testing generation with model: {model}")

resp = client.models.generate_content(
    model=model,
    contents="Hello! Respond with JSON: {\"status\": \"ok\"}",
    config={"response_mime_type": "application/json", "temperature": 0.0}
)
print("Response text:", resp.text)

