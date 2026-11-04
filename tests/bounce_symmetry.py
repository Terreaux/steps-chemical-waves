"""Verify that the movie returns through the same recorded states and views."""
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
movie=ROOT/'media/engine-activator-bounce.mp4'
indices=[0,75,150,299,300,449,524,599]
selection='+'.join(f'eq(n,{i})' for i in indices)
filters=f"select='{selection}',crop=1280:560:0:100,scale=640:280"
raw=subprocess.check_output(['ffmpeg','-v','error','-threads','2','-i',str(movie),'-vf',filters,
                             '-fps_mode','vfr','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
images=np.frombuffer(raw,dtype=np.uint8).reshape(len(indices),280,640,3)
by_index=dict(zip(indices,images))
pairs=[]
for i in [0,75,150,299]:
    opposite=599-i
    error=float(np.abs(by_index[i].astype(float)-by_index[opposite].astype(float)).mean())
    assert error<3, f'Bounce frames {i}/{opposite} differ beyond codec tolerance: {error}'
    pairs.append({'forwardFrame':i,'reverseFrame':opposite,'meanAbsoluteRGBError':error})
report={'criterion':'Same data/view at mirrored frame indices; exclude direction labels and allow lossy-codec error',
        'maximumAllowedMeanRGBError':3,'pairs':pairs,'result':'passed'}
(ROOT/'media/bounce-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
