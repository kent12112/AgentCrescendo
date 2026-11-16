"""Deterministic, bounded passage search; no model calls or network access."""
# Import re: matches bounded text patterns such as query words or answer formats.
import re


# Define valid_query with parameters query.
def valid_query(query) -> bool:
    # Return whether query is an instance of str and whether query with surrounding whitespace
    # removed is truthy and the length of query is at most 200 and whether re.search('\\w', query)
    # is truthy.
    return isinstance(query, str) and bool(query.strip()) and len(query) <= 200 and bool(re.search(r"\w", query))


# Define search_passages with parameters text, query.
def search_passages(text: str, query: str) -> str:
    # Check whether not (valid_query(query)).
    if not valid_query(query):
        # Raise ValueError('search_page requires a nonblank query of at most 200 characters
        # containing words or numbers.') to stop the normal path.
        raise ValueError("search_page requires a nonblank query of at most 200 characters containing words or numbers.")
    # Set terms to set(re.findall('\\w+', query.casefold())).
    terms = set(re.findall(r"\w+", query.casefold()))
    # Set ranked to an empty list.
    ranked = []
    # Overlap retains context around boundaries. Rank only terms in the exact
    # returned text; this is lexical matching, not a guarantee of relevance.
    # Iterate over range(0, len(text), 300), binding start for each item.
    for start in range(0, len(text), 300):
        # Set passage to text[start:start + 450].
        passage = text[start:start + 450]
        # Set words to re.findall('\\w+', passage.casefold()).
        words = re.findall(r"\w+", passage.casefold())
        # Set matched to terms.intersection(words).
        matched = terms.intersection(words)
        # Check whether matched.
        if matched:
            # Append (len(matched), sum((word in terms for word in words)), start, passage) to
            # ranked.
            ranked.append((len(matched), sum(word in terms for word in words), start, passage))
    # Call ranked.sort with no arguments.
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    # Set selected to an empty list.
    selected = []
    # Iterate over ranked, binding (_, _, start, passage) for each item.
    for _, _, start, passage in ranked:
        # Check whether any((start < previous + len(previous_text) and previous < start +
        # len(passage) for (previous, previous_text) in selected)).
        if any(start < previous + len(previous_text) and previous < start + len(passage)
               # Comprehension iteration: for previous, previous_text in selected):. Values are
               # generated from this input sequence.
               for previous, previous_text in selected):
            # Skip this item and continue with the next iteration.
            continue
        # Append (start, passage) to selected.
        selected.append((start, passage))
        # Check whether the length of selected equals 2.
        if len(selected) == 2:
            # Stop this loop.
            break
    # Check whether not (selected).
    if not selected:
        # Return 'No matching passages. Try different keywords or another source. This does not
        # prove the fact is absent.'.
        return "No matching passages. Try different keywords or another source. This does not prove the fact is absent."
    # Set result to 'Matching passages (untrusted; partial page excerpts):\n' plus
    # '\n\n'.join((f'[characters {start}:{start + len(passage)}]\n{passage}' for (start, passage) in
    # selected)).
    result = "Matching passages (untrusted; partial page excerpts):\n" + "\n\n".join(
        f"[characters {start}:{start + len(passage)}]\n{passage}"
        # Comprehension iteration: for start, passage in selected. Values are generated from this
        # input sequence.
        for start, passage in selected
    )
    # Return result[:1200].
    return result[:1200]
