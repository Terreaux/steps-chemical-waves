"""Validate both site-video encodings and actual browser playback."""
import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
results=[]
class VideoHandler(SimpleHTTPRequestHandler):
    # Match the byte-range behavior of a normal static website host. Python's
    # basic SimpleHTTPRequestHandler does not implement media seeking ranges.
    def do_GET(self):
        names={f'/engine-activator-orbit.{s}' for s in ['mp4','webm']}
        if self.path not in names:
            return super().do_GET()
        data=(ROOT/'media'/self.path.lstrip('/')).read_bytes()
        requested=self.headers.get('Range')
        start,end=0,len(data)-1
        if requested:
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',requested)
            if not match:
                self.send_error(416);return
            start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
            if start>end:
                self.send_error(416);return
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type','video/mp4' if self.path.endswith('.mp4') else 'video/webm')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Length',str(end-start+1))
        if requested:
            self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
        self.end_headers();self.wfile.write(data[start:end+1])

server=ThreadingHTTPServer(('127.0.0.1',0),partial(VideoHandler,directory=str(ROOT/'media')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/preview.html'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url)
    for suffix in ['mp4','webm']:
        path=ROOT/f'media/engine-activator-orbit.{suffix}'
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
        streams=probe['streams']
        assert len(streams)==1 and streams[0]['codec_type']=='video'
        assert streams[0]['width']==1280 and streams[0]['height']==720
        assert abs(float(probe['format']['duration'])-10)<.05
        assert streams[0]['pix_fmt']=='yuv420p'
        subprocess.run(['ffmpeg','-v','error','-threads','2','-i',str(path),'-f','null','-'],check=True)
        page.evaluate('(suffix)=>{const v=document.getElementById("film");v.src=`engine-activator-orbit.${suffix}`;v.load();}',suffix)
        page.wait_for_function('document.getElementById("film").readyState>=2',timeout=60000)
        assert abs(page.evaluate('document.getElementById("film").duration')-10)<.05
        page.evaluate('document.getElementById("film").play()')
        page.wait_for_function('document.getElementById("film").currentTime>.2')
        page.evaluate('document.getElementById("film").pause()')
        before=page.locator('#film').screenshot()
        page.evaluate('document.getElementById("film").currentTime=5')
        page.wait_for_function('Math.abs(document.getElementById("film").currentTime-5)<.05 && !document.getElementById("film").seeking && document.getElementById("film").readyState>=2')
        after=page.locator('#film').screenshot()
        assert before!=after,'The decoded orbit frames must change'
        results.append({'format':suffix,'codec':streams[0]['codec_name'],'duration':float(probe['format']['duration']),
                        'bytes':path.stat().st_size,'ffmpegDecode':'passed','browserPlayAndSeek':'passed',
                        'verifiedSeekSeconds':page.evaluate('document.getElementById("film").currentTime')})
        if suffix=='mp4':
            page.locator('#film').screenshot(path='/tmp/terreaux-video-decoded.png')
    assert not errors,errors
    browser.close()
server.shutdown();server.server_close()
report={'formats':results,'browser':'Chromium','pageErrors':errors,'temporaryPlaybackServer':'stopped after verification'}
(ROOT/'media/playback-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
