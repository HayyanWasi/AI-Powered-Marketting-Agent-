import sys

sys.path.insert(0, ".")
import google.generativeai as genai

from src.config.settings import settings

genai.configure(api_key=settings.google_api_key)
model = genai.GenerativeModel("models/gemini-2.5-flash-image")
response = model.generate_content(
    "Generate an image of a professional tech conference with blue lighting and modern stage"
)
print(f"Text: {(response.text or 'no text')[:200]}")
for part in response.parts:
    print(f"Part type: {type(part).__name__}")
    if hasattr(part, "inline_data"):
        print(f"Image mime: {part.inline_data.mime_type}")
        print(f"Image data length: {len(part.inline_data.data)} bytes")
        with open("test_gemini_image.png", "wb") as f:
            f.write(part.inline_data.data)
        print("Saved to test_gemini_image.png")
