# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/test_compress_project_textures.py (imported 2026-10-25)
# Changed: header only
"""Migration checks: alpha pixels, references, glTF extension, seals, and backups."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from compress_project_textures import migrate


class MigrationTests(unittest.TestCase):
    def test_migration_preserves_pixels_references_and_seal(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            project = base / "project"
            textures = project / "assets/textures"
            models = project / "assets/models"
            textures.mkdir(parents=True)
            models.mkdir(parents=True)
            source = textures / "alpha test.png"
            image = Image.new("RGBA", (2, 1))
            image.putdata([(17, 83, 191, 0), (4, 200, 8, 128)])
            image.save(source)
            original = source.read_bytes()
            Path(str(source) + ".import").write_text(
                '[remap]\nimporter="texture"\nuid="uid://preserved"\n'
                '[params]\ncompress/mode=2\ndetect_3d/compress_to=1\n')
            model = models / "test.gltf"
            model.write_text(json.dumps({"asset": {"version": "2.0", "extras": {
                "render_dependency_sha256": []}}, "images": [{"uri": "../textures/alpha%20test.png"}],
                "textures": [{"source": 0}]}))
            scene = project / "test.tres"
            scene.write_text('path="res://assets/textures/alpha test.png"\n')
            manifest = project / "manifest.json"
            signature = "res://assets/textures/alpha test.png||0.5"
            manifest.write_text(json.dumps({"layers": {signature: 7}}))
            report = migrate(project, base / "backup", workers=1)
            self.assertEqual(len(report["textures"]), 1)
            self.assertFalse(source.exists())
            self.assertEqual((base / "backup/assets/textures/alpha test.png").read_bytes(), original)
            target = source.with_suffix(".webp")
            self.assertEqual(Image.open(target).convert("RGBA").tobytes(), image.tobytes())
            document = json.loads(model.read_text())
            self.assertEqual(document["images"][0]["uri"], "../textures/alpha%20test.webp")
            self.assertNotIn("source", document["textures"][0])
            self.assertEqual(document["textures"][0]["extensions"]["EXT_texture_webp"]["source"], 0)
            self.assertIn("EXT_texture_webp", document["extensionsRequired"])
            self.assertEqual(document["asset"]["extras"]["render_dependency_sha256"][0]["sha256"],
                             hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertIn("alpha test.webp", scene.read_text())
            self.assertEqual(json.loads(manifest.read_text())["layers"],
                             {"res://assets/textures/alpha test.webp||0.5": 7})
            self.assertIn('uid="uid://preserved"', Path(str(target) + ".import").read_text())
            self.assertEqual(migrate(project, base / "backup")["textures"], [])

    def test_existing_conflicting_webp_does_not_remove_original(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            project = base / "project"
            project.mkdir()
            source = project / "test.png"
            Image.new("RGB", (1, 1), "red").save(source)
            source.with_suffix(".webp").write_bytes(b"unrelated file")
            with self.assertRaisesRegex(ValueError, "Conflicting WebP"):
                migrate(project, base / "backup", workers=1)
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
