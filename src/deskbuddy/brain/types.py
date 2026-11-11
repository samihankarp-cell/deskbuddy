from dataclasses import dataclass


@dataclass
class CheckResult:
    passed: bool
    reason: str = ""


@dataclass
class JobResult:
    title: str
    check: CheckResult
    answer: str = ""    # filled when the user asked for information
    summary: str = ""   # what was done, in a few words
