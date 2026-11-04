"""Exercise the user-visible playback and WebGL output, including mobile layout."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(os.environ.get('SIMS_URL', 'http://127.0.0.1:8766/'))
    page.wait_for_function("!document.getElementById('play').disabled")
    canvas = page.locator('#scene')
    initial = canvas.screenshot()
    page.locator('#timeline').fill('70')
    preset = page.locator('#preset').input_value()
    metadata = json.loads((ROOT/preset/'manifest.json').read_text())
    assert f"{metadata['times'][70]:.2f}" in page.locator('#time').inner_text()
    after = canvas.screenshot()
    assert initial != after, 'Recorded time must change the rendered field'
    page.select_option('#mapping','linear')
    assert canvas.screenshot() != after, 'Color mapping must change transfer function'
    page.select_option('#mapping','log')
    page.select_option('#species','Y')
    assert canvas.screenshot() != after, 'Changing species must change the field'
    page.check('#edges')
    before_orbit = canvas.screenshot()
    canvas.focus();page.keyboard.press('ArrowRight')
    assert canvas.screenshot() != before_orbit, 'Orbit must change geometry projection'
    if (ROOT/'volume/manifest.json').exists():
        before_cut = canvas.screenshot()
        page.locator('#cut').fill('0.5')
        assert canvas.screenshot() != before_cut, 'Volume cutaway must expose internal cells'
        assert page.locator('#cutValue').inner_text() == '50%'
        before_axis = canvas.screenshot()
        page.select_option('#cutAxis','y')
        assert canvas.screenshot() != before_axis
        page.click('#viewInlet')
        page.click('#viewSection')
        assert page.locator('#cutAxis').input_value() == 'z'
    page.click('#play')
    frame_before = page.locator('#timeline').input_value()
    page.wait_for_timeout(250)
    assert page.locator('#timeline').input_value() != frame_before
    page.click('#play')
    if preset == 'engine':
        page.select_option('#species','X');page.select_option('#mapping','robust');page.locator('#timeline').fill('8');page.locator('#cut').fill('0.58');page.uncheck('#edges');page.click('#viewThree')
        assert '≥' in page.locator('#rangeMax').inner_text()
        with_hardware=canvas.screenshot();page.uncheck('#hardware')
        assert canvas.screenshot()!=with_hardware, 'Gray solid context must be independently toggleable'
        page.check('#hardware')
    elif (ROOT/'volume/manifest.json').exists():
        page.select_option('#species','X');page.locator('#timeline').fill('12');page.locator('#cut').fill('0.86');page.uncheck('#edges')
    else:
        page.select_option('#species','X');page.locator('#timeline').fill('90')
    page.locator('#scene').focus();page.locator('#time').click()
    (ROOT/'docs').mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT/'docs/preview.png'),full_page=True)
    if preset == 'engine':
        page.select_option('#preset','volume')
        page.wait_for_function("document.getElementById('geometryLabel').textContent.includes('TWIN CHAMBERS') && !document.getElementById('play').disabled")
        assert page.locator('#cut').input_value() == '1'
        assert page.locator('#frameCount').inner_text() == '151'
        page.locator('#timeline').fill('70')
        assert page.locator('#time').inner_text() == '1.40 s'
    page.select_option('#preset','data')
    page.wait_for_function("document.getElementById('status').textContent.includes('SURFACE DATA')")
    assert page.locator('#cut').is_disabled()
    page.locator('#timeline').fill('90')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    print(json.dumps({'browser':'Chromium', 'errors':errors, 'checks':['load','recorded time','species','color mapping','mesh edges','orbit','play/pause','cutaway axes','camera presets','twin chamber preserved','baseline switch','mobile overflow']},indent=2))
    browser.close()
