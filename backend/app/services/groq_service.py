import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from groq import Groq

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are FastRAG, an exam-focused study assistant.

Your main job is to answer student questions using the uploaded document context.

Answer style:
- Make answers exam-ready.
- Start with a clear definition.
- Use headings and bullet points.
- Add examples when useful.
- Use tables for differences/comparisons.
- Use numbered steps for processes.
- Keep answers easy to memorize and write in exams.

Grounding rules:
1. First use the uploaded document context.
2. If the context has enough information, answer mainly from it.
3. If the context is incomplete, add a separate section called 'Extra Study Notes'.
4. Extra Study Notes may use general academic knowledge, but must be clearly labeled.
5. Do not mix general knowledge with document-based content.
6. Never claim extra notes came from the uploaded document.
7. Sources/page numbers apply only to uploaded document content.

If no relevant context is found, say:
'I could not find this topic in your uploaded documents. Here is a general study explanation:'
Then provide a general exam-ready answer.

Keep the answer useful for students preparing for exams."""


@lru_cache
def get_groq_client() -> Groq:
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing Groq configuration. Set GROQ_API_KEY in the backend .env file.",
        )

    return Groq(api_key=groq_api_key)


def generate_answer_from_context(
    question: str,
    context: str,
    fast_mode: bool = False,
) -> str:
    clean_question = question.strip()
    clean_context = context.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not clean_context:
        clean_context = "No relevant uploaded document context was retrieved."

    style_instruction = (
        (
            "Fast mode is enabled. Keep the answer short and direct. "
            "Use maximum 5 bullet points. Include only one small example if useful."
        )
        if fast_mode
        else (
            "Fast mode is disabled. Give a more complete exam-style answer with "
            "headings, points, and an example when useful."
        )
    )

    user_prompt = f"""Context from uploaded document:
{clean_context}

Question:
{clean_question}

Write an exam-ready answer.

Instructions:
- First answer using the uploaded document context.
- If information is missing, add a separate 'Extra Study Notes' section.
- Add a simple example if useful.
- End with a short exam-ready conclusion.

{style_instruction}"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=512 if fast_mode else 800,
            temperature=0.1,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Groq answer generation failed: {exc}",
        ) from exc

    answer = response.choices[0].message.content

    if not answer:
        raise HTTPException(
            status_code=500,
            detail="Groq returned an empty answer.",
        )

    return answer.strip()
