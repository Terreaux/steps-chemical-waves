# First vertical slice

The first question is whether a visitor can see the spatial structure of a real
reaction–diffusion recording, then inspect how it changes over time.

Use the official STEPS spatial Brusselator slab and its published recording as
the baseline. Preserve every recorded frame and surface face. Show concentrations
in µM with one fixed color range per species across the entire recording. Playback
has no editable reaction parameters: changing them requires another solver run.

The viewer has time scrubbing, play/pause, species selection, orbit, zoom, camera
reset, and optional mesh edges. Geometry and data load from local files without
external JavaScript dependencies or analytics. The interface exposes provenance.

A custom closed surface and its tetrahedral interior are a separate geometry
experiment. Passing a mesh-quality check does not establish that the stochastic
simulation has converged with respect to spatial resolution. Surface playback
must not be described as a volume rendering or an interior slice.
