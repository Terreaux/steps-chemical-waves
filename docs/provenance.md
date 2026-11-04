# Provenance and scientific scope

## Official baseline

Source: [CNS-OIST/STEPS_Example](https://github.com/CNS-OIST/STEPS_Example),
revision `23d8e941fcdd3e8d64e0764233b81746671600ab`.
The upstream repository declares GNU GPL version 2. The full license is retained
in this repository's `LICENSE`; this project is distributed as GPL-2.0-only.
No separate conflicting license was present in the reused files.

Unmodified upstream files:

- `upstream/STEPS_Tutorial_DataSaving_square.py`, originally
  `user_manual/source/API_2/scripts/STEPS_Tutorial_DataSaving_square.py`.
- `meshes/square_9k.msh`, originally `user_manual/source/API_2/meshes/square_9k.msh`.
- `upstream/square.vtkjs`, originally
  `user_manual/source/data/square_A0.3_B3_D1e-13_Run_0.vtkjs`.

The recording SHA-256 is
`08667e056a8775305630824995f46d5d7bdb6649c1aa464d896806112f38bb0a`.
The published recording is associated with the upstream tutorial, rather than a
run made by Terreaux. Its exact STEPS binary/build environment is not recorded in
the VTK archive. The accompanying script specifies the Tetexact stochastic
solver, seed 1234, A = 0.3, B = 3, diffusion = 10⁻¹³ m²/s for both species,
initial X = 5 µM, Y = 140 µM, and a 0.01 s recording interval through 1.5 s.

The archive contains a **surface extraction** of the tetrahedral slab, with
6,652 triangular surface cells and 3,328 points. Each triangle retains its
original cell concentration. Conversion preserves face order and every saved
time. It converts meters to micrometers and molar concentrations to µM, then
stores float32 arrays for the browser. Rounding is the only numeric compression.
No spatial smoothing or time interpolation is performed. Surface triangles can
share the same parent tetrahedron, so their unweighted average is not a valid
whole-volume concentration.

## Custom volume

The twin-chamber geometry is an original synthetic Terreaux geometry released
under GPL-2.0-only. It depicts no particular organism. It starts as two spheres
connected by a cylinder; their union is exported to a closed STL surface. A new
Gmsh model imports that surface and tetrahedralizes its interior. There is no
third-party surface asset or external mesh attribution requirement.

`meshes/quality.json` records connectivity, watertightness, face incidence,
positive tetrahedron volumes, Gmsh's minSICN quality metric and geometric volume
error. These establish an initial usable mesh, not spatial convergence of the
reaction–diffusion solution. The thin neck requires particular attention in a
future resolution study.

Mesh coordinates are in µm. The custom simulation uses a scale of 5 × 10⁻⁷ m per
mesh coordinate, making the physical shape half the source dimensions. The
viewer exports the actual physical dimensions in µm. The manifest records the
mesh hash, solver version, seed, physical scale and initial stimulus.

The volume model adapts the official reduced Brusselator reaction network and
rate constants. X is initially raised to 50 µM where x < −1.2 µm; elsewhere it is
5 µM. Y begins at 140 µM. After initialization the model evolves without further
forcing. A single trajectory illustrates the model; it is not statistical
evidence of a biological phenomenon or a validated prediction.

The cutaway discards whole tetrahedra by their center coordinate on a selected axis and draws
the remaining tetrahedron faces. Its boundary is a discrete, stepped selection,
not a geometrically interpolated section. Concentrations remain per-tetrahedron
values, with fixed per-species color limits across the complete recording.

Color mapping can be linear or logarithmic. The logarithmic mapping, enabled
initially to reveal low-concentration structure, is
`log(1 + c / 1 µM) / log(1 + c_max / 1 µM)`. The legend labels this transform;
the stored concentrations and plotted regional means remain in µM. Color limits
remain fixed across time and cutaway positions in both mappings. Color is
constant within each tetrahedron. Optional depth shading changes display
brightness and can be disabled; it does not change scalar data or plotted means.

The additional engine-interior preset has its own geometry, recording and
[scientific-scope documentation](engine.md). The twin-chamber and slab assets
remain unchanged.

## Model and limitations

The reduced system is ∅ ⇌ X → Y and 2X + Y → 3X. Reservoir species A and B are
implicit and held fixed; omitted products do not react further. This is an open
chemical system: total X + Y is not expected to be conserved. The tutorial's
scaling factors are TF = 10 and CF = 50,000. Consult the source scripts for
dimensional stochastic rate constants rather than treating A and B as molarity.

Browser playback is not a live STEPS solver. Changing camera, species, time or
cutaway does not rerun chemistry. Parameter sweeps and mesh/seed convergence
studies remain future work. The showcase demonstrates a reproducible geometry,
simulation and visualization pipeline, not scientific validation of new physics.

References: [official tutorial](https://steps.sourceforge.net/manual/API_2/STEPS_Tutorial_DataSaving.html),
[STEPS source](https://github.com/CNS-OIST/STEPS).
