"""Create an original closed surface, then tetrahedralize its interior with Gmsh.

Coordinates are micrometers. This is a synthetic geometry, not a biological cell.
The surface is generated from two spherical chambers joined by a narrow neck.
"""
from collections import Counter
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_surface(path):
    # Gmsh's ASCII STL repeats coordinates for adjacent facets.
    vertices = [tuple(map(float, line.split()[1:])) for line in path.read_text().splitlines()
                if line.strip().startswith('vertex ')]
    assert len(vertices) % 3 == 0
    triangles = [vertices[i:i+3] for i in range(0, len(vertices), 3)]
    assert all(len(set(t)) == 3 for t in triangles), 'Degenerate surface facet'
    edges = Counter(tuple(sorted((t[i], t[(i+1)%3]))) for t in triangles for i in range(3))
    assert all(n == 2 for n in edges.values()), 'Input surface is not watertight'
    return len(triangles)


def build():
    import gmsh
    import numpy as np

    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.add('twin-chambers-surface')
    occ = gmsh.model.occ
    a = occ.addSphere(-1.8, 0, 0, 1.4)
    b = occ.addSphere(1.8, 0, 0, 1.4)
    neck = occ.addCylinder(-1.8, 0, 0, 3.6, 0, 0, .6)
    occ.fuse([(3, a)], [(3, b), (3, neck)])
    occ.synchronize()
    analytic_volume = sum(occ.getMass(dim, tag) for dim, tag in gmsh.model.getEntities(3))
    gmsh.option.setNumber('Mesh.MeshSizeMin', .16)
    gmsh.option.setNumber('Mesh.MeshSizeMax', .24)
    gmsh.model.mesh.generate(2)
    gmsh.write(str(ROOT / 'meshes/twin-chambers.stl'))
    surface_triangles = validate_surface(ROOT / 'meshes/twin-chambers.stl')

    # Deliberately start again from the closed surface, not the CAD solid.
    gmsh.clear()
    gmsh.model.add('twin-chambers-volume')
    gmsh.merge(str(ROOT / 'meshes/twin-chambers.stl'))
    gmsh.model.mesh.classifySurfaces(math.radians(40), True, True, math.pi)
    gmsh.model.mesh.createGeometry()
    surfaces = [tag for _, tag in gmsh.model.getEntities(2)]
    shell = gmsh.model.geo.addSurfaceLoop(surfaces)
    volume = gmsh.model.geo.addVolume([shell])
    gmsh.model.geo.synchronize()
    gmsh.model.addPhysicalGroup(3, [volume], name='cytosol')
    gmsh.model.addPhysicalGroup(2, surfaces, name='boundary')
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize('Netgen')
    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    xyz = np.asarray(coordinates).reshape(-1, 3)
    lookup = {int(tag): i for i, tag in enumerate(tags)}
    types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
    assert list(types) == [4], 'Only linear tetrahedra are supported'
    tets = np.array([[lookup[int(n)] for n in row] for row in element_nodes[0].reshape(-1, 4)])
    volumes = np.abs(np.linalg.det(xyz[tets[:, 1:]] - xyz[tets[:, :1]])) / 6
    face_counts = Counter(tuple(sorted(t[i] for i in face)) for t in tets
                          for face in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)])
    boundary = [f for f, count in face_counts.items() if count == 1]
    edges = Counter(tuple(sorted((f[i], f[(i+1) % 3]))) for f in boundary for i in range(3))
    quality = np.asarray(gmsh.model.mesh.getElementQualities(element_tags[0], 'minSICN'))
    # The edge graph must form one connected, closed manifold surface.
    neighbors = {}
    for u, v in edges:
        neighbors.setdefault(u, set()).add(v)
        neighbors.setdefault(v, set()).add(u)
    visited, stack = set(), [next(iter(neighbors))]
    while stack:
        v = stack.pop()
        if v not in visited:
            visited.add(v)
            stack.extend(neighbors[v] - visited)
    assert len(visited) == len(neighbors), 'Disconnected boundary'
    assert all(n == 2 for n in edges.values()), 'Non-watertight boundary'
    assert max(face_counts.values()) == 2, 'Non-manifold tetrahedral mesh'
    assert volumes.min() > 0 and quality.min() > .1, 'Degenerate/poor-quality tetrahedra'
    assert abs(volumes.sum()/analytic_volume - 1) < .03, 'Excessive geometry approximation error'
    gmsh.write(str(ROOT / 'meshes/twin-chambers.msh'))
    report = {'generator': f'Gmsh {gmsh.__version__}', 'unit': 'µm', 'source': 'Original Terreaux synthetic geometry; GPL-2.0-only',
              'surfaceToVolume': 'STL import → classify → discrete geometry → surface loop → tetrahedralize',
              'inputSurfaceWatertight': True, 'inputSurfaceTriangles': surface_triangles,
              'nodes': len(xyz), 'tetrahedra': len(tets), 'boundaryTriangles': len(boundary),
              'connectedBoundary': True, 'watertight': True, 'nonManifoldFaces': 0,
              'minimumTetVolumeUm3': float(volumes.min()), 'volumeUm3': float(volumes.sum()),
              'CADVolumeUm3': analytic_volume, 'volumeRelativeError': float(abs(volumes.sum()/analytic_volume-1)),
              'minSICN': float(quality.min()), 'medianSICN': float(np.median(quality)),
              'boundsUm': [xyz.min(axis=0).tolist(), xyz.max(axis=0).tolist()]}
    (ROOT / 'meshes/quality.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    gmsh.finalize()


if __name__ == '__main__':
    build()
