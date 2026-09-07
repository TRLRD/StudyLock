import json
import tempfile
import unittest
from pathlib import Path

import main


class StudyLockCoreTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(main.normalize("  Na²  "), "na2")
        self.assertEqual(main.normalize("12 × 8"), "12 x 8")

    def test_validate_questions(self):
        data = {
            "Chemistry": [
                {"question": "What is Na?", "answers": ["sodium"], "topic": "Atomic structure"}
            ]
        }
        cleaned = main.validate_question_sets(data)
        self.assertEqual(cleaned["Chemistry"][0]["topic"], "Atomic structure")
        self.assertEqual(cleaned["Chemistry"][0]["difficulty"], "Normal")

    def test_invalid_question_file(self):
        with self.assertRaises(ValueError):
            main.validate_question_sets({"Chemistry": [{"question": "broken"}]})

    def test_process_name_normalization(self):
        self.assertEqual(main.normalize_process_name("Game.exe"), "game")
        self.assertEqual(main.normalize_process_name("Game"), "game")


if __name__ == "__main__":
    unittest.main()
