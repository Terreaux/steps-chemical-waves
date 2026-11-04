# Smooth activator surface

The new files are separate from all earlier videos:

- `engine-activator-smooth-orbit.mp4` / `.webm`: 10-second forward orbit.
- `engine-activator-smooth-bounce.mp4` / `.webm`: 20-second forward/reverse loop.
- `engine-activator-smooth-orbit-poster.jpg`: still preview.
- `smooth-preview.html`: local playback page.

These show a volume-weighted nodal recovery of the actual 0–10-second STEPS
trajectory, with piecewise-linear scalar interpolation across the exposed
surface. Triangle edges are hidden and lighting uses shared-node smooth normals.
The original cell values, geometric coordinates and 0.04-second time samples
remain unchanged. The original fixed concentration color range is retained.

See [the interpolation method and limits](../docs/smooth-surface.md). This is a
visual reconstruction; quantitative analysis uses the original cell data.
The reverse half is explicitly labeled playback of recorded states.

This version was prepared and validated on `leo/smooth-surface-render`.
The separate filenames preserve the earlier cell-value videos. Capture and
verification use temporary localhost servers that close afterward; repository
publication does not start the port-8766 service.
