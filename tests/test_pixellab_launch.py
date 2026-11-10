import hashlib
import unittest

from videoforge.pixellab.launch import resolve_target
from videoforge.pixellab.client import PixelLabError

A = "123e4567-e89b-12d3-a456-426614174007"
B = "123e4567-e89b-12d3-a456-426614174008"


class Mock:
    def __init__(self, entries, *, total=None):
        self.entries=entries
        self.total=len(entries) if total is None else total
    def characters(self):
        return {"characters": self.entries, "total": self.total}


class TargetTests(unittest.TestCase):
    def test_selects_only_matching_identity(self):
        expected=hashlib.sha256(B.encode()).hexdigest()
        self.assertEqual(resolve_target(Mock([{"id":A}, {"id":B}]),expected),B)

    def test_no_match_refuses_to_guess(self):
        with self.assertRaises(PixelLabError):
            resolve_target(Mock([{"id":A}]),hashlib.sha256(B.encode()).hexdigest())

    def test_incomplete_page_is_blocked(self):
        with self.assertRaises(PixelLabError):
            resolve_target(Mock([{"id":A}],total=2),hashlib.sha256(A.encode()).hexdigest())

    def test_bad_fingerprint_is_blocked(self):
        with self.assertRaises(PixelLabError):
            resolve_target(Mock([{"id":A}]),"not-a-digest")

    def test_no_ids_in_error(self):
        try:
            resolve_target(Mock([{"id":A}]),hashlib.sha256(B.encode()).hexdigest())
        except PixelLabError as exc:
            self.assertNotIn(A,str(exc))
            self.assertNotIn(B,str(exc))
