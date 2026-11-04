# Engine interior: geometry and scientific scope

The third preset is an original **conceptual annular engine cavity**, with a
tapered central core, twelve stationary radial vanes and six connected bypass
passages. It is a recognizable engineering interior rather than a model of a
specific manufacturer's engine. The core and vanes are solid exclusions: STEPS
occupies the surrounding cavity and the bypass passages, not the metal.

The twin-chamber preset and official slab remain available, with their recorded
assets unchanged. The engine is a separate recording in `engine/`.

## Surface → interior volume

`scripts/build_engine.py` constructs the conceptual cavity with OpenCASCADE
primitives in Gmsh. It exports a closed triangular STL, checks that every input
surface edge has exactly two incident triangles, clears the CAD model, and
imports only that surface into a fresh model. It creates a surface loop and
tetrahedralizes the enclosed region while preserving the imported boundary
facets. The solver mesh therefore comes from the closed surface, not from the
original CAD solid.

The first fine remeshing approach generated 179,029 tetrahedra. Preserving the
validated surface facets produces 55,473 tetrahedra with the same geometry
features and a more practical playback footprint. Both input and output are
closed; the output boundary is connected, tetrahedron volumes are positive,
and no volume face has more than two incident tetrahedra. Gmsh's minimum
minSICN score is 0.1305; median is 0.8511. The polyhedral volume differs from
the CAD volume by about 0.0585%. Exact measurements are in
`meshes/engine-quality.json`.

These are mesh-engineering checks, not a reaction–diffusion convergence study.
The thin junctions and vanes create very small cells; the applicability of
the voxel reaction model and its dependence on mesh resolution need separate
scientific investigation. No accuracy claim is inferred from element count.

## What the chemistry represents

This is a **sealed, microscopic engine-shaped reactor** containing the same
idealized Brusselator chemistry as the baseline. It demonstrates how molecular
reaction–diffusion can be simulated and inspected inside a complex volume.
There is no imposed flow, combustion, turbulence, temperature field, heat
transfer, thrust or engine-performance calculation. It is not an engineering
prediction about a real jet engine.

The source mesh coordinates are scaled by 5 × 10⁻⁷ meters, making the simulated
domain 2.8 µm long. This scale keeps molecule counts and stochastic runtime
practical; the viewer reports actual simulation coordinates. Extending the
same diffusion-only model to a meter-scale engine would give completely
different time scales and is not claimed here.

STEPS 5.1.0's serial `Tetexact` solver uses seed 1234, the official tutorial's
reaction constants, and diffusion coefficient 10⁻¹³ m²/s for both species.
Initial X is 5 µM, raised to 50 µM where x < −1.05 µm, and initial Y is 140 µM.
The system then evolves without forcing. It records 251 states over 10 seconds,
at 0.04-second intervals. Regional plots are volume-weighted means for cells
with center x < −0.5 µm (front) or x > 0.5 µm (rear); they do not describe flow.

## Visualization

The camera offers three-quarter, axial and interior views. A section can remove
tetrahedra along x, y or z. This is a cell-based cutaway, not a smooth geometric
intersection, and all revealed colors come from the recorded tetrahedra. Fixed
per-species color limits and optional logarithmic mapping apply across time.
Optional depth shading changes only display brightness and can be disabled for
the unshaded color transfer function. Regional curves always show untransformed
concentrations in µM.

The default engine color range uses the global 99.5th percentile for each
species, computed over all recorded cells and times. Values above that limit
share the top color; both the mapping selector and the `≥` legend mark this
clipping. Very small cells can give high concentration for a single molecule,
so a few extreme values otherwise obscure the bulk of the field. Choose
"Logarithmic · full range" or linear mapping to use the actual recorded maximum.
No stored values or regional measurements are clipped.

The optional gray core and vanes show the original solid CAD exclusions as
context. They are not assigned chemical concentrations or included in regional
measurements. Hiding this overlay leaves the recorded fluid-cavity field alone.

The viewer is recorded playback; camera and section controls do not solve or
alter chemistry. Mesh/time convergence, ensembles and cross-solver comparisons
remain future work.

## License and reproduction

All engine geometry and generator code are original Terreaux work, released
under **GPL-2.0-only**. No external CAD or mesh asset is bundled, so there is no
manufacturer ownership claim or third-party asset license to infer. The
reaction model retains its attribution to the GPL-2.0 CNS-OIST example in
[provenance.md](provenance.md).

```sh
.venv/bin/python scripts/build_engine.py
.venv/bin/python scripts/simulate_volume.py --preset engine --duration 10
```

The mesh, script and data checksums and runtime are inspectable in the quality
report and recording manifest. Meshing uses Gmsh 4.15.2; the installed dependencies
remain pinned in `requirements.txt`.
