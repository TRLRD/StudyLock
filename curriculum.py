"""Course and paper metadata used by StudyLock.

Paper definitions are data-driven so new curricula/subjects can be added without
rewriting the session engine. O Level remains intentionally unavailable.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Paper:
    id: str
    name: str
    code: str = ""
    description: str = ""

@dataclass(frozen=True)
class Curriculum:
    id: str
    name: str
    subjects: tuple[str, ...]
    qualification_stages: tuple[str, ...]
    papers: dict[tuple[str, str], tuple[Paper, ...]]

GCSE_CHEM_ALEVEL = (
    Paper("paper-1", "Paper 1", "1", "Multiple choice"),
    Paper("paper-2", "Paper 2", "2", "AS structured questions"),
    Paper("paper-3", "Paper 3", "3", "Advanced practical skills"),
)

CURRICULA: tuple[Curriculum, ...] = (
    Curriculum(
        id="gcse", name="GCSE", subjects=("Chemistry",),
        qualification_stages=("A Level", "AS Only", "A2"),
        papers={
            ("Chemistry", "A Level"): GCSE_CHEM_ALEVEL,
            ("Chemistry", "AS Only"): GCSE_CHEM_ALEVEL,
            ("Chemistry", "A2"): GCSE_CHEM_ALEVEL,
        },
    ),
)

def available_curricula() -> tuple[Curriculum, ...]: return CURRICULA

def get_curriculum(curriculum_id: str) -> Curriculum | None:
    key = str(curriculum_id).strip().lower()
    return next((c for c in CURRICULA if c.id == key), None)

def subjects_for(curriculum_id: str) -> tuple[str, ...]:
    c = get_curriculum(curriculum_id); return c.subjects if c else ()

def stages_for(curriculum_id: str) -> tuple[str, ...]:
    c = get_curriculum(curriculum_id); return c.qualification_stages if c else ()

def papers_for(curriculum_id: str, subject: str, qualification_stage: str) -> tuple[Paper, ...]:
    c = get_curriculum(curriculum_id)
    return c.papers.get((subject, qualification_stage), ()) if c else ()

def question_matches(question: dict, *, curriculum_id: str, subject: str,
                     qualification_stage: str, paper_id: str | None = None) -> bool:
    if not (
        str(question.get("curriculum", "")).strip().lower() == str(curriculum_id).strip().lower()
        and str(question.get("subject", "")).strip().lower() == str(subject).strip().lower()
        and str(question.get("qualification_stage", "")).strip().lower() == str(qualification_stage).strip().lower()
    ): return False
    return paper_id in (None, "", "all") or str(question.get("paper", "")).strip().lower() == str(paper_id).strip().lower()

def filter_questions(questions: Iterable[dict], *, curriculum_id: str, subject: str,
                     qualification_stage: str, paper_id: str | None = None) -> list[dict]:
    return [q for q in questions if question_matches(q, curriculum_id=curriculum_id,
        subject=subject, qualification_stage=qualification_stage, paper_id=paper_id)]

def tag_question(question: dict, *, curriculum_id: str, subject: str,
                 qualification_stage: str, exam_board: str = "", paper_reference: str = "",
                 paper: str = "") -> dict:
    result = dict(question)
    result.update(curriculum=curriculum_id, subject=subject,
                  qualification_stage=qualification_stage, exam_board=exam_board,
                  paper_reference=paper_reference, paper=paper)
    return result
