import unittest

import timer_feature


class TimerFeatureTests(unittest.TestCase):
    def test_default_timer_settings_are_present(self):
        settings = {}
        timer = timer_feature.timer_settings(settings)
        self.assertEqual(timer["color"], "#FFFFFF")
        self.assertEqual(timer["size"], 18)
        self.assertEqual(timer["position"], "Top Right")

    def test_timer_settings_preserve_custom_values(self):
        settings = {"timer": {"color": "#00FF00", "size": 24, "position": "Bottom Left"}}
        timer = timer_feature.timer_settings(settings)
        self.assertEqual(timer["color"], "#00FF00")
        self.assertEqual(timer["size"], 24)
        self.assertEqual(timer["position"], "Bottom Left")


if __name__ == "__main__":
    unittest.main()
