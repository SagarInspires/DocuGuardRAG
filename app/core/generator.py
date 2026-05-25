import os
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()


FALLBACK_PREFIX = "Based on the retrieved evidence"


def build_generation_prompt(question: str, context: str) -> str:
    return f"""
You are a strict document-grounded assistant.

Answer the user's question using ONLY the provided context.

Rules:
- Give a direct, concise answer.
- Do not hallucinate.
- Do not use outside knowledge.
- If the answer is not present in the context, say:
  "I could not find this in the uploaded documents."

Question:
{question}

Context:
{context}

Answer:
"""


def clean_context_metadata(text: str) -> str:
    """
    Removes context-builder metadata such as:
    File: x.pdf Page: 10 Chunk ID: abc Text:
    """

    if not text:
        return ""

    text = re.sub(r"File:\s*[^.]+?\.pdf", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"Page:\s*\d+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"Chunk ID:\s*\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bText:\s*", " ", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text: str) -> str:
    text = clean_context_metadata(text)
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def split_into_sentences(text: str) -> List[str]:
    text = normalize_text(text)

    if not text:
        return []

    raw_sentences = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", text)

    sentences = []

    for sentence in raw_sentences:
        sentence = sentence.strip()

        if len(sentence) < 35:
            continue

        if sentence.lower().startswith(("file:", "page:", "chunk", "text:")):
            continue

        sentences.append(sentence)

    return sentences


def get_question_keywords(question: str) -> List[str]:
    stopwords = {
        "what", "why", "how", "when", "where", "which", "who",
        "is", "are", "was", "were", "the", "a", "an", "of", "in",
        "on", "for", "to", "and", "or", "with", "by", "from",
        "explain", "define", "tell", "me", "about", "does", "do",
        "give", "write", "short", "brief", "note", "notes"
    }

    words = re.findall(r"[a-zA-Z0-9]+", question.lower())

    keywords = [
        word for word in words
        if word not in stopwords and len(word) > 2
    ]

    return keywords


def rank_sentences_by_question(sentences: List[str], question: str) -> List[str]:
    keywords = get_question_keywords(question)

    if not keywords:
        return sentences[:4]

    scored = []

    for sentence in sentences:
        lower_sentence = sentence.lower()
        score = 0

        for keyword in keywords:
            if keyword in lower_sentence:
                score += 3

        definition_signals = [
            "is", "refers to", "means", "defined as", "consists of",
            "includes", "classified", "divided", "concentrated",
            "important", "main", "major"
        ]

        for signal in definition_signals:
            if signal in lower_sentence:
                score += 1

        # Penalize noisy unrelated lines
        noise_terms = ["prepare", "question", "map", "exercise", "file", "chunk id"]
        for noise in noise_terms:
            if noise in lower_sentence:
                score -= 2

        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    ranked = [sentence for score, sentence in scored if score > 0]

    if not ranked:
        return sentences[:3]

    return ranked[:4]


def build_extractive_fallback_answer(question: str, context: str) -> str:
    """
    Creates a clean answer from retrieved evidence when Gemini/API fails.
    This is not true generation; it is extractive summarization.
    """

    context = normalize_text(context)

    if not context:
        return "I could not find this in the uploaded documents."

    sentences = split_into_sentences(context)

    if not sentences:
        short_context = context[:700].rsplit(" ", 1)[0]
        return f"{FALLBACK_PREFIX}, {short_context}."

    best_sentences = rank_sentences_by_question(
        sentences=sentences,
        question=question
    )

    if not best_sentences:
        return "I could not find this clearly in the uploaded documents."

    # Deduplicate similar sentences
    seen = set()
    final_sentences = []

    for sentence in best_sentences:
        key = sentence[:80].lower()

        if key not in seen:
            seen.add(key)
            final_sentences.append(sentence)

    answer_body = " ".join(final_sentences)

    max_chars = 850

    if len(answer_body) > max_chars:
        answer_body = answer_body[:max_chars].rsplit(" ", 1)[0] + "."

    return f"{FALLBACK_PREFIX}, {answer_body}"


def is_extractive_fallback_answer(answer: str) -> bool:
    return bool(answer and answer.strip().startswith(FALLBACK_PREFIX))


def generate_answer(question: str, context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    if not api_key:
        return build_extractive_fallback_answer(question, context)

    try:
        import google.generativeai as genai  # type: ignore[import-not-found]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = build_generation_prompt(
            question=question,
            context=context
        )

        response = model.generate_content(prompt)

        if not response or not getattr(response, "text", None):
            return build_extractive_fallback_answer(question, context)

        return response.text.strip()

    except Exception:
        return build_extractive_fallback_answer(question, context)