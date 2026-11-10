import unittest
from videoforge.pixellab.social_audit import inspect
from videoforge.pixellab.client import PixelLabError

class SocialAuditTests(unittest.TestCase):
    def test_detects_real_names_not_similar_generic(self):
        detail={"animations":[
            {"animation_type":"idle","directions":[]},
            {"display_name":"singing while sitting","directions":[]},
            {"display_name":"drinking water","directions":[]},
            {"animation_name":"playing video games","directions":[]},
        ]}
        report=inspect(detail)
        self.assertEqual(report["total_animation_groups"],4)
        self.assertTrue(report["activities"]["sing_seated"])
        self.assertTrue(report["activities"]["drink_water"])
        self.assertTrue(report["activities"]["games"])
        self.assertFalse(report["activities"]["coffee"])
        self.assertFalse(report["activities"]["restroom"])
        self.assertNotIn("singing while",str(report))
    def test_no_groups_refuses_to_guess(self):
        with self.assertRaises(PixelLabError):
            inspect({"animation_count":9})

if __name__=="__main__":
    unittest.main()
