import os
import re
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

FALLBACK_PREFIX = "Based on the retrieved evidence"

MAX_CONTEXT_CHARS = int(os.getenv("OLLAMA_MAX_CONTEXT_CHARS", "3500"))
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "180"))


def build_generation_prompt(question: str, context: str) -> str:
    return f"""
You are a strict document-grounded RAG assistant.

Use ONLY the provided context. Do not use outside knowledge.

Your task:
- If the context contains a direct definition or explanation, answer clearly.
- Give the answer in 2 to 5 sentences.
- Do not mention file names, pages, chunk IDs, retrieval scores, or metadata.
- Do not copy the context word-for-word unless necessary.
- If the context truly does not contain the answer, say:
  "I could not find this clearly in the uploaded documents."

Question:
{question}

Relevant context:
{context}

Answer:
"""


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_context_metadata(text: str) -> str:
    """
    Removes RAG context-builder metadata from retrieved context.

    Examples removed:
    File: abc.pdf
    Page: 5
    Chunk ID: abc_c12
    Text:
    [Source 1]
    """

    if not text:
        return ""

    text = re.sub(
        r"File:\s*.*?\s+Page:\s*\d+\s+Chunk ID:\s*\S+\s+Text:\s*",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bFile:\s*.*?(?=\bPage:|\bChunk ID:|\bText:|$)",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bPage:\s*\d+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChunk ID:\s*\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bText:\s*", " ", text, flags=re.IGNORECASE)

    text = re.sub(r"\[Source\s*\d+\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\d+\]", " ", text)
    text = re.sub(r"[-_=]{3,}", " ", text)

    return normalize_space(text)


def split_into_sentences(text: str) -> List[str]:
    text = clean_context_metadata(text)

    if not text:
        return []

    raw_sentences = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", text)
    sentences = []

    for sentence in raw_sentences:
        sentence = normalize_space(sentence)

        if len(sentence) < 25:
            continue

        words = sentence.split()
        if len(words) < 5:
            continue

        alpha_chars = sum(ch.isalpha() for ch in sentence)
        total_chars = max(len(sentence), 1)

        if alpha_chars / total_chars < 0.45:
            continue

        lower = sentence.lower()

        if "chunk id" in lower:
            continue

        if lower.startswith(("file:", "page:", "text:", "source:")):
            continue

        sentences.append(sentence)

    return sentences


def get_question_keywords(question: str) -> List[str]:
    stopwords = {
        "what", "why", "how", "when", "where", "which", "who", "whom",
        "is", "are", "was", "were", "be", "been", "being",
        "the", "a", "an", "of", "in", "on", "for", "to", "and", "or",
        "with", "by", "from", "as", "at", "into", "than", "then",
        "does", "do", "did", "can", "could", "should", "would",
        "explain", "define", "tell", "me", "about", "give", "write",
        "short", "brief", "note", "notes", "answer", "according",
        "document", "pdf", "uploaded", "retrieved",
    }

    words = re.findall(r"[a-zA-Z0-9]+", question.lower())

    keywords = [
        word for word in words
        if word not in stopwords and len(word) > 2
    ]

    seen = set()
    final_keywords = []

    for word in keywords:
        if word not in seen:
            seen.add(word)
            final_keywords.append(word)

    return final_keywords


def prepare_relevant_context_for_llm(question: str, context: str) -> str:
    """
    Builds compact, question-focused context for local Ollama.

    This is important because small local models become weak when they receive
    long noisy chunks. We first select the most relevant sentences, then pass
    only that compact evidence to the model.
    """

    cleaned_context = clean_context_metadata(context)

    if not cleaned_context:
        return ""

    sentences = split_into_sentences(cleaned_context)

    if not sentences:
        return cleaned_context[:MAX_CONTEXT_CHARS]

    keywords = get_question_keywords(question)

    scored = []

    for sentence in sentences:
        lower = sentence.lower()
        score = 0

        for keyword in keywords:
            if keyword in lower:
                score += 5

        answer_signals = [
            "is the process",
            "is a process",
            "is the technique",
            "is a technique",
            "refers to",
            "means",
            "defined as",
            "is used",
            "subdivides",
            "divides",
            "separates",
            "segments",
            "consists",
            "includes",
            "called",
            "known as",
        ]

        for signal in answer_signals:
            if signal in lower:
                score += 2

        if len(sentence.split()) > 90:
            score -= 2

        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = [sentence for score, sentence in scored if score > 0]

    if not selected:
        selected = sentences[:4]

    compact_context = " ".join(selected[:6])

    return compact_context[:MAX_CONTEXT_CHARS]


def rank_sentences_by_question(sentences: List[str], question: str) -> List[str]:
    """
    Conservative fallback ranking.
    Used only if Ollama is unavailable.
    """

    keywords = get_question_keywords(question)

    if not keywords:
        return sentences[:2]

    scored = []

    for sentence in sentences:
        lower = sentence.lower()
        score = 0

        for keyword in keywords:
            if keyword in lower:
                score += 4

        answer_like_signals = [
            "is", "are", "refers to", "means", "defined as",
            "used to", "proposes", "introduced", "consists",
            "includes", "based on", "called", "known as",
        ]

        for signal in answer_like_signals:
            if signal in lower:
                score += 1

        if len(sentence.split()) > 80:
            score -= 2

        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    ranked = [sentence for score, sentence in scored if score > 0]

    if not ranked:
        return []

    return ranked[:2]


def build_extractive_fallback_answer(question: str, context: str) -> str:
    """
    Emergency fallback only.
    Main product output should come from Ollama.
    """

    context = clean_context_metadata(context)

    if not context:
        return "I could not find this in the uploaded documents."

    sentences = split_into_sentences(context)

    if not sentences:
        short_context = context[:600].rsplit(" ", 1)[0]
        return f"{FALLBACK_PREFIX}, {short_context}."

    best_sentences = rank_sentences_by_question(sentences, question)

    if not best_sentences:
        return (
            "I could not find a clear answer to this in the uploaded documents. "
            "The retrieved evidence may be related, but it does not directly answer the question."
        )

    keywords = get_question_keywords(question)
    answer_text = " ".join(best_sentences).lower()

    matched_keywords = [
        keyword for keyword in keywords
        if keyword in answer_text
    ]

    if keywords and len(matched_keywords) == 0:
        return (
            "I could not find a clear answer to this in the uploaded documents. "
            "The retrieved evidence may be related, but it does not directly answer the question."
        )

    seen = set()
    final_sentences = []

    for sentence in best_sentences:
        key = sentence[:90].lower()

        if key not in seen:
            seen.add(key)
            final_sentences.append(sentence)

    answer_body = " ".join(final_sentences)

    max_chars = 700

    if len(answer_body) > max_chars:
        answer_body = answer_body[:max_chars].rsplit(" ", 1)[0] + "."

    return f"{FALLBACK_PREFIX}, {answer_body}"


def is_extractive_fallback_answer(answer: str) -> bool:
    return bool(answer and answer.strip().startswith(FALLBACK_PREFIX))


def generate_with_ollama(question: str, context: str) -> Optional[str]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    cleaned_context = prepare_relevant_context_for_llm(
        question=question,
        context=context,
    )

    if not cleaned_context:
        return None

    prompt = build_generation_prompt(
        question=question,
        context=cleaned_context,
    )

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }

    try:
        print(
            f"[Ollama request] base_url={base_url} "
            f"model={model_name} context_chars={len(cleaned_context)} "
            f"num_predict={OLLAMA_NUM_PREDICT}"
        )

        response = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("response", "")

        if not answer or not answer.strip():
            return None

        answer = clean_context_metadata(answer.strip())

        if not answer:
            return None

        return answer

    except Exception as error:
        print(f"[Ollama generation failed] {type(error).__name__}: {error}")
        return None


def generate_answer(question: str, context: str) -> str:
    answer = generate_with_ollama(
        question=question,
        context=context,
    )

    if answer:
        print("[LLM generation succeeded] provider=ollama")
        return answer

    print("[LLM generation failed] Ollama unavailable, using extractive fallback")
    return build_extractive_fallback_answer(question, context)