"""Testes offline, nenhuma cobrança PixelLab."""
import tempfile
import unittest
from pathlib import Path
from videoforge.pixellab.production_animations import read_catalog, plan, run, _groups
from videoforge.pixellab.client import PixelLabError

CHAR="123e4567-e89b-12d3-a456-426614174001"
GID="123e4567-e89b-12d3-a456-426614174002"
JOB="123e4567-e89b-12d3-a456-426614174003"

class Fake:
    def __init__(self):
        self.groups=[{"display_name":"idle","animation_group_id":GID,
                      "directions":[{"direction":"south"}]}]
        self.posts=[]
    def character(self,cid):
        assert cid==CHAR
        return {"animations":self.groups}
    def animate(self,cid,*,name,description,direction,frame_count,animation_group_id=None):
        self.posts.append((name,direction,animation_group_id))
        existing=next((x for x in self.groups if x["display_name"]==name),None)
        if existing is None:
            existing={"display_name":name,"animation_group_id":GID,"directions":[]}
            self.groups.append(existing)
        assert direction not in [d["direction"] for d in existing["directions"]]
        existing["directions"].append({"direction":direction})
        return {"background_job_ids":[JOB],"animation_group_id":GID}
    def poll(self,jobs,*,max_seconds):
        assert jobs==[JOB]
        return {}

class ProductionTests(unittest.TestCase):
    def test_catalog_complete_and_unique(self):
        catalog=read_catalog()
        self.assertGreaterEqual(len(catalog),120)
        self.assertEqual(len({x["motion"] for x in catalog}),len(catalog))
        self.assertTrue({"talk_explain","sing_seated","sip_coffee","play_gamepad","wash_hands","edit_video"} <= {x["motion"] for x in catalog})
        self.assertTrue(any(x["kind"]=="object" for x in catalog))
        self.assertTrue(any(x["kind"]=="sequence" for x in catalog))
    def test_plan_does_not_replace_existing(self):
        fake=Fake()
        catalog=read_catalog()
        p=plan(fake.character(CHAR),catalog)
        self.assertGreater(len(p["pending"]),120)
        self.assertEqual(len(p["separate"]),15)
        self.assertEqual(fake.posts,[])
    def test_generation_only_new_and_group_reuse(self):
        fake=Fake()
        catalog=[x for x in read_catalog() if x["motion"]=="talk_explain"]
        with tempfile.TemporaryDirectory() as td:
            report=run(fake,CHAR,catalog,mode="generate",max_new=2,
                       authorized=True,public_report=True,output=Path(td),sleeper=lambda n:None)
            self.assertEqual(len(fake.posts),2)
            self.assertEqual(fake.posts[0][2],None)
            self.assertEqual(fake.posts[1][2],GID)
            self.assertEqual(report["status"],"completed")
            public=(Path(td)/"report.json").read_text()
            self.assertNotIn(CHAR,public)
            self.assertNotIn(JOB,public)
            self.assertNotIn(GID,public)
    def test_duplicate_direction_is_skipped(self):
        fake=Fake()
        fake.groups.append({"display_name":"talk_explain","animation_group_id":GID,
                            "directions":[{"direction":"south"}]})
        catalog=[x for x in read_catalog() if x["motion"]=="talk_explain"]
        with tempfile.TemporaryDirectory() as td:
            report=run(fake,CHAR,catalog,mode="generate",max_new=2,
                       authorized=True,public_report=True,output=Path(td),sleeper=lambda n:None)
            self.assertEqual(len(fake.posts),1)
            self.assertEqual(fake.posts[0][1],"north")
            self.assertEqual(len(report["completed"]),1)
    def test_authorization_required(self):
        fake=Fake()
        with self.assertRaises(PixelLabError):
            run(fake,CHAR,read_catalog(),mode="generate",max_new=4)
        self.assertEqual(fake.posts,[])
    def test_multiple_groups_same_name_refused(self):
        with self.assertRaises(PixelLabError):
            _groups({"animations":[{"display_name":"foo","directions":[]},{"display_name":"foo","directions":[]}]})
    def test_no_groups_refused(self):
        with self.assertRaises(PixelLabError):
            _groups({"animation_count":6})

if __name__=="__main__":
    unittest.main()
