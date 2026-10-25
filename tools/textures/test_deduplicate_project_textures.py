# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/test_deduplicate_project_textures.py (imported 2026-10-25)
# Changed: header only
"""Reference, import-semantics and repeat-export regressions for texture sharing."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from deduplicate_project_textures import deduplicate, ALIASES


class TextureSharingTests(unittest.TestCase):
    def texture(self, project, name, normal=0):
        path = project / "assets" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"identical texture bytes")
        Path(str(path) + ".import").write_text(
            '[remap]\nimporter="texture"\ntype="CompressedTexture2D"\n'
            f'uid="uid://{name.replace("/", "_")}"\n[params]\ncompress/normal_map={normal}\n')
        return path

    def test_shared_references_seals_uids_backup_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            a = self.texture(project, "textures/a space.webp")
            b = self.texture(project, "models/b.webp")
            scene = project / "assets/models/model.gltf"
            digest = hashlib.sha256(a.read_bytes()).hexdigest()
            scene.write_text(json.dumps({"images": [{"uri": "b.webp"}], "asset": {"extras": {
                "render_dependency_sha256": [{"uri": "b.webp", "sha256": digest}]}}}))
            material = project / "material.tres"
            material.write_text('[ext_resource type="Texture2D" uid="uid://models_b.webp" path="res://assets/models/b.webp"]')
            original = scene.read_bytes()
            preview = deduplicate(project)
            self.assertEqual(preview["saved_bytes"], a.stat().st_size)
            self.assertEqual(scene.read_bytes(), original)
            report = deduplicate(project, base / "backup", True)
            self.assertEqual(report["removed_files"], 2)
            self.assertFalse(a.exists())
            self.assertFalse(b.exists())
            shared = next((project / "assets/textures/shared").rglob("*.webp"))
            document = json.loads(scene.read_text())
            from urllib.parse import unquote
            self.assertEqual((scene.parent / unquote(document["images"][0]["uri"])).resolve(), shared.resolve())
            self.assertEqual(document["asset"]["extras"]["render_dependency_sha256"][0]["sha256"], digest)
            self.assertIn(shared.relative_to(project).as_posix(), material.read_text())
            self.assertIn('uid://textures_a space.webp', material.read_text())
            self.assertEqual((base / "backup/assets/models/model.gltf").read_bytes(), original)
            self.assertEqual(deduplicate(project, apply=True)["removed_files"], 0)
            self.texture(project, "models/b.webp")
            self.assertEqual(deduplicate(project, base / "again", True)["created_files"], 0)
            self.assertTrue((project / ALIASES).exists())

    def test_different_import_settings_are_not_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.texture(project, "color.webp", 0)
            self.texture(project, "normal.webp", 1)
            self.assertEqual(deduplicate(project)["removed_files"], 0)

    def test_signature_collision_stops_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            a = self.texture(project, "a.webp")
            b = self.texture(project, "b.webp")
            (project / "manifest.json").write_text(json.dumps({"res://assets/a.webp|x": 1, "res://assets/b.webp|x": 2}))
            with self.assertRaisesRegex(ValueError, "collapse"):
                deduplicate(project, apply=True)
            self.assertTrue(a.exists() and b.exists())


if __name__ == "__main__":
    unittest.main()
