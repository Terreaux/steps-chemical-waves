"""Adapted from CNS-OIST's GPL-2.0 spatial Brusselator example.

Run a serial stochastic STEPS Tetexact simulation in the validated custom volume.
No simulated chemistry is replaced by a procedural visual effect.
"""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import steps
import steps.interface
from steps.model import Model, ReactionManager, Species, VolumeSystem, Diffusion
from steps.geom import TetMesh, Compartment
from steps.rng import RNG
from steps.sim import Simulation
from steps.saving import ResultSelector

ROOT = Path(__file__).resolve().parents[1]


def simulate(preset='volume'):
    engine = preset == 'engine'
    mdl = Model()
    r = ReactionManager()
    with mdl:
        X, Y = Species.Create()
        vsys = VolumeSystem.Create()
        with vsys:
            None <r[1]> X >r[2]> Y
            r[1].K = .3 * 10 / 5e4, 10
            r[2].K = 3 * 10
            2*X + Y >r[3]> 3*X
            r[3].K = 10 * 5e4**2
            Diffusion(X, 1e-13)
            Diffusion(Y, 1e-13)
    # This is a microscopic synthetic reactor, not full-scale engine chemistry.
    mesh_path = ROOT / ('meshes/engine-cavity.msh' if engine else 'meshes/twin-chambers.msh')
    mesh = TetMesh.LoadGmsh(str(mesh_path), scale=5e-7)
    with mesh:
        comp = Compartment.Create(mesh.tets, vsys)
    sim = Simulation('Tetexact', mdl, mesh, RNG('mt19937', 512, 1234))
    rs = ResultSelector(sim)
    concentrations = rs.TETS(mesh.tets).LIST(X, Y).Conc
    sim.toSave(concentrations, dt=.04 if engine else .02)
    sim.newRun()
    sim.comp.X.Conc = 5e-6
    sim.comp.Y.Conc = 1.4e-4
    # An explicitly documented initial stimulus, followed by unforced evolution.
    stimulus_threshold = -1.05e-6 if engine else -1.2e-6
    stimulated = [tet for tet in mesh.tets if tet.center.x < stimulus_threshold]
    for tet in stimulated:
        sim.TET(tet).X.Conc = 5e-5
    begin = time.perf_counter()
    sim.run(4.0 if engine else 3.0)
    elapsed = time.perf_counter()-begin
    out = ROOT / preset
    out.mkdir(exist_ok=True)
    values = np.asarray(concentrations.data[0]).reshape(-1, len(mesh.tets), 2) * 1e6
    times = np.asarray(concentrations.time[0]).tolist()
    positions, centers, face_cells, tet_volumes = [], [], [], []
    all_centers = np.array([[t.center.x, t.center.y, t.center.z] for t in mesh.tets]) * 1e6
    lo, hi = all_centers[:, 0].min(), all_centers[:, 0].max()
    for i, tet in enumerate(mesh.tets):
        vertices = [[v.x*1e6, v.y*1e6, v.z*1e6] for v in tet.verts]
        vertices_array = np.asarray(vertices)
        tet_volumes.append(abs(np.linalg.det(vertices_array[1:]-vertices_array[0]))/6)
        for face in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]:
            positions.extend(vertices[j] for j in face)
            centers.extend([(all_centers[i,0]-lo)/(hi-lo)]*3)
            face_cells.append(i)
    def write(name, a):
        np.asarray(a, dtype='<f4').tofile(out / name)
    write('positions.f32', positions)
    write('centers.f32', centers)
    write('face-cells.f32', face_cells)
    for j, species in enumerate(['X', 'Y']):
        write(f'{species}.f32', values[:,:,j])
    weights = np.asarray(tet_volumes)
    regions = {'left': all_centers[:,0] < -.5, 'right': all_centers[:,0] > .5}
    traces = {species: {name: np.average(values[:,mask,j], axis=1, weights=weights[mask]).tolist()
                       for name,mask in regions.items()} for j,species in enumerate(['X','Y'])}
    meta = {'volume': True, 'label': f'TWIN CHAMBERS / {len(mesh.tets):,} VOLUME TETRAHEDRA', 'radius': 2.2,
            'description': 'Original twin-chamber volume; serial STEPS Tetexact run, seed 1234. An initial X stimulus in the left chamber is followed by unforced reaction–diffusion. Cutaway removes whole tetrahedra, not an interpolated plane. Fixed color range across every frame; no time interpolation. This mesh has passed geometry checks; scientific mesh convergence remains untested.',
            'solver': 'Tetexact', 'stepsVersion': steps.__version__, 'seed': 1234, 'elapsedSeconds': elapsed,
            'faces': len(face_cells), 'cells': len(mesh.tets), 'times': times,
            'positionUnit': 'µm', 'concentrationUnit': 'µM', 'meshScaleMeters': 5e-7,
            'meshSHA256': hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            'traces': traces, 'regionDefinitionUm': {'left': 'tet center x < -0.5', 'right': 'tet center x > 0.5'},
            'initialStimulus': {'xLessThanMeters': stimulus_threshold, 'XConcM': 5e-5, 'tetrahedra': len(stimulated)},
            'species': {s: {'min': float(values[:,:,i].min()), 'max': float(values[:,:,i].max())} for i,s in enumerate(['X','Y'])}}
    if engine:
        for i,species in enumerate(['X','Y']):
            meta['species'][species]['displayP995'] = float(np.quantile(values[:,:,i].astype('<f4'), .995))
        meta.update({'label': f'ANNULAR ENGINE CAVITY / {len(mesh.tets):,} VOLUME TETRAHEDRA', 'radius': 1.85,
                     'defaultCutAxis': 'z', 'defaultCut': .57, 'defaultFrame': 10,
                     'defaultSpeed': '1',
                     'defaultMapping': 'robust',
                     'description': 'Original conceptual engine cavity with a tapered core, 12 stator vanes and six connected bypass passages. STEPS Tetexact evolves an idealized Brusselator in a sealed microscopic volume (2.8 µm long); seed 1234, initial X stimulus at the front. This is reaction–diffusion only: no airflow, combustion, heat transfer or engine-performance prediction. The cutaway removes whole tetrahedra. Mesh/time convergence remains untested.',
                     'traceTitle': 'Chemistry through a complex interior.',
                     'traceLabels': {'left': 'Front region', 'right': 'Rear region'},
                     'regionNote': 'Volume-weighted cells with center x < −0.5 µm (front) or x > 0.5 µm (rear). Initial X stimulus at x < −1.05 µm. A sealed microscale demonstration: no flow or combustion.',
                     'modelNote': 'A synthetic chemical oscillator in a sealed engine-shaped microcavity. The tapered core and stator vanes are solid exclusions; chemistry occupies the surrounding annulus and six bypass passages. No airflow or combustion is simulated.',
                     'regionDefinitionUm': {'left': 'tet center x < -0.5 (front)', 'right': 'tet center x > 0.5 (rear)'},
                     'meshScaleExplanation': 'Source CAD units scaled by 5e-7 m. This is a micron-scale demonstration, not an actual engine-size diffusion time.'})
    (out / 'manifest.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(json.dumps({k:v for k,v in meta.items() if k!='times'},indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--preset', choices=['volume', 'engine'], default='volume')
    simulate(parser.parse_args().preset)
