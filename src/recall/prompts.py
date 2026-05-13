JSON_ONLY_SYSTEM = "Output only one JSON object matching the requested schema."

RECALL_PROMPT_TEMPLATE = """Return one JSON object with this schema:
{{
  "paper_title": "...",
  "paper_authors": ["...", "..."],
  "decision_basis": "...",
  "has_open_conjecture": false,
  "conjectures": [
    {{
      "conjecture_label": "...",
      "conjecture_text": "...",
      "conjecture_section": "...",
      "difficulty_note": "...",
      "difficulty": 0.5
    }}
  ]
}}

Rules:
- `paper_title` must be a non-empty string.
- `paper_authors` must be a JSON array of non-empty author-name strings.
- `decision_basis` must be one short English sentence.
- `has_open_conjecture` must be a JSON boolean.
- `conjectures` must be a JSON array. If `has_open_conjecture` is false, it must be `[]`.
- Set `has_open_conjecture` to true iff the paper contains at least one explicit unresolved mathematical statement.
- Count these as hits:
  1. labeled `Conjecture` / `Question` / `Open Problem`
  2. sentences with markers like `open question`, `open problem`, `open issue`, `remains unknown whether`, or `we suspect ... although we have been unable to establish ...`
  3. a direct statement that a specific mathematical property, existence claim, or classification problem `still remains an open issue`
- Do NOT count:
  1. generic future work
  2. `it would be interesting`
  3. `there are indications`
  4. `without explicit proof`
  5. `work in progress` claims unless they are clearly posed as an unresolved problem statement
  6. bare facts that something is not known unless the paper explicitly presents it as a problem/question
- If a sentence says a specific claim or property is `still an open issue`, count it even if it is not written as a formal question.
- If `has_open_conjecture` is true, extract only the explicit unresolved statements themselves, not nearby speculation.
- `conjecture_label` should use the paper's label when present, otherwise use a short fallback like `Unlabeled open problem 1`.
- `conjecture_text` should copy the paper's unresolved statement as faithfully as possible and preserve notation.
- `conjecture_section` should be the visible section/subsection title, or `""` if unavailable.
- `difficulty_note` must be one short English sentence.
- `difficulty` must be a number in [0, 1], with most ordinary cases near 0.5 and extreme values used sparingly.

Paper content:
{book_md}
"""
