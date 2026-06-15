import os
import re
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from groq import Groq

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"
MERMAID_BLOCK_PATTERN = re.compile(
    r"```mermaid\s*([\s\S]*?)```",
    re.IGNORECASE,
)
DIAGRAM_REQUEST_TERMS = ("diagram", "flowchart", "flow chart", "architecture")
MERMAID_NODE_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z_]*(?:\[[^\[\]]+\])?$"
)

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
- Read the exact question carefully and follow its command word: define, explain, compare, discuss, justify, list, trace, or describe.
- Prioritize the requested topic. Do not pad the answer with a generic introduction to the entire subject.
- Explain why and how, not only what.

Formatting rules:
- Return clean Markdown.
- Use # for the answer title and ## or ### for sections.
- Use a Markdown table for genuine comparisons only.
- Do not write raw page references inside the answer; the application shows sources separately.
- Do not use HTML.

Diagram rules:
- Add a Mermaid diagram only when it improves understanding of a process, algorithm, architecture, hierarchy, decision flow, or lifecycle.
- Do not add a diagram for a simple definition or ordinary descriptive answer.
- Use a fenced code block beginning with ```mermaid and exactly `flowchart TD` syntax.
- Use only plain `-->` arrows. Do not use edge labels, numbered moves, player numbers, position numbers, styling directives, or left-to-right graphs.
- Keep node labels short and use only facts supported by the provided document context.
- The diagram must summarize steps or relationships already explained in the answer.
- Use generic concept labels. Never introduce arbitrary numbers, named examples, branches, or stages that are not explicitly supported by the context.
- For an algorithm, show its actual control flow: input, repeated decision or processing steps, and result.
- Use at most one diagram in an exam answer and at most two in unit notes.
- Never invent missing stages or relationships to make a diagram look complete.

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


def normalize_mermaid_diagram(diagram: str) -> str:
    lines = [line.strip() for line in diagram.splitlines() if line.strip()]
    if not lines or lines[0].lower() != "flowchart td":
        return diagram.strip()

    phrase_ids: dict[str, str] = {}

    def normalize_node(node: str) -> str:
        clean_node = node.strip()
        if MERMAID_NODE_PATTERN.fullmatch(clean_node):
            return clean_node

        label = re.sub(r"[\[\]{}()]", "", clean_node).strip()
        if not label:
            return clean_node

        if label not in phrase_ids:
            phrase_ids[label] = chr(ord("A") + len(phrase_ids))
        return f"{phrase_ids[label]}[{label}]"

    normalized_lines = ["flowchart TD"]
    for line in lines[1:]:
        if "-->" not in line or "|" in line:
            normalized_lines.append(line)
            continue

        left_node, right_node = line.split("-->", 1)
        normalized_lines.append(
            f"{normalize_node(left_node)} --> {normalize_node(right_node)}"
        )

    return "\n".join(normalized_lines)


def is_reliable_mermaid(diagram: str) -> bool:
    lines = [line.strip() for line in diagram.splitlines() if line.strip()]

    if not lines or lines[0].lower() != "flowchart td":
        return False

    arrow_lines = [line for line in lines[1:] if "-->" in line]
    suspicious_content = re.search(
        r"\||\d|classDef|style\s+|graph\s+lr",
        diagram,
        re.IGNORECASE,
    )
    valid_arrow_syntax = all(
        all(
            MERMAID_NODE_PATTERN.fullmatch(node.strip())
            for node in line.split("-->", 1)
        )
        for line in arrow_lines
    )

    return (
        2 <= len(arrow_lines) <= 12
        and suspicious_content is None
        and valid_arrow_syntax
    )


def remove_unreliable_mermaid(answer: str) -> str:
    def validate_or_remove(match: re.Match) -> str:
        diagram = normalize_mermaid_diagram(match.group(1))
        if not is_reliable_mermaid(diagram):
            return ""
        return f"```mermaid\n{diagram}\n```"

    cleaned_answer = MERMAID_BLOCK_PATTERN.sub(validate_or_remove, answer)
    return re.sub(r"\n{3,}", "\n\n", cleaned_answer).strip()


def build_step_flowchart(answer: str) -> str:
    section_lines: list[str] = []
    in_process_section = False

    for raw_line in answer.splitlines():
        line = raw_line.strip()

        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower()
            in_process_section = any(
                term in heading
                for term in ("step", "working", "process", "procedure", "algorithm")
            )
            continue

        if in_process_section:
            section_lines.append(line)

    step_labels: list[str] = []
    for line in section_lines:
        match = re.match(
            r"^(?:[-*]|\d+[.)])\s+(?:\*\*)?(.+?)(?:\*\*)?(?::\s|:\s*$|$)",
            line,
        )
        if not match:
            continue

        label = match.group(1)
        label = re.sub(r"\*\*|__|`", "", label)
        label = re.split(r"[:.;]", label, maxsplit=1)[0]
        label = re.sub(r"[^A-Za-z\s-]", "", label)
        label = re.sub(r"\s+", " ", label).strip()

        if 2 <= len(label.split()) <= 10 and label not in step_labels:
            step_labels.append(label)

        if len(step_labels) == 7:
            break

    if len(step_labels) < 3:
        return ""

    diagram_lines = ["flowchart TD"]
    for index, label in enumerate(step_labels):
        node_id = chr(ord("A") + index)
        if index == 0:
            diagram_lines.append(f"{node_id}[{label}]")
            continue

        previous_id = chr(ord("A") + index - 1)
        diagram_lines.append(f"{previous_id} --> {node_id}[{label}]")

    diagram = "\n".join(diagram_lines)
    if not is_reliable_mermaid(diagram):
        return ""

    return f"## Concept Flow\n\n```mermaid\n{diagram}\n```"


def generate_grounded_diagram(
    client: Groq,
    question: str,
    answer: str,
) -> str:
    diagram_prompt = f"""Create one compact Mermaid flowchart using only the explanation below.

Question:
{question}

Grounded explanation:
{answer[:6000]}

Return only a fenced Mermaid block.

Strict format:
```mermaid
flowchart TD
A[Short input label] --> B[Short documented step]
B --> C[Short documented step]
C --> D[Short result label]
```

Rules:
- Use 4 to 8 nodes.
- Use only plain --> arrows.
- Use no edge labels, numbers, styling directives, examples, player names, or position names.
- Do not introduce any step or relationship absent from the grounded explanation.
- Use flowchart TD only."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You convert grounded study explanations into minimal Mermaid "
                        "flowcharts. Return only the requested Mermaid block."
                    ),
                },
                {"role": "user", "content": diagram_prompt},
            ],
            max_tokens=300,
            temperature=0,
        )
    except Exception as exc:
        print(f"[FastRAG] Diagram generation skipped: {exc}")
        return ""

    diagram_response = response.choices[0].message.content or ""
    match = MERMAID_BLOCK_PATTERN.search(diagram_response)
    if not match:
        return ""

    diagram = normalize_mermaid_diagram(match.group(1))
    if not is_reliable_mermaid(diagram):
        return ""

    return f"## Concept Flow\n\n```mermaid\n{diagram}\n```"


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
- Add one or two document-grounded Mermaid diagrams when the unit contains a process, search procedure, architecture, reasoning flow, or learning workflow that benefits from visualization.
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
- Include one document-grounded Mermaid diagram when the topic is a process, algorithm, architecture, hierarchy, or decision flow and a diagram would genuinely help.
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
- Keep the answer internally consistent and avoid repeating the same point under multiple headings.
- If the retrieved evidence does not support part of the question, state the limitation instead of guessing.

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

    cleaned_answer = remove_unreliable_mermaid(answer.strip())
    requested_diagram = any(
        term in clean_question.lower()
        for term in DIAGRAM_REQUEST_TERMS
    )

    if requested_diagram and "```mermaid" not in cleaned_answer:
        diagram_section = generate_grounded_diagram(
            client=get_groq_client(),
            question=clean_question,
            answer=cleaned_answer,
        )
        if not diagram_section:
            diagram_section = build_step_flowchart(cleaned_answer)
        if diagram_section:
            cleaned_answer = f"{cleaned_answer}\n\n{diagram_section}"

    return cleaned_answer
