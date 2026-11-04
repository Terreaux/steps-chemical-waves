# Engine activator orbit

Website-ready video of the actual STEPS X-activator recording in the conceptual
engine cavity. The camera makes one 360° orbit with gentle pitch variation.

- `engine-activator-orbit.mp4`: H.264, 1280 × 720, 30 fps, 10 seconds, no audio,
  with fast-start metadata for web playback.
- `engine-activator-orbit.webm`: VP9 alternative.
- `engine-activator-orbit-poster.jpg`: still fallback/preview.
- `orbit-export.json`: source hash, encoding measurements, sampling and checksums.

The four seconds of recorded simulation are shown over ten seconds of video.
Concentrations hold at their recorded 0.04-second samples; no concentrations are
interpolated. Camera motion is sampled at 30 fps. The clip contains one finite
trajectory; looping restarts that trajectory and does not imply a perfectly
periodic chemical solution.

Colors represent X concentration in µM with a fixed logarithmic transfer
function and the labeled global 99.5th-percentile range. Rarer peaks share the
top color. Gray hardware is solid context, not chemical concentration. The
on-screen scope is retained: an idealized sealed microscopic cavity, with no
flow, combustion or engine-performance calculation.

## Embed

Copy the video and poster assets to your site's media folder, then adapt paths:

```html
<video width="1280" height="720" autoplay muted loop playsinline controls
       preload="metadata" poster="/media/engine-activator-orbit-poster.jpg"
       aria-label="Recorded X activator in an idealized sealed engine-shaped microcavity">
  <source src="/media/engine-activator-orbit.webm" type="video/webm">
  <source src="/media/engine-activator-orbit.mp4" type="video/mp4">
  <img src="/media/engine-activator-orbit-poster.jpg"
       alt="X concentration in a conceptual engine cavity, with gray solid hardware">
</video>
<script>
  const video = document.querySelector('video');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    video.autoplay = false;
    video.pause();
  }
</script>
```

Keep a way to pause the animation. The poster also works as a static alternative.
See `preview.html` for a local playback page. No website hosting is deployed by
this repository.
Use a static host with HTTP byte-range support for reliable seeking. The basic
Python development server can play the file but does not implement those ranges.

## Reproduce

Serve the repository, then run:

```sh
.venv/bin/python scripts/export_orbit.py --url http://127.0.0.1:8766 --duration 10 --fps 30
```

Requires the pinned Playwright environment, Chromium and FFmpeg with libx264 and
libvpx-vp9. Export uses the same WebGL renderer as interactive playback through
the `?capture=1` presentation mode. The capture mode is separate from ordinary
interactive viewing.

Original Terreaux geometry, visualization and video are released under
GPL-2.0-only. The chemistry adapts the CNS-OIST GPL-2.0 spatial Brusselator example;
see [provenance](../docs/provenance.md) and [engine methods](../docs/engine.md).
