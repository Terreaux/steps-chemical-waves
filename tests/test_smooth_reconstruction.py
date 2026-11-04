"""Check a visual reconstruction independently against recorded cell data."""
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


class SmoothReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT/'engine-smooth'
        cls.meta=json.loads((cls.root/'manifest.json').read_text())
        cls.vertices=np.fromfile(cls.root/'vertices.f32',dtype='<f4').reshape(-1,3).astype(float)
        cls.tets=np.fromfile(cls.root/'tetrahedra.u32',dtype='<u4').reshape(-1,4)
        cls.volumes=np.abs(np.linalg.det(cls.vertices[cls.tets[:,1:]]-cls.vertices[cls.tets[:,:1]]))/6

    def test_sources_and_time_samples_are_preserved(self):
        self.assertEqual(self.meta['sourceManifestSHA256'],hashlib.sha256((ROOT/'engine/manifest.json').read_bytes()).hexdigest())
        self.assertEqual(self.meta['times'][0],0)
        self.assertEqual(self.meta['times'][-1],10)
        self.assertEqual(len(self.meta['times']),251)
        self.assertFalse(self.meta['timeInterpolation'])
        for species in ['X','Y']:
            self.assertEqual(self.meta['sourceSHA256'][species],hashlib.sha256((ROOT/f'engine/{species}.f32').read_bytes()).hexdigest())

    def test_recovered_values_match_weighted_source_cells(self):
        nodes=np.linspace(0,len(self.vertices)-1,31,dtype=int)
        for species in ['X','Y']:
            source=np.memmap(ROOT/f'engine/{species}.f32',dtype='<f4',mode='r',shape=(251,len(self.tets)))
            display=np.memmap(self.root/f'{species}.f32',dtype='<f4',mode='r',shape=(251,len(self.vertices)))
            for node in nodes:
                incident=np.flatnonzero(np.any(self.tets==node,axis=1))
                weights=self.volumes[incident]
                for frame in [0,63,125,250]:
                    expected=np.average(source[frame,incident],weights=weights)
                    self.assertAlmostEqual(float(display[frame,node]),float(expected),delta=max(1e-5,float(expected)*1e-6))
                    self.assertGreaterEqual(display[frame,node],source[frame,incident].min()-1e-5)
                    self.assertLessEqual(display[frame,node],source[frame,incident].max()+1e-5)

    def test_topology_and_constant_field(self):
        neighbors=np.fromfile(self.root/'neighbors.i32',dtype='<i4').reshape(-1,2)
        quality=json.loads((ROOT/'meshes/engine-quality.json').read_text())
        self.assertEqual(int(np.sum(neighbors[:,1]<0)),quality['boundaryTriangles'])
        self.assertTrue(np.all(neighbors[:,0]>=0))
        self.assertTrue(np.all(neighbors<len(self.tets)))
        self.assertLess(self.meta['constantFieldMaximumError'],1e-12)
        self.assertTrue(np.all(self.volumes>0))


if __name__=='__main__':
    unittest.main()
