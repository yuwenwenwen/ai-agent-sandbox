
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

MODEL = os.getenv("GEMINI_MODEL")


def generate_python(task: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=task,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You generate Python 3 code for a sandbox demo. "
                "Return only executable Python code. "
                "Do not include Markdown code fences or explanations. "
                "Use only the Python standard library. "
                "Do not access the network, read secrets, "
                "or modify files outside /tmp."
            ),
            temperature=0.2,
        ),
    )

    code = (response.text or "").strip()

    if not code:
        raise ValueError("Gemini 沒有產生程式碼")

    return code
