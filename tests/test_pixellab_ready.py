import tempfile
import unittest
from pathlib import Path
from scripts.export_pixellab_ready import export_when_ready
from videoforge.pixellab.client import PixelLabError

class Fake:
    def __init__(self,status):
        self.status=status
        self.calls=0
    def download(self,cid,*,spritesheet):
        self.calls+=1
        if self.status=="locked":
            raise PixelLabError("HTTP 423: Personagem ainda está sendo processado.")
        if self.status=="fail":
            raise PixelLabError("HTTP 402: Créditos insuficientes.")
        return b"PK\x03\x04complete"

class ReadinessTests(unittest.TestCase):
    def test_locked_waits_without_writing_or_retrying(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"pixels.zip";api=Fake("locked")
            self.assertEqual(export_when_ready(api,"test",path),"source_processing")
            self.assertFalse(path.exists())
            self.assertEqual(api.calls,1)
    def test_export_writes_bytes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"pixels.zip";api=Fake("ready")
            self.assertEqual(export_when_ready(api,"test",path),"exported")
            self.assertEqual(path.read_bytes(),b"PK\x03\x04complete")
            self.assertEqual(api.calls,1)
    def test_other_api_failures_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PixelLabError):
                export_when_ready(Fake("fail"),"test",Path(tmp)/"pixels.zip")

if __name__=="__main__":
    unittest.main()
