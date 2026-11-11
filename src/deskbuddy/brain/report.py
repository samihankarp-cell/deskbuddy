"""The final wording. Code decides Done or I couldn't; no model can change it."""
from deskbuddy.brain.types import JobResult


def line_for(result: JobResult) -> str:
    if result.check.passed:
        if result.answer:
            return result.answer.strip()
        return f"Done: {(result.summary or result.title).strip().rstrip('.')}."
    reason = (result.check.reason or "I could not confirm it worked").strip().rstrip(".")
    return f"I couldn't: {result.title.strip().rstrip('.')}, because {reason}."


def format_report(results: list[JobResult]) -> str:
    if not results:
        return "I couldn't: there was nothing I could act on in that."
    return "\n".join(line_for(r) for r in results)
