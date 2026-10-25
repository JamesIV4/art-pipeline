# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/test_gltf_opacity.py (imported 2026-10-25)
# Changed: header only
"""Small deterministic convention regression; no art/images are edited."""
import unittest
from PIL import Image
from gltf_opacity import sample_alpha, material_alpha, mask_visible, REPEAT, CLAMP, MIRROR, NEAREST


class AlphaTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGBA", (2, 2))
        self.image.putdata([(0, 0, 0, 255), (0, 0, 0, 0), (0, 0, 0, 64), (0, 0, 0, 192)])

    def test_top_left_origin(self):
        self.assertEqual(sample_alpha(self.image, (.25, .25)), 1)
        self.assertEqual(sample_alpha(self.image, (.75, .25)), 0)
        self.assertAlmostEqual(sample_alpha(self.image, (.25, .75)), 64/255)
        self.assertAlmostEqual(sample_alpha(self.image, (.75, .75)), 192/255)

    def test_wrong_blender_buffer_orientation_is_detected(self):
        # Blender pixel buffers are bottom-up; using raw glTF V without
        # conversion would interchange these asymmetric top/bottom values.
        wrong = self.image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        self.assertNotEqual(sample_alpha(wrong, (.25, .25)), sample_alpha(self.image, (.25, .25)))

    def test_bilinear(self):
        self.assertAlmostEqual(sample_alpha(self.image, (.5, .5)), (255+64+192)/1020)

    def test_repeat(self):
        self.assertEqual(sample_alpha(self.image, (1.25, .25), {"wrapS": REPEAT}), 1)
        self.assertEqual(sample_alpha(self.image, (-.75, .25), {"wrapS": REPEAT}), 1)

    def test_clamp(self):
        self.assertEqual(sample_alpha(self.image, (-10, .25), {"wrapS": CLAMP}), 1)
        self.assertEqual(sample_alpha(self.image, (10, .25), {"wrapS": CLAMP}), 0)

    def test_mirror(self):
        self.assertEqual(sample_alpha(self.image, (1.25, .25), {"wrapS": MIRROR}), 0)
        self.assertEqual(sample_alpha(self.image, (2.25, .25), {"wrapS": MIRROR}), 1)

    def test_nearest(self):
        self.assertEqual(sample_alpha(self.image, (.3, .3), {"magFilter": NEAREST}), 1)

    def test_opaque_ignores_all_alpha(self):
        self.assertEqual(material_alpha({"pbrMetallicRoughness": {"baseColorFactor": [1,1,1,0]}}, 0, 0), 1)

    def test_mask_factor_vertex_and_cutoff(self):
        mat = {"alphaMode": "MASK", "pbrMetallicRoughness": {"baseColorFactor": [1,1,1,.8]}}
        alpha = material_alpha(mat, 1, .5)
        self.assertEqual(alpha, .4)
        self.assertFalse(mask_visible(mat, alpha))
        self.assertTrue(mask_visible(mat, .5))
        mat["alphaCutoff"] = .6
        self.assertFalse(mask_visible(mat, .5))


if __name__ == "__main__":
    unittest.main()
