"""Source-locked Cambridge Chemistry 9701 Paper 1 question bank.

The bank contains exactly 120 question records: 40 from each of the three
user-provided October/November 2025 papers 9701/11, 9701/12 and 9701/13.
No generated/practice questions are included.

The question text is preserved from the supplied papers. The answer-key
metadata is deliberately marked pending until it is verified against the
matching Cambridge mark schemes; the app must not silently substitute
invented/generated questions.
"""

from pathlib import Path
import json

_DATA = Path(__file__).with_name("exam_questions.json")


def questions():
    return json.loads(_DATA.read_text(encoding="utf-8"))
