"""Recover a continuous display field from recorded finite-volume cell values.

Nodal values are convex, volume-weighted averages over incident tetrahedra.
Rendering interpolates these nodal scalars linearly across visible triangles.
This changes the display reconstruction only, never the STEPS trajectory.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix

ROOT=Path(__file__).resolve().parents[1]


def reconstruct():
    source=ROOT/'engine'
    out=ROOT/'engine-smooth'
    out.mkdir(exist_ok=True)
    meta=json.loads((source/'manifest.json').read_text())
    expanded=np.fromfile(source/'positions.f32',dtype='<f4').reshape(-1,3)
    vertices,inverse=np.unique(expanded,axis=0,return_inverse=True)
    faces=inverse.reshape(-1,3)
    face_cells=np.fromfile(source/'face-cells.f32',dtype='<f4').astype(int)
    # Reconstruct topology from the four faces stored for every tetrahedron.
    cell_nodes=[set() for _ in range(meta['cells'])]
    for f,c in zip(faces,face_cells):
        cell_nodes[c].update(map(int,f))
    assert all(len(n)==4 for n in cell_nodes)
    tets=np.array([sorted(n) for n in cell_nodes],dtype=np.uint32)
    xyz=vertices.astype(float)
    volumes=np.abs(np.linalg.det(xyz[tets[:,1:]]-xyz[tets[:,:1]]))/6
    assert np.all(volumes>0)
    rows=tets.ravel()
    cols=np.repeat(np.arange(len(tets)),4)
    weights=np.repeat(volumes,4)
    sums=np.bincount(rows,weights=weights,minlength=len(vertices))
    operator=coo_matrix((weights/sums[rows],(rows,cols)),shape=(len(vertices),len(tets))).tocsr()
    constant_error=float(np.abs(operator@np.ones(len(tets))-1).max())
    assert constant_error<1e-12
    adjacency={}
    # Each stored face is oriented outward relative to its first incident cell.
    for f,c in zip(faces,face_cells):
        key=tuple(sorted(map(int,f)))
        if key not in adjacency:
            tri=list(map(int,f))
            opposite=next(v for v in tets[c] if v not in tri)
            a,b,d=xyz[tri]
            if np.dot(np.cross(b-a,d-a),xyz[opposite]-a)>0:
                tri[1],tri[2]=tri[2],tri[1]
            adjacency[key]=[tri,int(c),-1]
        else:
            assert adjacency[key][2]==-1,'Non-manifold mesh face'
            adjacency[key][2]=int(c)
    unique_faces=np.array([x[0] for x in adjacency.values()],dtype='<u4')
    neighbors=np.array([x[1:] for x in adjacency.values()],dtype='<i4')
    np.asarray(vertices,dtype='<f4').tofile(out/'vertices.f32')
    tets.astype('<u4').tofile(out/'tetrahedra.u32')
    unique_faces.tofile(out/'faces.u32')
    neighbors.tofile(out/'neighbors.i32')
    np.asarray(xyz[tets].mean(axis=1),dtype='<f4').tofile(out/'cell-centers.f32')
    report={'method':'At each mesh node: sum(V_cell * c_cell) / sum(V_cell) over all incident tetrahedra. Linear interpolation of scalar concentration within rendered triangles.',
            'geometry':'Original mesh coordinates unchanged. Only exposed faces of the selected tetrahedra are rendered.',
            'normals':'Area-weighted shared-node normals on the exposed surface; display shading only.',
            'timeInterpolation':False,'volumeConservationClaim':False,'constantFieldMaximumError':constant_error,
            'nodes':len(vertices),'cells':len(tets),'faces':len(unique_faces),
            'boundaryFaces':int(np.sum(neighbors[:,1]<0)),
            'times':meta['times'],'concentrationUnit':'µM','positionUnit':'µm',
            'sourceManifestSHA256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
            'sourceSHA256':{},'species':{}}
    for species in ['X','Y']:
        path=source/f'{species}.f32'
        values=np.fromfile(path,dtype='<f4').reshape(len(meta['times']),len(tets))
        nodal=np.asarray((operator@values.T).T,dtype='<f4')
        assert np.all(np.isfinite(nodal)) and np.all(nodal>=0)
        # Positive normalized weights cannot invent concentration extrema.
        assert nodal.min()>=values.min() and nodal.max()<=values.max()
        nodal.tofile(out/f'{species}.f32')
        report['sourceSHA256'][species]=hashlib.sha256(path.read_bytes()).hexdigest()
        report['species'][species]={'min':float(nodal.min()),'max':float(nodal.max()),'displayP995':float(np.quantile(nodal,.995))}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='times'},indent=2))


if __name__=='__main__':
    reconstruct()
