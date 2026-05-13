JSON_ONLY_SYSTEM = "Output only one JSON object matching the requested schema."

LABEL_PROMPT_TEMPLATE = """Evaluate the paper and output exactly one JSON object in this shape:
{{
  "importance": 0.5,
  "formal_difficulty": 0.5,
  "subject": "other_math",
  "comment": "..."
}}

Output only the JSON object.
You only need to directly answer with this JSON object; do not save it yourself.
The scores must be numbers in [0, 1].
`subject` must be exactly one of: `algebra`, `number_theory`, `geometry_topology`, `analysis`, `probability_statistics`, `combinatorics`, `logic_foundations`, `applied_mathematics`, `other_math`, `non_math_or_mislabeled`.
`comment` must be concise English.
For `importance`, use this scale: author instructions or papers with no substantive mathematical content should be scored 0; Fields-Medal-level work should be scored 1; most ordinary research papers should follow a roughly normal distribution centered around 0.5.
For `formal_difficulty`, use this scale: results that already exist in mathlib should be scored 0; subjects that mathlib does not support at all should be scored 1; most papers should follow a roughly normal distribution centered around 0.5.
Before assigning `formal_difficulty`, you must use the `mathlib_search` tool to search mathlib for the main concepts of the paper.
Use multiple `mathlib_search` searches for different relevant concepts when helpful, so the `formal_difficulty` score is based on search evidence rather than guessing.
Choose `subject` based on the paper's primary mathematical area. Use `other_math` only when the paper is clearly mathematical but does not fit the listed subjects well. Use `non_math_or_mislabeled` only when the content is not actually mathematical or appears mislabeled.
In `comment`, briefly explain the two scores and the chosen `subject`. In the `formal_difficulty` part, mention what mathlib seems to support, what appears missing, and how that affected the score, based on the search results.

Paper content:
{book_md}
"""
