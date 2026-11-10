import unittest
from videoforge.pixellab.production_object_audit import inspect
from videoforge.pixellab.client import PixelLabError

OBJ="123e4567-e89b-12d3-a456-426614174006"
class Fake:
    def _request(self,method,path,*,query=None):
        if path=="/objects":
            return {"total":1,"objects":[{"id":OBJ,"name":"VideoForge AI - Office Chair 2026","status":"completed"}]}
        if path=="/objects/"+OBJ:
            return {"animations":[{"display_name":"rotate_chair_left","directions":[]}]}
        raise AssertionError(path)

class ObjectAuditTest(unittest.TestCase):
    def test_only_reads_and_does_not_leak_identifier(self):
        report=inspect(Fake())
        self.assertEqual(report["objects"]["rotate_chair_left"]["status"],"existing")
        self.assertEqual(report["objects"]["rotate_chair_right"]["status"],"needs_generation")
        self.assertEqual(report["objects"]["open_cabinet"]["status"],"object_not_created")
        self.assertNotIn(OBJ,str(report))
if __name__=="__main__":
    unittest.main()
