"""S7: list the Gemini models this key can use for generation."""
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()
names = []
for m in client.models.list():
    if "generateContent" in (m.supported_actions or []) and "gemini" in m.name:
        names.append(m.name)
print(len(names))
print("\n".join(sorted(names)))
