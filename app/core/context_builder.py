from typing import List, Dict


def build_context_from_chunks(chunks: List[Dict]) -> str:
    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]

        source = metadata.get("source", "unknown")
        page = metadata.get("page", "unknown")
        chunk_id = chunk.get("chunk_id", "unknown")
        text = chunk.get("text", "")

        context_block = f"""
[Source {index}]
File: {source}
Page: {page}
Chunk ID: {chunk_id}
Text:
{text}
""".strip()

        context_parts.append(context_block)

    return "\n\n".join(context_parts)