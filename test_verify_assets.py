import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from verify_assets import inspect_assets


class AssetChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'assets.json'
        image = Image.new('RGBA', (20, 20))
        image.paste((20, 80, 160, 254), (5, 5, 15, 15))
        image.save(self.root / 'pet.png')
        self.entry = {'path': 'pet.png', 'group': 'test', 'size': [20, 20], 'alpha': 'cutout'}

    def tearDown(self):
        self.temp.cleanup()

    def check(self, entries=None, layouts=None, **options):
        self.manifest.write_text(json.dumps({'files': entries or [self.entry],
                                            'layouts': layouts or []}), encoding='utf8')
        return inspect_assets(self.manifest, **options)

    def test_cutout_with_partial_opacity(self):
        report = self.check()
        self.assertFalse(report['errors'])
        self.assertEqual(report['images'][0]['visible_bbox'], (5, 5, 15, 15))
        self.assertEqual(report['visual_acceptance'], 'not_checked')

    def test_missing_wrong_size_opaque_and_empty_cutouts_fail(self):
        for change in [{'path': 'missing.png'}, {'size': [21, 20]}, {'size': [20.5, 20]},
                       {'alpha': 'opaque'}]:
            with self.subTest(change=change):
                self.assertTrue(self.check([{**self.entry, **change}])['errors'])
        for color in [(0, 0, 0, 255), (0, 0, 0, 0)]:
            Image.new('RGBA', (20, 20), color).save(self.root / 'pet.png')
            self.assertTrue(self.check()['errors'])

    def test_crop_outside_image_or_only_transparency_fails(self):
        for crop in [[0, 0, 21, 20], [0, 0, 4, 4], [5, 5, 5, 15]]:
            with self.subTest(crop=crop):
                self.assertTrue(self.check([{**self.entry, 'crops': {'part': crop}}])['errors'])
        self.assertFalse(self.check([{**self.entry, 'crops': {'part': [5, 5, 15, 15]}}])['errors'])

    def test_pose_canvas_mismatch_fails(self):
        Image.new('RGBA', (21, 20), (0, 0, 0, 255)).save(self.root / 'after.png')
        entries = [self.entry, {'path': 'after.png', 'alpha': 'opaque', 'size': [21, 20],
                                'same_canvas_as': 'pet.png'}]
        self.assertTrue(any('画布' in e for e in self.check(entries)['errors']))

    def test_only_current_group_and_external_asset_root(self):
        entries = [self.entry, {'path': 'unavailable.png', 'group': 'other'}]
        self.assertFalse(self.check(entries, group='test', root=self.root)['errors'])
        with self.assertRaises(ValueError):
            self.check(entries, group='unknown')

    def layout(self):
        return {'id': 'contact', 'size': [40, 40], 'layers': [
            {'id': 'a', 'path': 'pet.png', 'box': [0, 0, 20, 20]},
            {'id': 'b', 'path': 'pet.png', 'box': [5, 0, 20, 20]}], 'contacts': [
            {'id': 'hand', 'a': {'layer': 'a', 'point': [10, 10]},
             'b': {'layer': 'b', 'point': [5, 10]}, 'tolerance': 0}]}

    def test_contact_uses_placed_coordinates_and_visible_points(self):
        layout = self.layout()
        self.assertEqual(self.check(layouts=[layout])['contacts_checked'], 1)
        self.assertFalse(self.check(layouts=[layout])['errors'])
        layout['layers'][1]['box'][0] = 10
        self.assertTrue(self.check(layouts=[layout])['errors'])
        layout['contacts'][0]['b']['point'] = [0, 0]
        self.assertTrue(self.check(layouts=[layout])['errors'])

    def test_preview_does_not_overwrite_or_claim_visual_acceptance(self):
        folder = self.root / 'preview'
        report = self.check(layouts=[self.layout()], preview=folder)
        self.assertFalse(report['errors'])
        with Image.open(folder / 'contact.png') as image:
            self.assertEqual(image.size, (80, 40))
        self.assertTrue(self.check(layouts=[self.layout()], preview=folder)['errors'])


if __name__ == '__main__':
    unittest.main()
