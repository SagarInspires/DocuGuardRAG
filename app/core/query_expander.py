from app.core.acronym_extractor import get_document_acronyms


def expand_query_with_acronyms(query: str, source: str | None = None) -> str:
    acronym_map = get_document_acronyms(source)

    if not acronym_map:
        return query

    query_upper = query.upper()
    expansion_terms = []

    for acronym, full_form in acronym_map.items():
        if acronym.upper() in query_upper:
            expansion_terms.append(full_form)

    if not expansion_terms:
        return query

    return query + " " + " ".join(expansion_terms)