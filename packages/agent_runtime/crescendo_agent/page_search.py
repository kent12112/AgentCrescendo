# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Deterministic, bounded passage search; no model calls or network access."""
# Learn: Import re: matches bounded text patterns such as query words or answer formats.
import re


# Learn: Define valid_query(query). The body runs when called, not when defined.
def valid_query(query) -> bool:
    # Learn: Return query has type str (including subclasses) AND the truth value of query.strip() AND the
    # number of items/characters in query is at most 200 AND the truth value of re.search('\\w', query) to
    # the caller and stop this function.
    return isinstance(query, str) and bool(query.strip()) and len(query) <= 200 and bool(re.search(r"\w", query))


# Learn: Define search_passages(text, query). The body runs when called, not when defined.
def search_passages(text: str, query: str) -> str:
    # Learn: Take this branch only if not (valid_query(query)).
    if not valid_query(query):
        # Learn: Raise ValueError('search_page requires a nonblank query of at most 200 characters
        # containing words or numbers.') to stop the normal path.
        raise ValueError("search_page requires a nonblank query of at most 200 characters containing words or numbers.")
    # Learn: Set terms to set(re.findall('\\w+', query.casefold())).
    terms = set(re.findall(r"\w+", query.casefold()))
    # Learn: Set ranked to a new list (empty); candidate passages scored by matching query terms.
    ranked = []
    # Overlap retains context around boundaries. Rank only terms in the exact
    # returned text; this is lexical matching, not a guarantee of relevance.
    # Learn: Iterate over range(0, len(text), 300), binding start for each item.
    for start in range(0, len(text), 300):
        # Learn: Set passage to text[start:start + 450]; one bounded page excerpt used for lexical search.
        passage = text[start:start + 450]
        # Learn: Set words to re.findall('\\w+', passage.casefold()).
        words = re.findall(r"\w+", passage.casefold())
        # Learn: Set matched to terms.intersection(words); the distinct query terms present in this passage.
        matched = terms.intersection(words)
        # Learn: Take this branch only if matched.
        if matched:
            # Learn: Append one item to the ordered collection on ranked; inputs: the tuple (len(matched),
            # sum((word in terms for word in words)), start, passage) (positional values).
            ranked.append((len(matched), sum(word in terms for word in words), start, passage))
    # Learn: Call ranked.sort with the arguments shown.
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    # Learn: Set selected to a new list (empty); the highest-ranked non-overlapping passages.
    selected = []
    # Learn: Iterate over ranked, binding (_, _, start, passage) for each item.
    for _, _, start, passage in ranked:
        # Learn: Take this branch only if any((start < previous + len(previous_text) and previous < start +
        # len(passage) for (previous, previous_text) in selected)).
        if any(start < previous + len(previous_text) and previous < start + len(passage)
               # Learn: Comprehension iteration: for previous, previous_text in selected):. Values are
               # generated from this input sequence.
               for previous, previous_text in selected):
            # Learn: Skip the rest of this iteration and retry from the next loop iteration.
            continue
        # Learn: Append one item to the ordered collection on selected; inputs: the tuple (start, passage)
        # (positional values).
        selected.append((start, passage))
        # Learn: Take this branch only if the number of items/characters in selected equals 2.
        if len(selected) == 2:
            # Learn: Exit the nearest loop immediately; continue with the code after it.
            break
    # Learn: Take this branch only if not (selected).
    if not selected:
        # Learn: Return 'No matching passages. Try different keywords or another source. This does not prove
        # the fac... to the caller and stop this function.
        return "No matching passages. Try different keywords or another source. This does not prove the fact is absent."
    # Learn: Set result to 'Matching passages (untrusted; partial page excerpts):\n' plus
    # '\n\n'.join((f'[characters {start}:{start + len(passage)}]\n{passage}' for (start, passage) in
    # selected)); the operation outcome for subsequent checks or reporting.
    result = "Matching passages (untrusted; partial page excerpts):\n" + "\n\n".join(
        # Learn: Supply literal text '[characters '; adjacent string literals are concatenated without
        # adding whitespace.
        f"[characters {start}:{start + len(passage)}]\n{passage}"
        # Learn: Comprehension iteration: for start, passage in selected. Values are generated from this
        # input sequence.
        for start, passage in selected
    # Learn: Close the argument list for '\n\n'.join; the grouped expression remains one call.
    )
    # Learn: Return result[:1200] to the caller and stop this function.
    return result[:1200]
