"""Contratos básicos de layout do escritório fullscreen, sem navegador ou servidor."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "site"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class OfficeUITests(unittest.TestCase):
    def test_canvas_is_main_scene(self):
        document=(ROOT/"index.html").read_text(encoding="utf-8")
        parser=Parser()
        parser.feed(document)
        self.assertTrue(any(tag=="canvas" and attrs.get("id")=="officeCanvas" for tag,attrs in parser.tags))
        self.assertTrue(any(tag=="canvas" and attrs.get("id")=="officeMiniMap" for tag,attrs in parser.tags))
        self.assertTrue(any(tag=="script" and attrs.get("src")=="./office-art.js" for tag,attrs in parser.tags))
        self.assertTrue(any(tag=="script" and attrs.get("src")=="./office-renderer.js" for tag,attrs in parser.tags))
        self.assertTrue(any(tag=="script" and attrs.get("src")=="./office-map.js" for tag,attrs in parser.tags))
        self.assertLess(document.index('./office-art.js'),document.index('./office-renderer.js'))
        self.assertTrue(any(tag=="script" and attrs.get("src")=="./app.js" for tag,attrs in parser.tags))

    def test_full_viewport_is_defined(self):
        css=(ROOT/"styles.css").read_text(encoding="utf-8")
        self.assertIn("100dvh",css)
        self.assertIn(".workspace{position:absolute;inset:0",css)
        self.assertIn("touch-action:none",css)
        self.assertIn(".mini-toggle",css)
        self.assertIn('data-collapsed="true"',(ROOT/"index.html").read_text(encoding="utf-8"))

    def test_original_canvas_renderer_supports_controls(self):
        renderer=(ROOT/"office-renderer.js").read_text(encoding="utf-8")
        for method in ("pointerDown","pointerMove","pointerUp","zoomAt","reset","setAgents","setSelected","setMiniMap","renderMiniMap","focusAgent","defaultZoom"):
            self.assertIn(method,renderer)
        self.assertNotIn("https://",renderer)
        art=(ROOT/"office-art.js").read_text(encoding="utf-8")
        self.assertIn("window.VideoForgeArt=",art)
        # O cenário antigo permanece como fallback; PixelLab usa sprites locais.
        self.assertIn("officeBase(c)",art)
        self.assertIn("pixelBase(c)",art)
        self.assertIn("loadSprites",art)
        self.assertIn("setArtMode",art)
        self.assertIn("paintBackground:",art)
        self.assertIn("paintAgents:function",art)
        self.assertIn("CREATIVE  ROOM",art)
        self.assertIn("MEDIA LAB",art)

if __name__=="__main__":
    unittest.main()
