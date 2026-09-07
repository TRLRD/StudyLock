"""Curriculum metadata and question filtering for StudyLock.

The first release intentionally exposes only GCSE -> Chemistry. More curricula
and subjects can be added without changing the question/session engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Curriculum:
    id: str
    name: str
    subjects: tuple[str, ...]
    qualification_stages: tuple[str, ...]


# Product roadmap: keep this list small until the core app is finalized.
CURRICULA: tuple[Curriculum, ...] = (
    Curriculum(
        id="gcse",
        name="GCSE",
        subjects=("Chemistry",),
        qualification_stages=("O Level", "A Level", "AS Only", "A2"),
    ),
)


def available_curricula() -> tuple[Curriculum, ...]:
    return CURRICULA


def get_curriculum(curriculum_id: str) -> Curriculum | None:
    key = str(curriculum_id).strip().lower()
    return next((c for c in CURRICULA if c.id == key), None)


def subjects_for(curriculum_id: str) -> tuple[str, ...]:
    curriculum = get_curriculum(curriculum_id)
    return curriculum.subjects if curriculum else ()


def stages_for(curriculum_id: str) -> tuple[str, ...]:
    curriculum = get_curriculum(curriculum_id)
    return curriculum.qualification_stages if curriculum else ()


def question_matches(
    question: dict,
    *,
    curriculum_id: str,
    subject: str,
    qualification_stage: str,
) -> bool:
    """Return True only for questions belonging to the selected course."""
    return (
        str(question.get("curriculum", "")).strip().lower() == str(curriculum_id).strip().lower()
        and str(question.get("subject", "")).strip().lower() == str(subject).strip().lower()
        and str(question.get("qualification_stage", "")).strip().lower()
        == str(qualification_stage).strip().lower()
    )


def filter_questions(
    questions: Iterable[dict],
    *,
    curriculum_id: str,
    subject: str,
    qualification_stage: str,
) -> list[dict]:
    return [
        q for q in questions
        if question_matches(
            q,
            curriculum_id=curriculum_id,
            subject=subject,
            qualification_stage=qualification_stage,
        )
    ]


def tag_question(
    question: dict,
    *,
    curriculum_id: str,
    subject: str,
    qualification_stage: str,
    exam_board: str = "",
    paper_reference: str = "",
) -> dict:
    """Attach course metadata while preserving the existing question fields."""
    result = dict(question)
    result["curriculum"] = curriculum_id
    result["subject"] = subject
    result["qualification_stage"] = qualification_stage
    result["exam_board"] = exam_board
    result["paper_reference"] = paper_reference
    return result
