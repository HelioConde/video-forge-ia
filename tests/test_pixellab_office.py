"""Testes sem rede e sem créditos para Rooms e Objects PixelLab."""
import tempfile
import unittest
from pathlib import Path

from videoforge.pixellab.office_assets import (
    read_plan, list_all, existing_record, build_queue, run
)
from videoforge.pixellab.client import PixelLabError


class FakePixelLab:
    def __init__(self, room_records=None, object_records=None):
        self.rows = {
            "rooms": list(room_records or []),
            "objects": list(object_records or []),
        }
        self.posts = []
        self.count = 0
        self.next = 100

    def _request(self, method, path, payload=None, *, query=None, **kwargs):
        if method == "GET" and path in ("/rooms", "/objects"):
            key = path.removeprefix("/")
            start = (query or {}).get("offset", 0)
            limit = (query or {}).get("limit", 50)
            return {key: [dict(x) for x in self.rows[key][start:start+limit]],
                    "total": len(self.rows[key])}
        if method == "GET" and (path.startswith("/rooms/") or path.startswith("/objects/")):
            kind, asset_id = path.split("/")[1:3]
            matched = next((x for x in self.rows[kind] if x["id"] == asset_id), None)
            if matched is None:
                raise AssertionError("Asset ID desconhecido")
            return dict(matched)
        if method == "POST" and path in ("/create-room", "/create-object-pro-flash"):
            self.posts.append((path, payload))
            self.count += 1
            kind = "rooms" if path == "/create-room" else "objects"
            ident = f"123e4567-e89b-12d3-a456-{self.next:012d}"
            self.next += 1
            self.rows[kind].append({"id":ident,"name":payload["name"],
                                    "status":"completed","can_be_style_room":True})
            return {("room_id" if kind == "rooms" else "object_id"):ident}
        raise AssertionError(f"Chamada inesperada: {method} {path}")


class OfficeAssetsTests(unittest.TestCase):
    def setUp(self):
        self.plan=read_plan()

    def test_plan_has_three_rooms_six_objects(self):
        self.assertEqual(len(self.plan["rooms"]),3)
        self.assertEqual(len(self.plan["objects"]),6)
        self.assertEqual(len(build_queue(self.plan)),9)

    def test_readonly_audit_never_generates(self):
        fake=FakePixelLab()
        with tempfile.TemporaryDirectory() as temp:
            report=run(fake,self.plan,mode="plan",output=Path(temp))
            self.assertEqual(len(report["assets"]),9)
            self.assertEqual(report["generated"],0)
            self.assertEqual(fake.posts,[])
            self.assertTrue((Path(temp)/"report.json").exists())

    def test_first_batch_creates_one_room_and_two_objects(self):
        fake=FakePixelLab()
        with tempfile.TemporaryDirectory() as temp:
            result=run(fake,self.plan,mode="generate",stage="first",max_new=3,
                       authorized=True,report_public=True,output=Path(temp))
            self.assertEqual(result["generated"],3)
            self.assertEqual([x[0] for x in fake.posts],
                             ["/create-room","/create-object-pro-flash",
                              "/create-object-pro-flash"])
            self.assertFalse(fake.posts[0][1]["pieces"])
            self.assertEqual(fake.posts[1][1]["n_directions"],1)
            self.assertNotIn(fake.rows["rooms"][0]["id"],(Path(temp)/"report.json").read_text())

    def test_same_assets_are_reused_without_second_charge(self):
        fake=FakePixelLab()
        with tempfile.TemporaryDirectory() as temp:
            run(fake,self.plan,mode="generate",stage="first",max_new=3,
                authorized=True,report_public=True,output=Path(temp))
            original_calls=len(fake.posts)
            result=run(fake,self.plan,mode="generate",stage="first",max_new=3,
                       authorized=True,report_public=True,output=Path(temp))
            self.assertEqual(len(fake.posts),original_calls)
            self.assertEqual(result["reused"],3)

    def test_remaining_rooms_inherit_original_style(self):
        fake=FakePixelLab([{"id":"123e4567-e89b-12d3-a456-426614174000",
                            "name":self.plan["rooms"][0]["name"],
                            "status":"completed","can_be_style_room":True}])
        with tempfile.TemporaryDirectory() as temp:
            result=run(fake,self.plan,mode="generate",stage="remaining",max_new=6,
                       authorized=True,report_public=True,output=Path(temp))
            self.assertEqual(result["generated"],6)
            self.assertEqual(len(fake.posts),6)
            self.assertEqual(fake.posts[0][1]["style_room_id"],
                             fake.rows["rooms"][0]["id"])
            self.assertEqual(fake.posts[1][1]["style_room_id"],
                             fake.rows["rooms"][0]["id"])

    def test_missing_style_room_blocks_paid_create(self):
        fake=FakePixelLab()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PixelLabError):
                run(fake,self.plan,mode="generate",stage="remaining",max_new=6,
                    authorized=True,report_public=True,output=Path(temp))
            self.assertEqual(fake.posts,[])

    def test_paid_requires_explicit_authorization(self):
        fake=FakePixelLab()
        with self.assertRaises(PixelLabError):
            run(fake,self.plan,mode="generate",stage="first",authorized=False,
                report_public=True)
        self.assertEqual(fake.posts,[])

    def test_duplicate_name_blocks_generations(self):
        fake=FakePixelLab(room_records=[
            {"id":"x","name":self.plan["rooms"][0]["name"],"status":"completed"},
            {"id":"y","name":self.plan["rooms"][0]["name"],"status":"completed"}])
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PixelLabError):
                run(fake,self.plan,mode="generate",stage="first",max_new=3,
                    authorized=True,report_public=True,output=Path(temp))
        self.assertEqual(fake.posts,[])

    def test_any_failed_existing_asset_blocks_generation(self):
        fake=FakePixelLab(room_records=[
            {"id":"123e4567-e89b-12d3-a456-426614174000",
             "name":self.plan["rooms"][0]["name"],"status":"failed"}])
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PixelLabError):
                run(fake,self.plan,mode="generate",stage="first",max_new=3,
                    authorized=True,report_public=True,output=Path(temp))
        self.assertEqual(fake.posts,[])

    def test_pagination_reads_all_pages_without_skipping(self):
        fake=FakePixelLab(room_records=[{"id":str(i),"name":f"other-{i}","status":"completed"}
                                             for i in range(225)])
        result=list_all(fake,"rooms")
        self.assertEqual(len(result),225)
        self.assertEqual(result[224]["name"],"other-224")


if __name__ == "__main__":
    unittest.main()
