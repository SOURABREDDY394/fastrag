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
- Explain each important point instead of listing one-line keywords.
- Prefer complete study notes over brief summaries unless Fast Mode is enabled.

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
    answer_mode: str = "exam",
    unit_number: int | None = None,
    unit_page_range: tuple[int, int] | None = None,
) -> str:
    clean_question = question.strip()
    clean_context = context.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not clean_context:
        clean_context = "No relevant uploaded document context was retrieved."

    if answer_mode == "unit":
        page_range_text = (
            f"pages {unit_page_range[0]}-{unit_page_range[1]}"
            if unit_page_range
            else "the detected unit section"
        )
        style_instruction = f"""Unit Notes mode is enabled for Unit {unit_number} ({page_range_text}).
- Focus only on Unit {unit_number}; do not summarize the other units.
- Write detailed, exam-ready revision notes of roughly 900-1400 words when evidence supports it.
- Begin with the unit title and a short overview.
- Organize the unit into its major topics and subtopics.
- Explain every important concept in 2-4 sentences, not as bare keywords.
- Include definitions, methods, steps, classifications, advantages, limitations, and examples found in the document.
- Add an 'Important Exam Questions' section based only on the unit topics.
- End with a rapid-revision checklist and a concise unit conclusion.
- Do not add unrelated general knowledge or invent material missing from the document."""
    elif answer_mode == "summary":
        style_instruction = """Book Summary mode is enabled.
- Treat the context as evidence sampled across the whole uploaded document.
- Use the syllabus or contents information to identify the document structure.
- Cover every unit or major section visible in the evidence.
- Write a comprehensive whole-book revision guide, not a list of page locations.
- Begin with a short overview of the subject and its unit structure.
- For each unit, include the unit title, major topics, and at least 6 substantial revision points when evidence supports them.
- Explain each revision point in 2-4 sentences instead of writing bare keywords.
- Include important definitions, methods, classifications, advantages, limitations, or examples found in the evidence.
- End each unit with a short 'Exam Focus' list of likely concepts to revise.
- End the complete answer with a final rapid-revision checklist.
- Do not invent missing units, topics, definitions, or examples.
- Do not add general-knowledge Extra Study Notes in Book Summary mode.
- Do not output empty sections such as 'Extra Study Notes: None'.
- If evidence for a unit is limited, explicitly say that the available document excerpts are limited for that unit."""
    else:
        style_instruction = (
            (
                "Fast mode is enabled. Keep the answer short and direct. "
                "Use maximum 5 bullet points. Include only one small example if useful."
            )
            if fast_mode
            else (
                """Detailed Exam Answer mode is enabled.
- Write a complete 8-10 mark answer unless the question clearly asks for something shorter.
- Start with a definition or direct introduction.
- Use 4-7 meaningful headings when the topic supports them.
- Explain every main point in 2-4 sentences; do not give only one-line bullets.
- Include classifications, working, steps, features, advantages, limitations, or applications when present in the document.
- Include a document-grounded example when available.
- Finish with a concise exam-ready conclusion.
- Aim for roughly 700-1200 words when the retrieved evidence is sufficient."""
            )
        )

    def build_user_prompt(context_text: str) -> str:
        return f"""Context from uploaded document:
{context_text}

Question:
{clean_question}

Write an exam-ready answer.

Instructions:
- First answer using the uploaded document context.
- If information is missing, add a separate 'Extra Study Notes' section.
- Add a simple example if useful.
- End with a short exam-ready conclusion.
- Never respond with only page numbers or tell the student where key points are located.
- Directly explain the requested content.

{style_instruction}"""

    try:
        client = get_groq_client()
        max_tokens = (
            2100
            if answer_mode == "unit"
            else (1800 if answer_mode == "summary" else (600 if fast_mode else 1700))
        )

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(clean_context)},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
        except Exception as exc:
            error_text = str(exc).lower()
            if answer_mode not in {"summary", "unit"} or (
                "request too large" not in error_text and "413" not in error_text
            ):
                raise

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(clean_context[:10000]),
                    },
                ],
                max_tokens=1600,
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
