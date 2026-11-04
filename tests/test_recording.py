"""Check displayed values against the original published scientific output."""
import hashlib
from array import array
import json
import math
from pathlib import Path
import struct
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class RecordingTests(unittest.TestCase):
    def test_baseline_conversion_matches_every_source_value(self):
        meta = json.loads((ROOT / 'data/manifest.json').read_text())
        source = ROOT / 'upstream/square.vtkjs'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), meta['sourceSHA256'])
        with zipfile.ZipFile(source) as archive:
            series = json.loads(archive.read('0/index.json'))['series']
            self.assertEqual(meta['times'], [s['timeStep'] for s in series])
            for species in ['X', 'Y']:
                raw = (ROOT / f'data/{species}.f32').read_bytes()
                displayed = struct.unpack('<' + str(len(raw)//4) + 'f', raw)
                self.assertEqual(len(displayed), len(series)*meta['faces'])
                for i, entry in enumerate(series):
                    d = json.loads(archive.read('0/' + entry['url'] + '/index.json'))
                    field = next(a['data'] for a in d['cellData']['arrays'] if a['data']['name'] == species + '.Conc')
                    original = struct.unpack('<' + str(meta['faces']) + 'd', archive.read('data/' + field['ref']['id']))
                    actual = displayed[i*meta['faces']:(i+1)*meta['faces']]
                    for a, b in zip(actual, original):
                        self.assertTrue(math.isclose(a, b*1e6, rel_tol=6e-8, abs_tol=1e-9))

    def test_volume_mesh_quality_report(self):
        report = json.loads((ROOT / 'meshes/quality.json').read_text())
        self.assertTrue(report['watertight'])
        self.assertTrue(report['connectedBoundary'])
        self.assertEqual(report['nonManifoldFaces'], 0)
        self.assertGreater(report['minimumTetVolumeUm3'], 0)
        self.assertGreater(report['minSICN'], .1)
        self.assertLess(report['volumeRelativeError'], .03)
        from scripts.build_volume import validate_surface
        self.assertGreater(validate_surface(ROOT/'meshes/twin-chambers.stl'), 0)

    def test_custom_recording_consistency(self):
        path = ROOT / 'volume/manifest.json'
        if not path.exists():
            self.skipTest('Custom STEPS run not yet available')
        meta = json.loads(path.read_text())
        self.assertEqual(meta['meshSHA256'], hashlib.sha256((ROOT/'meshes/twin-chambers.msh').read_bytes()).hexdigest())
        self.assertEqual(meta['faces'], 4*meta['cells'])
        self.assertTrue(all(a < b for a,b in zip(meta['times'],meta['times'][1:])))
        for species in ['X','Y']:
            raw = (ROOT / f'volume/{species}.f32').read_bytes()
            values = struct.unpack('<'+str(len(raw)//4)+'f',raw)
            self.assertEqual(len(values),meta['cells']*len(meta['times']))
            self.assertTrue(all(math.isfinite(v) and v>=0 for v in values))
            self.assertGreater(max(values)-min(values),1)

    def test_engine_volume_and_recording(self):
        report = json.loads((ROOT/'meshes/engine-quality.json').read_text())
        self.assertTrue(report['watertight'] and report['connectedBoundary'])
        self.assertEqual(report['statorVanes'], 12)
        self.assertEqual(report['bypassPassages'], 6)
        self.assertGreater(report['minSICN'], .1)
        self.assertLess(report['volumeRelativeError'], .03)
        from scripts.build_volume import validate_surface
        self.assertEqual(validate_surface(ROOT/'meshes/engine-cavity.stl'), report['inputSurfaceTriangles'])
        meta = json.loads((ROOT/'engine/manifest.json').read_text())
        self.assertEqual(meta['meshSHA256'], hashlib.sha256((ROOT/'meshes/engine-cavity.msh').read_bytes()).hexdigest())
        self.assertEqual(meta['cells'], report['tetrahedra'])
        self.assertEqual(meta['faces'], meta['cells']*4)
        self.assertEqual(len(meta['times']), 251)
        self.assertEqual(meta['times'][0], 0)
        self.assertAlmostEqual(meta['times'][-1], 10)
        self.assertAlmostEqual(meta['saveIntervalSeconds'], .04)
        for i,t in enumerate(meta['times']):
            self.assertAlmostEqual(t,i*.04,places=9)
        self.assertTrue(all(a < b for a,b in zip(meta['times'],meta['times'][1:])))
        for species in ['X','Y']:
            raw=(ROOT/f'engine/{species}.f32').read_bytes()
            values=array('f',raw)
            self.assertEqual(len(values), meta['cells']*len(meta['times']))
            self.assertTrue(all(math.isfinite(v) and v>=0 for v in values))
            self.assertGreater(meta['species'][species]['displayP995'],0)
            self.assertLess(meta['species'][species]['displayP995'],max(values))
            for region in ['left','right']:
                self.assertEqual(len(meta['traces'][species][region]), len(meta['times']))
                self.assertTrue(all(math.isfinite(v) and v>=0 for v in meta['traces'][species][region]))

    def test_twin_chamber_assets_unchanged(self):
        first=json.loads((ROOT/'docs/validation.json').read_text())
        for name,digest in first['recordingSHA256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'volume'/name).read_bytes()).hexdigest(),digest)


if __name__ == '__main__':
    unittest.main()
