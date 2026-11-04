# Smooth surface-field rendering — local iteration

The smooth view uses the same 10-second STEPS trajectory, seed 1234, 55,473
tetrahedra and 251 recorded states as the original videos. The earlier videos
remain separate, unchanged files. The reconstruction is generated in
`engine-smooth/`; the new videos use the `engine-activator-smooth-` prefix.

## Concentration reconstruction

For a mesh node v, let I(v) be its incident tetrahedra, Vᵢ their physical volumes,
and cᵢ(t) the recorded cell concentrations in µM. The display value is

`c_v(t) = Σᵢ∈I(v) Vᵢ cᵢ(t) / Σᵢ∈I(v) Vᵢ`.

The weights are positive and normalized. This preserves constant fields and
keeps each recovered value within the incident cells' concentration range.
The original float32 physical vertex coordinates are used to compute volumes.
The recovery is computed on the complete mesh before applying the cutaway, so
changing the view does not redefine the recovered physical field.

For every visible surface triangle, WebGL linearly interpolates the recovered
**scalar concentrations** between its three nodes, then applies the existing
logarithmic concentration-to-color transfer function. Color itself is not
interpolated as a substitute for concentration. Shared nodes have identical
values, giving a continuous piecewise-linear surface field across triangle
boundaries. Gradients can still vary between triangles.

No temporal interpolation is used. Each video frame holds an actual saved
0.04-second state. The ten-second forward camera orbit and twenty-second bounce
timing are unchanged; the return half is explicitly labeled reverse playback.

## Surface selection and shading

The renderer selects whole tetrahedra by their centers, matching the existing
cutaway. It draws a face only when exactly one of its incident tetrahedra is
selected. Internal faces between two selected cells are omitted. Triangle edges
are disabled in this mode.

Area-weighted normals are accumulated at shared exposed-surface nodes and
interpolated for smooth display lighting. Vertex positions and the solver mesh
are unchanged. The cutaway silhouette still follows the original discrete
tetrahedra; it is not a remeshed geometric section. The gray hardware context is
recessed by 0.005 µm (5 nm) to avoid depth fighting with adjacent field surfaces;
this offset applies only to the gray display geometry.

The fixed color limits and labeled rare-peak saturation are retained from the
original cell-value videos, allowing a consistent visual comparison. The video
labels the interpolated surface field and its reconstruction method.

## Interpretation and checks

This recovery is for visualization. It changes displayed local extrema and is
not a conservative replacement for the cell data. Quantitative totals, regional
means and any scientific analysis must continue to use the original records.
The original microcavity's reaction–diffusion scope and lack of flow/combustion
modeling remain unchanged.

Checks cover source-file hashes, 0–10-second sampling, an independent comparison
of recovered values against weighted incident-cell records, concentration
bounds, constant-field preservation and mesh-face adjacency. Separate video
checks cover decoding, browser play/seek, and forward/reverse frame symmetry.

## Reproduce locally

```sh
.venv/bin/python scripts/reconstruct_surface.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/export_orbit.py --field smooth
.venv/bin/python scripts/export_bounce.py --field smooth
.venv/bin/python tests/video_playback.py --field smooth
.venv/bin/python tests/bounce_symmetry.py --field smooth
```

Capture and playback checks use scoped temporary localhost servers and close
them afterward. They do not restart the stopped port-8766 session service.
For interactive inspection on a manually started server, open
`/?capture=1&field=smooth` or choose **Smooth reconstruction** in the engine view.
