"""The final wording: plain sentences, no "Done:" or "I couldn't:" labels.
Code still decides whether a job worked (the verdict is stored with the job); this only words it."""
from deskbuddy.brain.types import JobResult

SPECIAL = {"you said no": "Okay, I won't do that.", "you stopped me": "Okay, stopped."}


def sentence(text: str) -> str:
    text = " ".join((text or "").split()).strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


def line_for(result: JobResult) -> str:
    if result.check.passed:
        return result.answer.strip() or sentence(result.summary or result.title)
    reason = (result.check.reason or "").strip().rstrip(".")
    return SPECIAL.get(reason.lower()) or sentence(reason) or "That didn't work."


def format_report(results: list[JobResult]) -> str:
    if not results:
        return "I'm not sure what you'd like me to do. Could you say a bit more?"
    return " ".join(line_for(r) for r in results)
