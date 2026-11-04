"""Deterministically render recorded STEPS data and encode a 10 s website video.

Uses the same local WebGL renderer as interactive playback. Time samples are
held, never interpolated; the camera moves smoothly between recorded samples.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def export(url, duration, fps, width, height):
    out = ROOT/'media'
    out.mkdir(exist_ok=True)
    qc = Path(tempfile.mkdtemp(prefix='terreaux-orbit-qc-'))
    frames = round(duration*fps)
    mp4 = out/'engine-activator-orbit.mp4'
    webm = out/'engine-activator-orbit.webm'
    poster = out/'engine-activator-orbit-poster.jpg'
    ffmpeg_log = qc/'ffmpeg.log'
    command = ['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','image2pipe','-vcodec','png',
               '-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','medium',
               '-crf','20','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)]
    samples = []
    with ffmpeg_log.open('wb') as log, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
        page.set_default_timeout(90000)
        errors = []
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(url.rstrip('/')+'/?capture=1',wait_until='networkidle')
        page.wait_for_function('window.terreauxCapture !== undefined',timeout=60000)
        metadata = page.evaluate('window.terreauxCapture.metadata()')
        encoder = subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for i in range(frames):
                state = page.evaluate('(u)=>window.terreauxCapture.render(u)',i/(frames-1))
                png = page.screenshot(type='png',animations='disabled')
                encoder.stdin.write(png)
                if i in [0,frames//4,frames//2,3*frames//4,frames-1]:
                    path = qc/f'{i:04d}.png';path.write_bytes(png)
                    samples.append({'videoFrame':i,**state,'image':str(path)})
                if i == round(frames*.08):
                    page.screenshot(path=str(poster),type='jpeg',quality=94)
                if i%fps == 0:
                    print(f'Rendered {i}/{frames} frames',flush=True)
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError(ffmpeg_log.read_text())
            if errors:
                raise RuntimeError(str(errors))
        finally:
            browser.close()
            if encoder.poll() is None:
                encoder.terminate()
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',str(mp4),'-an',
                    '-c:v','libvpx-vp9','-b:v','0','-crf','31','-threads','2','-row-mt','1','-pix_fmt','yuv420p',str(webm)],check=True)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(mp4)]))
    stream = probe['streams'][0]
    assert stream['width']==width and stream['height']==height
    assert int(stream['nb_frames'])==frames
    assert abs(float(probe['format']['duration'])-duration)<.001
    report = {'durationSeconds':duration,'fps':fps,'frames':frames,'width':width,'height':height,
              'source':'engine/manifest.json and per-tetrahedron X.f32 recording',
              'sourceManifestSHA256':hashlib.sha256((ROOT/'engine/manifest.json').read_bytes()).hexdigest(),
              'renderMetadata':metadata,'simulationTimeRange':[metadata['times'][0],metadata['times'][-1]],
              'timeSampling':'Hold the preceding recorded state; no concentration interpolation',
              'camera':'One 360-degree orbit with gentle pitch variation',
              'label':'Idealized sealed microscopic engine cavity; no flow or combustion',
              'colorMapping':'Fixed global 99.5th-percentile log range; rare peaks saturate at labeled ≥ threshold',
              'context':'Gray core and stator vanes are solid context, not concentrations',
              'audio':False,'browserErrors':[],'inspectionFrames':[{k:v for k,v in s.items() if k!='image'} for s in samples],
              'files':{f.name:{'bytes':f.stat().st_size,'SHA256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in [mp4,webm,poster]}}
    (out/'orbit-export.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['renderMetadata','inspectionFrames']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8766')
    parser.add_argument('--duration',type=float,default=10)
    parser.add_argument('--fps',type=int,default=30)
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=720)
    args=parser.parse_args()
    export(args.url,args.duration,args.fps,args.width,args.height)
