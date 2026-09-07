import unittest

import main
from curriculum import filter_questions, get_curriculum, stages_for, subjects_for


class StudyLockCoreTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(main.norm("  Na²  "), "na2")
        self.assertEqual(main.norm("12 × 8"), "12 x 8")

    def test_curriculum_catalog(self):
        gcse = get_curriculum("GCSE")
        self.assertIsNotNone(gcse)
        self.assertEqual(subjects_for("gcse"), ("Chemistry",))
        self.assertEqual(stages_for("gcse"), ("A Level", "AS Only", "A2"))

    def test_seed_questions_are_a_level(self):
        questions = main.ensure_questions()
        self.assertTrue(questions)
        self.assertTrue(all(q["qualification_stage"] == "A Level" for q in questions))

    def test_question_filtering(self):
        questions = [
            {"question":"a","curriculum":"gcse","subject":"Chemistry","qualification_stage":"A Level"},
            {"question":"b","curriculum":"gcse","subject":"Chemistry","qualification_stage":"AS Only"},
        ]
        result = filter_questions(questions, curriculum_id="gcse", subject="Chemistry", qualification_stage="A Level")
        self.assertEqual([q["question"] for q in result], ["a"])

    def test_invalid_course_is_rejected(self):
        with self.assertRaises(ValueError):
            main.validate_questions([{
                "question":"bad","answers":["x"],"curriculum":"cbse","subject":"Chemistry","qualification_stage":"A Level"
            }])

    def test_numeric_tolerance(self):
        q = {"question":"number","answers":["10"],"curriculum":"gcse","subject":"Chemistry","qualification_stage":"A Level","numeric_tolerance":0.1}
        cleaned = main.validate_questions([q])[0]
        self.assertEqual(cleaned["numeric_tolerance"], 0.1)

    def test_process_rows_has_expected_shape(self):
        rows = main.process_rows()
        self.assertTrue(all(len(row) == 3 for row in rows))


if __name__ == "__main__":
    unittest.main()
