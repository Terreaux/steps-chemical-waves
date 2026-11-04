"""Create a recognizable conceptual engine cavity from original CAD geometry.

This sealed microscale cavity is an idealized domain for Brusselator chemistry,
not a combustion, flow, heat-transfer, aerospace or engine-performance model.
The closed STL surface is reimported and tetrahedralized as an interior volume.
"""
from collections import Counter
import json
import math
from pathlib import Path

import gmsh
import numpy as np

from build_volume import validate_surface

ROOT = Path(__file__).resolve().parents[1]


def build():
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.add('engine-cavity-surface')
    occ = gmsh.model.occ
    outer = [(3, occ.addCone(-2.8, 0, 0, 1.3, 0, 0, 1.05, 1.65)),
             (3, occ.addCylinder(-1.5, 0, 0, 2.3, 0, 0, 1.65)),
             (3, occ.addCone(.8, 0, 0, 2.0, 0, 0, 1.65, .95))]
    loops = []
    # Six coolant/bypass passages connect the front and rear annular chambers.
    for i in range(6):
        a = i*math.pi/3
        radial = np.array([0, math.cos(a), math.sin(a)])
        front = np.array([-1.4, 0, 0]) + radial*1.95
        rear = np.array([1.0, 0, 0]) + radial*1.95
        loops.append((3, occ.addCylinder(*front, *(rear-front), .18)))
        for x in [-1.4, 1.0]:
            inner = np.array([x, 0, 0]) + radial*1.45
            elbow = np.array([x, 0, 0]) + radial*1.95
            loops.append((3, occ.addCylinder(*inner, *(elbow-inner), .18)))
            loops.append((3, occ.addSphere(*elbow, .18)))
    united, _ = occ.fuse([outer[0]], outer[1:] + loops)
    core = [(3, occ.addCone(-3.0, 0, 0, 1.5, 0, 0, .4, .85)),
            (3, occ.addCylinder(-1.5, 0, 0, 2.5, 0, 0, .85)),
            (3, occ.addCone(1.0, 0, 0, 2.0, 0, 0, .85, .4))]
    core_union, _ = occ.fuse([core[0]], core[1:])
    cavity, _ = occ.cut(united, core_union)
    vanes = []
    for i in range(12):
        vane = occ.addBox(-.75, .70, -.065, .70, 1.1, .13)
        occ.rotate([(3, vane)], 0, 0, 0, 1, 0, 0, i*math.pi/6)
        vanes.append((3, vane))
    occ.cut(cavity, vanes)
    occ.synchronize()
    assert len(gmsh.model.getEntities(3)) == 1, 'Cavity must be one connected solid'
    cad_volume = sum(occ.getMass(dim, tag) for dim, tag in gmsh.model.getEntities(3))
    gmsh.option.setNumber('Mesh.MeshSizeMin', .075)
    gmsh.option.setNumber('Mesh.MeshSizeMax', .21)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 16)
    gmsh.model.mesh.generate(2)
    surface_path = ROOT / 'meshes/engine-cavity.stl'
    gmsh.write(str(surface_path))
    surface_triangles = validate_surface(surface_path)

    gmsh.clear()
    gmsh.model.add('engine-cavity-volume')
    gmsh.merge(str(surface_path))
    # Preserve the validated imported surface facets while filling its interior.
    gmsh.option.setNumber('Mesh.MeshOnlyEmpty', 1)
    surfaces = [tag for _, tag in gmsh.model.getEntities(2)]
    shell = gmsh.model.geo.addSurfaceLoop(surfaces)
    volume = gmsh.model.geo.addVolume([shell])
    gmsh.model.geo.synchronize()
    gmsh.model.addPhysicalGroup(3, [volume], name='interior')
    gmsh.model.addPhysicalGroup(2, surfaces, name='boundary')
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize('Netgen')
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    xyz = np.asarray(xyz).reshape(-1, 3)
    lookup = {int(t): i for i, t in enumerate(tags)}
    types, element_tags, nodes = gmsh.model.mesh.getElements(3)
    assert list(types) == [4]
    tets = np.array([[lookup[int(n)] for n in row] for row in nodes[0].reshape(-1, 4)])
    volumes = np.abs(np.linalg.det(xyz[tets[:, 1:]] - xyz[tets[:, :1]])) / 6
    faces = Counter(tuple(sorted(t[i] for i in f)) for t in tets
                    for f in [(0,1,2), (0,1,3), (0,2,3), (1,2,3)])
    boundary = [f for f,n in faces.items() if n == 1]
    edges = Counter(tuple(sorted((f[i], f[(i+1)%3]))) for f in boundary for i in range(3))
    neighbors = {}
    for u,v in edges:
        neighbors.setdefault(u,set()).add(v)
        neighbors.setdefault(v,set()).add(u)
    visited, stack = set(), [next(iter(neighbors))]
    while stack:
        v = stack.pop()
        if v not in visited:
            visited.add(v)
            stack.extend(neighbors[v]-visited)
    quality = np.asarray(gmsh.model.mesh.getElementQualities(element_tags[0], 'minSICN'))
    assert len(visited) == len(neighbors), 'Disconnected volume boundary'
    assert all(n == 2 for n in edges.values()), 'Non-watertight volume boundary'
    assert max(faces.values()) == 2, 'Non-manifold volume faces'
    assert volumes.min() > 0 and quality.min() > .1, 'Degenerate or poor-quality element'
    error = abs(volumes.sum()/cad_volume-1)
    assert error < .03, 'Excessive geometric volume error'
    gmsh.write(str(ROOT / 'meshes/engine-cavity.msh'))
    report = {'generator': f'Gmsh {gmsh.__version__}', 'unit': 'µm', 'source': 'Original Terreaux conceptual annular engine cavity; GPL-2.0-only',
              'surfaceToVolume': 'Watertight STL import → preserve boundary facets → surface loop → tetrahedralize interior',
              'statorVanes': 12, 'bypassPassages': 6,
              'inputSurfaceWatertight': True, 'inputSurfaceTriangles': surface_triangles,
              'nodes': len(xyz), 'tetrahedra': len(tets), 'boundaryTriangles': len(boundary),
              'connectedBoundary': True, 'watertight': True, 'nonManifoldFaces': 0,
              'minimumTetVolumeUm3': float(volumes.min()), 'volumeUm3': float(volumes.sum()),
              'CADVolumeUm3': cad_volume, 'volumeRelativeError': float(error),
              'minSICN': float(quality.min()), 'medianSICN': float(np.median(quality)),
              'boundsUm': [xyz.min(axis=0).tolist(), xyz.max(axis=0).tolist()]}
    (ROOT / 'meshes/engine-quality.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    gmsh.finalize()


if __name__ == '__main__':
    build()
