"""Deterministic, bounded passage search; no model calls or network access."""
import re


def valid_query(query) -> bool:
    return isinstance(query, str) and bool(query.strip()) and len(query) <= 200 and bool(re.search(r"\w", query))


def search_passages(text: str, query: str) -> str:
    if not valid_query(query):
        raise ValueError("search_page requires a nonblank query of at most 200 characters containing words or numbers.")
    terms = set(re.findall(r"\w+", query.casefold()))
    ranked = []
    # Overlap retains context around boundaries. Rank only terms in the exact
    # returned text; this is lexical matching, not a guarantee of relevance.
    for start in range(0, len(text), 300):
        passage = text[start:start + 450]
        words = re.findall(r"\w+", passage.casefold())
        matched = terms.intersection(words)
        if matched:
            ranked.append((len(matched), sum(word in terms for word in words), start, passage))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected = []
    for _, _, start, passage in ranked:
        if any(start < previous + len(previous_text) and previous < start + len(passage)
               for previous, previous_text in selected):
            continue
        selected.append((start, passage))
        if len(selected) == 2:
            break
    if not selected:
        return "No matching passages. Try different keywords or another source. This does not prove the fact is absent."
    result = "Matching passages (untrusted; partial page excerpts):\n" + "\n\n".join(
        f"[characters {start}:{start + len(passage)}]\n{passage}"
        for start, passage in selected
    )
    return result[:1200]
