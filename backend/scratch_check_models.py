import requests

from src.config.settings import settings

api_key = settings.grok_api_key
response = requests.get(
    "https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {api_key}"}
)
data = response.json()
print("Available models:")
for model in data.get("data", []):
    print(f"- {model['id']}")
