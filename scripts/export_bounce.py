"""Replay the actual ten-second orbit forward and backward, with direction labels."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]


def export(field='cells'):
    media=ROOT/'media'
    smooth=field=='smooth'
    stem='engine-activator-smooth' if smooth else 'engine-activator'
    source=media/f'{stem}-orbit.mp4'
    forward=json.loads((media/('smooth-orbit-export.json' if smooth else 'orbit-export.json')).read_text())
    assert forward['durationSeconds']==10 and forward['simulationTimeRange']==[0,10]
    mp4=media/f'{stem}-bounce.mp4'
    webm=media/f'{stem}-bounce.webm'
    labels=Path(tempfile.mkdtemp(prefix='terreaux-bounce-labels-'))
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',13)
    for name,text in [('forward','FORWARD PLAYBACK'),('reverse','REVERSE PLAYBACK')]:
        image=Image.new('RGBA',(1280,720),(0,0,0,0))
        ImageDraw.Draw(image).text((1242,30),text,font=font,fill=(197,218,208,255),anchor='rt')
        image.save(labels/f'{name}.png')
    graph=('[0:v]split=2[a][b];[a]setpts=PTS-STARTPTS[f0];'
           '[f0][1:v]overlay=0:0:eof_action=repeat[f];'
           '[b]reverse,setpts=PTS-STARTPTS[r0];[r0][2:v]overlay=0:0:eof_action=repeat[r];'
           '[f][r]concat=n=2:v=1:a=0[out]')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y','-threads','2','-i',str(source),
                    '-i',str(labels/'forward.png'),'-i',str(labels/'reverse.png'),
                    '-filter_complex_threads','1','-filter_complex',graph,'-map','[out]','-an',
                    '-c:v','libx264','-threads','2','-preset','medium','-crf','18','-pix_fmt','yuv420p',
                    '-movflags','+faststart',str(mp4)],check=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',str(mp4),'-an',
                    '-c:v','libvpx-vp9','-b:v','0','-crf','31','-threads','2','-row-mt','1',
                    '-pix_fmt','yuv420p',str(webm)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(mp4)]))
    assert int(info['streams'][0]['nb_frames'])==600
    assert abs(float(info['format']['duration'])-20)<.001
    report={'durationSeconds':20,'fps':30,'frames':600,'width':1280,'height':720,
            'simulationDurationSeconds':10,'simulationSaveIntervalSeconds':.04,'simulationSavedStates':251,
            'forwardVideoSeconds':[0,10],'reverseVideoSeconds':[10,20],
            'camera':'One full rotation forward, followed by the same rotation backward',
            'playback':'Forward frames 0…299 then 299…0. A repeated endpoint frame at each turnaround.',
            'scientificScope':'Reverse is video playback of saved states, never reversed solver dynamics.',
            'directionLabels':['FORWARD PLAYBACK','REVERSE PLAYBACK'],
            'sourceVideoSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'files':{f.name:{'bytes':f.stat().st_size,'SHA256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in [mp4,webm]}}
    report['fieldRepresentation']='Volume-weighted nodal recovery and linear surface interpolation' if smooth else 'Recorded cell values'
    (media/('smooth-bounce-export.json' if smooth else 'bounce-export.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--field',choices=['cells','smooth'],default='cells')
    export(parser.parse_args().field)
