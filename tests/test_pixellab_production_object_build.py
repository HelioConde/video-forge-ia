import tempfile
import unittest
from pathlib import Path
from videoforge.pixellab.production_object_build import build
from videoforge.pixellab.client import PixelLabError

CHAIR="123e4567-e89b-12d3-a456-426614174002"
CABINET="123e4567-e89b-12d3-a456-426614174003"
JOB="123e4567-e89b-12d3-a456-426614174004"

class Fake:
    def __init__(self):
        self.chair=["rotate_chair_left"]
        self.cabinet=[]
        self.have_cabinet=False
        self.posts=[]
    def _request(self,method,path,payload=None,*,query=None):
        if method=="GET" and path=="/objects":
            rows=[{"id":CHAIR,"name":"VideoForge AI - Office Chair 2026","status":"completed"}]
            if self.have_cabinet:
                rows.append({"id":CABINET,"name":"VideoForge AI - Cabinet 2026","status":"completed"})
            return {"objects":rows,"total":len(rows)}
        if method=="GET" and path=="/objects/"+CHAIR:
            return {"animations":[{"display_name":n} for n in self.chair]}
        if method=="GET" and path=="/objects/"+CABINET:
            return {"animations":[{"display_name":n} for n in self.cabinet],"status":"completed"}
        if method=="POST" and path=="/create-object-pro-flash":
            self.posts.append("create_cabinet")
            self.have_cabinet=True
            return {"object_id":CABINET}
        if method=="POST" and path.endswith("/animations"):
            self.posts.append(payload["display_name"])
            assert "directions" not in payload
            (self.chair if CHAIR in path else self.cabinet).append(payload["display_name"])
            return {"background_job_ids":[JOB]}
        raise AssertionError(path)
    def poll(self,ids,*,max_seconds=780):
        assert ids==[JOB]

class ObjectBuildTests(unittest.TestCase):
    def test_plan_is_read_only(self):
        api=Fake()
        with tempfile.TemporaryDirectory() as td:
            r=build(api,output=Path(td))
            self.assertEqual(r["status"],"planned_only")
            self.assertEqual(r["motions"]["rotate_chair_left"],"existing")
            self.assertEqual(api.posts,[])
    def test_requires_cost_approval(self):
        with self.assertRaises(PixelLabError):
            build(Fake(),mode="generate")
    def test_generation_reuses_existing(self):
        api=Fake()
        with tempfile.TemporaryDirectory() as td:
            # Substitute paid cabinet readiness for offline mock.
            from unittest.mock import patch
            with patch("videoforge.pixellab.production_object_build.wait_for_asset",
                       return_value={"status":"completed"}):
                r=build(api,mode="generate",authorized=True,output=Path(td))
            self.assertEqual(api.posts,["rotate_chair_right","create_cabinet","open_cabinet"])
            self.assertNotIn(CHAIR,(Path(td)/"report.json").read_text())
            self.assertEqual(r["status"],"completed")
if __name__=="__main__":
    unittest.main()
