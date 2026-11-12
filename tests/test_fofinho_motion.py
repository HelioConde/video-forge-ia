"""No-cost motion test for Fofinho Part 3 and VideoForge Remotion adapter."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from videoforge.generators.autoeditor import load_manifest, build_remotion_props, validate_manifest
from videoforge.motion.remotion_overlay import apply_motion_overlay, MotionOverlayError
from videoforge.production.motion_plan import (
    SCHEMA, MotionPlanError, validate_motion_plan, motion_for_actor, verify_animated_scene,
)
from videoforge.production.scene_layers import validate_layer_plan, count_image_requests

ROOT = Path(__file__).resolve().parents[1]


class FofinhoMotionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(ROOT/"geradores/autoeditor/exemplo-manifesto.json")

    def test_storyboard_assigns_animation_to_correct_character_and_prop(self):
        scene = self.manifest["cenas"][5]
        plan = scene["motion_plan"]
        self.assertEqual(plan["schema"], SCHEMA)
        self.assertEqual([x["id"] for x in plan["cues"]], ["porta-da-torre", "pesquisadora"])
        self.assertEqual(motion_for_actor(plan,"porta-da-torre")[0]["motion"],"sway")
        self.assertEqual(motion_for_actor(plan,"pesquisadora")[0]["motion"],"idle")
        self.assertEqual(motion_for_actor(plan,"nonexistent"),[])
        self.assertEqual(count_image_requests(self.manifest),26)

    def test_paw_animation_fails_without_separate_rgba_layer(self):
        layer_plan=validate_layer_plan({
            "characters":[{"id":"fofinho","description":"Mesmo gatinho azul da cena"}],
            "movable_props":[{"id":"gotinha","description":"Gotinha azul em movimento"}]
        })
        cue={"id":"fofinho","motion":"paw-lift","start":.1,"end":.8,"distance":20}
        with self.assertRaisesRegex(MotionPlanError,"CORRECT_LAYER_ROLE"):
            validate_motion_plan({"schema":SCHEMA,"cues":[cue]},layer_plan)
        with self.assertRaisesRegex(MotionPlanError,"NOT_EXTRACTED"):
            validate_motion_plan({"schema":SCHEMA,"cues":[
                {**cue,"id":"patinha-fofinho"}]},layer_plan)
        character_parts=[{"id":"patinha-fofinho","parent_id":"fofinho",
                          "description":"Patinha azul separada no ombro do gato"}]
        layer_plan=validate_layer_plan({**layer_plan,"character_parts":character_parts})
        result=validate_motion_plan({"schema":SCHEMA,"cues":[
            {**cue,"id":"patinha-fofinho"},
            {"id":"gotinha","motion":"rise","start":.1,"end":.7,"distance":30},
        ]},layer_plan)
        self.assertEqual(len(result["cues"]),2)
        with self.assertRaisesRegex(MotionPlanError,"MISSING_FROM_COMPOSITION"):
            verify_animated_scene(result,[{"id":"fofinho"},{"id":"gotinha"}])
        audit=verify_animated_scene(result,[
            {"id":"fofinho"},{"id":"patinha-fofinho"},{"id":"gotinha"}])
        self.assertTrue(audit["all_motion_actors_have_rgba_layers"])
        self.assertFalse(audit["youtube_upload_approved"])

    def test_motion_rejects_overlap_wrong_prop_rotation_and_out_of_bound_distance(self):
        layer_plan=validate_layer_plan({"characters":[],"movable_props":[
            {"id":"gota","description":"Gota azul com fundo transparente"}]})
        valid={"id":"gota","motion":"rise","start":.1,"end":.6,"distance":20}
        for cues,reason in [
            ([valid,dict(valid,start=.5,end=.9)],"OVERLAPPING"),
            ([dict(valid,motion="paw-wave")],"CORRECT_LAYER_ROLE"),
            ([dict(valid,distance=300)],"TIMING_OR_DISTANCE"),
            ([dict(valid,start=1.0,end=.7)],"TIMING_OR_DISTANCE"),
            ([dict(valid,id="../../token")],"NOT_EXTRACTED"),
        ]:
            with self.subTest(reason=reason),self.assertRaisesRegex(MotionPlanError,reason):
                validate_motion_plan({"schema":SCHEMA,"cues":cues},layer_plan)

    def test_fofinho_part3_blueprint_has_18_beats_and_no_unapproved_cast(self):
        path=ROOT/"canal/manu-kids/fofinho-parte03-motion-blueprint.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["mode"],"plan_only")
        self.assertFalse(data["execution_enabled"])
        self.assertFalse(data["upload_enabled"])
        self.assertEqual([x["beat"] for x in data["beats"]],list(range(1,19)))
        all_actors={a for x in data["beats"] for a in x["required_rgba_actors"]}
        self.assertTrue({"fofinho","gotinha","patinha-fofinho","emanuelly","borboleta"}<=all_actors)
        self.assertFalse({"fofinha-arco-iris","fofinha-rosa","raposo"}&all_actors)
        for scene in data["beats"]:
            self.assertTrue(all(x["id"] in scene["required_rgba_actors"]
                                for x in scene["cues"]))
            for actor in scene["required_character_parts"]:
                self.assertTrue(actor in scene["required_rgba_actors"])
            # All cues must conform to the same role-scoped contract.
            roles={"fofinho":"characters","emanuelly":"characters",
                   "patinha-fofinho":"character_parts","mao-emanuelly":"character_parts"}
            plan={"characters":[],"movable_props":[],"character_parts":[]}
            for actor in scene["required_rgba_actors"]:
                group=roles.get(actor,"movable_props")
                item={"id":actor,"description":"Elemento da cena original de Fofinho"}
                if group=="character_parts":item["parent_id"]="fofinho" if actor.startswith("patinha") else "emanuelly"
                plan[group].append(item)
            # For independent body parts, parent must also be included.
            layer=validate_layer_plan(plan)
            approved=validate_motion_plan({"schema":SCHEMA,"cues":scene["cues"]},layer)
            self.assertEqual(len(approved["cues"]),len(scene["cues"]))

    def test_actual_remotion_props_reference_isolated_paw_and_droplet(self):
        manifest=copy.deepcopy(self.manifest)
        scene=manifest["cenas"][0]
        scene["layer_plan"]={
            "characters":[{"id":"fofinho","description":"Mesmo gato azul separado da cena"}],
            "movable_props":[{"id":"gotinha","description":"Uma gotinha azul fora da patinha"}],
            "character_parts":[{"id":"patinha","parent_id":"fofinho",
                                "description":"Patinha articulada do Fofinho isolada"}]
        }
        scene["motion_plan"]={"schema":SCHEMA,"cues":[
            {"id":"patinha","motion":"paw-lift","start":.1,"end":.75,"distance":26},
            {"id":"gotinha","motion":"rise","start":.12,"end":.6,"distance":36},
            {"id":"gotinha","motion":"fall","start":.61,"end":.91,"distance":36}
        ]}
        raw=validate_manifest(manifest)
        self.assertEqual(count_image_requests(raw),28)
        layer_rows=[]
        for i,shot in enumerate(raw["cenas"],1):
            row={"scene_id":shot["id"],"background":{"file":f"scene-{i}/background.png"},
                 "characters":[],"movable_props":[],"character_parts":[]}
            if i==1:
                row["characters"]=[{"id":"fofinho","file":"scene-1/characters/fofinho.png","alpha_coverage":.2}]
                row["movable_props"]=[{"id":"gotinha","file":"scene-1/movable_props/gotinha.png",
                                      "alpha_coverage":.05,"bbox":[240,340,320,470]}]
                row["character_parts"]=[{"id":"patinha","parent_id":"fofinho",
                                         "file":"scene-1/character_parts/patinha.png",
                                         "alpha_coverage":.04,"bbox":[250,550,380,710]}]
            else:
                row["characters"]=[{"id":"pesquisadora",
                                   "file":f"scene-{i}/characters/pesquisadora.png",
                                   "alpha_coverage":.2}]
                if i in (2,6):
                    prop_id="caderno" if i==2 else "porta-da-torre"
                    row["movable_props"]=[{"id":prop_id,
                                          "file":f"scene-{i}/movable_props/{prop_id}.png",
                                          "alpha_coverage":.1,"bbox":[120,220,450,650]}]
            layer_rows.append(row)
        words=[{"start":i*.36+.3,"end":i*.36+.5,"text":w}
               for i,w in enumerate(" ".join(s["narracao"] for s in raw["cenas"]).split())]
        props=build_remotion_props(raw,110.0,words,staging_id="vf-motion-test",
                                  layer_document={"scenes":layer_rows})
        layers=props["scenes"][0]["layers"]
        self.assertEqual([x["role"] for x in layers],
                         ["front_character","hero_prop","character_part"])
        self.assertEqual(layers[1]["motion"][0]["motion"],"rise")
        self.assertEqual(layers[2]["motion"][0]["motion"],"paw-lift")
        self.assertGreater(layers[2]["anchorY"],0)
        self.assertNotIn("motion",layers[0])
        self.assertFalse(props.get("youtube_upload_approved",False))

    def test_motion_overlay_patches_known_master_only(self):
        original="""import {meshFrameIndex} from './pose-timeline';
  meshFrames?:{fps:number;frames:string[]}
          const transform=!staticLayer && pose.enabled
            ? 'translate('+pose.translateX.toFixed(3)+'px,'+
              pose.translateY.toFixed(3)+'px) rotate('+pose.rotateDeg.toFixed(4)+
              'deg)'
            : undefined;
            transform,
            transformOrigin:(layer.anchorX ?? 50)+'% '+(layer.anchorY ?? 80)+'%',"""
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"src";src.mkdir()
            master=src/"master-short.tsx";master.write_text(original,encoding="utf-8")
            (src/"character-idle.ts").touch()
            (src/"pose-timeline.ts").touch()
            h=apply_motion_overlay(Path(tmp))
            self.assertEqual(len(h),64)
            output=master.read_text(encoding="utf-8")
            self.assertIn("videoForgeMotionAtFrame",output)
            self.assertIn("motion?:VideoForgeMotionCue[]",output)
            self.assertTrue((src/"videoforge-motion.ts").is_file())
            with self.assertRaisesRegex(MotionOverlayError,"ALREADY_INSTALLED"):
                apply_motion_overlay(Path(tmp))
            master.write_text(original.replace("meshFrameIndex","unexpected"),
                              encoding="utf-8")
            (src/"videoforge-motion.ts").unlink()
            with self.assertRaisesRegex(MotionOverlayError,"UNSUPPORTED"):
                apply_motion_overlay(Path(tmp))


if __name__ == "__main__":
    unittest.main()
