"""Losslessly identify source faces; convert float64 M to float32 µM for playback.

No interpolation in space or time. The recording is a surface extraction of a
tetrahedral volume, not the complete volume concentration field.
"""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REV = '23d8e941fcdd3e8d64e0764233b81746671600ab'


def convert():
    source = ROOT / 'upstream/square.vtkjs'
    with zipfile.ZipFile(source) as z:
        def array(d):
            kind = {'Float64Array': 'd', 'Int32Array': 'i', 'Uint32Array': 'I'}[d['dataType']]
            return struct.unpack('<' + str(d['size']) + kind, z.read('data/' + d['ref']['id']))

        series = json.loads(z.read('0/index.json'))['series']
        first = json.loads(z.read('0/0/index.json'))
        points, polys = array(first['points']), array(first['polys'])
        assert len(polys) % 4 == 0 and all(n == 3 for n in polys[::4])
        faces = [polys[i+1:i+4] for i in range(0, len(polys), 4)]
        positions = [points[3*v+c]*1e6 for face in faces for v in face for c in range(3)]
        (ROOT / 'data/positions.f32').write_bytes(struct.pack('<' + str(len(positions)) + 'f', *positions))
        metadata = {'sourceRevision': REV, 'sourceSHA256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'faces': len(faces), 'vertices': len(points)//3, 'times': [s['timeStep'] for s in series],
                    'positionUnit': 'µm', 'concentrationUnit': 'µM', 'species': {}}
        for species in ['X', 'Y']:
            values = []
            for entry in series:
                d = json.loads(z.read('0/' + entry['url'] + '/index.json'))
                assert d['points'] == first['points'] and d['polys'] == first['polys']
                field = next(a['data'] for a in d['cellData']['arrays'] if a['data']['name'] == species + '.Conc')
                frame = array(field)
                assert len(frame) == len(faces) and all(v >= 0 for v in frame)
                values.extend(v*1e6 for v in frame)
            (ROOT / f'data/{species}.f32').write_bytes(struct.pack('<' + str(len(values)) + 'f', *values))
            metadata['species'][species] = {'min': min(values), 'max': max(values)}
        (ROOT / 'data/manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print(json.dumps({k:v for k,v in metadata.items() if k != 'times'}, indent=2))


if __name__ == '__main__':
    convert()
