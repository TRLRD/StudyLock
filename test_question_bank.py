import unittest
import main

class QuestionBankTests(unittest.TestCase):
    def test_has_100_unique_questions(self):
        qs=main.ensure_questions()
        self.assertGreaterEqual(len(qs),100)
        self.assertEqual(len({q['id'] for q in qs}),len(qs))
    def test_bank_is_a_level_chemistry(self):
        qs=main.ensure_questions()
        self.assertTrue(all(q['qualification_stage']=='A Level' for q in qs))
        self.assertTrue(all(q['subject']=='Chemistry' for q in qs))
    def test_recent_question_ids_are_not_repeated(self):
        qs=main.ensure_questions()
        recent=[]
        for _ in range(min(12,len(qs))):
            pool=[q for q in qs if q['id'] not in recent] or qs
            q=pool[0]; recent.append(q['id'])
        self.assertEqual(len(recent),len(set(recent)))

if __name__=='__main__': unittest.main()
