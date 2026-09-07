import unittest

import main
from curriculum import filter_questions, get_curriculum, stages_for, subjects_for


class StudyLockCoreTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(main.normalize("  Na²  "), "na2")
        self.assertEqual(main.normalize("12 × 8"), "12 x 8")

    def test_curriculum_catalog(self):
        gcse = get_curriculum("GCSE")
        self.assertIsNotNone(gcse)
        self.assertEqual(subjects_for("gcse"), ("Chemistry",))
        self.assertEqual(stages_for("gcse"), ("O Level", "A Level", "AS Only", "A2"))

    def test_validate_questions_requires_valid_course(self):
        data = {
            "Chemistry": [
                {
                    "question": "What is Na?",
                    "answers": ["sodium"],
                    "topic": "Atomic structure",
                    "curriculum": "gcse",
                    "subject": "Chemistry",
                    "qualification_stage": "O Level",
                }
            ]
        }
        cleaned = main.validate_question_sets(data)
        self.assertEqual(cleaned["Chemistry"][0]["curriculum"], "gcse")
        self.assertEqual(cleaned["Chemistry"][0]["qualification_stage"], "O Level")

    def test_invalid_question_file(self):
        with self.assertRaises(ValueError):
            main.validate_question_sets({"Chemistry": [{"question": "broken"}]})

    def test_invalid_course_is_rejected(self):
        with self.assertRaises(ValueError):
            main.validate_question_sets({
                "Chemistry": [{
                    "question": "broken course",
                    "answers": ["x"],
                    "curriculum": "cbse",
                    "subject": "Chemistry",
                    "qualification_stage": "O Level",
                }]
            })

    def test_question_filtering(self):
        questions = [
            {"question": "gcse o level", "curriculum": "gcse", "subject": "Chemistry", "qualification_stage": "O Level"},
            {"question": "gcse a level", "curriculum": "gcse", "subject": "Chemistry", "qualification_stage": "A Level"},
        ]
        result = filter_questions(questions, curriculum_id="gcse", subject="Chemistry", qualification_stage="O Level")
        self.assertEqual([q["question"] for q in result], ["gcse o level"])

    def test_process_name_normalization(self):
        self.assertEqual(main.normalize_process_name("Game.exe"), "game")
        self.assertEqual(main.normalize_process_name("Game"), "game")


if __name__ == "__main__":
    unittest.main()
