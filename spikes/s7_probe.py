"""S7: one small call per candidate model, to see which this key can use."""
import sys
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()
for model in sys.argv[1:]:
    start = time.perf_counter()
    try:
        r = client.models.generate_content(model=model, contents="Reply with the word ok.")
        print(f"{model}: OK {time.perf_counter() - start:.1f}s tokens={r.usage_metadata.total_token_count}")
    except Exception as e:
        print(f"{model}: FAIL {str(e)[:140]}")
