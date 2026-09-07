import unittest
from curriculum import available_curricula, papers_for, filter_questions

class PaperMetadataTests(unittest.TestCase):
    def test_chemistry_a_level_exposes_papers(self):
        c = available_curricula()[0]
        papers = papers_for(c.id, "Chemistry", "A Level")
        self.assertEqual([p.id for p in papers], ["paper-1", "paper-2", "paper-3"])
        self.assertEqual(papers[0].description, "Multiple choice")

    def test_paper_filter_is_optional_and_exact(self):
        questions = [
            {"id": "1", "curriculum": "gcse", "subject": "Chemistry", "qualification_stage": "A Level", "paper": "paper-1"},
            {"id": "2", "curriculum": "gcse", "subject": "Chemistry", "qualification_stage": "A Level", "paper": "paper-2"},
        ]
        self.assertEqual(len(filter_questions(questions, curriculum_id="gcse", subject="Chemistry", qualification_stage="A Level")), 2)
        self.assertEqual([q["id"] for q in filter_questions(questions, curriculum_id="gcse", subject="Chemistry", qualification_stage="A Level", paper_id="paper-2")], ["2"])

if __name__ == "__main__":
    unittest.main()
