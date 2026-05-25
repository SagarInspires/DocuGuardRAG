import os
from dotenv import load_dotenv
from google import genai

from app.core.prompt_loader import load_prompt

load_dotenv()


def fallback_answer(question: str, context: str) -> str:
    return (
        "LLM generation is currently unavailable due to API quota or provider error. "
        "However, relevant document evidence was retrieved successfully. "
        "Please check the citations and retrieved_chunks fields for source-grounded evidence."
    )


def generate_answer(question: str, context: str) -> str:
    prompt_config = load_prompt("app/prompts/answer_v1.yaml")

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    if not api_key:
        return fallback_answer(question, context)

    try:
        client = genai.Client(api_key=api_key)

        system_prompt = prompt_config["system"]
        user_prompt = prompt_config["user_template"].format(
            question=question,
            context=context
        )

        final_prompt = f"""
{system_prompt}

{user_prompt}
""".strip()

        response = client.models.generate_content(
            model=model_name,
            contents=final_prompt
        )

        return response.text

    except Exception:
       return fallback_answer(question, context)