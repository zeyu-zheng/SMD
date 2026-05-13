JSON_ONLY_SYSTEM = "Output only one JSON object matching the requested schema."

RERANK_PROMPT_TEMPLATE = """Return one JSON object with this schema:
{{
  "sources": [
    {{"title": "...", "url": "...", "claim": "..."}}
  ],
  "reason": "...",
  "status": "solved",
  "importance": 0.5,
  "difficulty": 0.5
}}

Rules:
- Verify the candidate's current status using current web information.
- `status` must be one of: `open`, `solved`, `invalid`.
- Use `open` when the candidate is a concrete open problem in the source and no credible solved evidence is found.
- Use `solved` when a credible source appears to solve it.
- Use `invalid` when it is not a concrete open problem in the source.
- `sources` should list only sources directly supporting the status.
- `reason` must be one concise English sentence.
- `importance` must be a number in [0, 1] for the candidate itself: candidates with no substantive mathematical content should be scored 0; Fields-Medal-level problems should be scored 1; most ordinary research problems should follow a roughly normal distribution centered around 0.5.
- `difficulty` must be a number in [0, 1], with most ordinary cases near 0.5 and extreme values used sparingly.
- For `solved` or `invalid`, set `importance` and `difficulty` to 0.

Paper title: {paper_title}
Paper authors: {paper_authors}
Candidate label: {conjecture_label}
Candidate section: {conjecture_section}
Candidate text:
{conjecture_text}
"""
