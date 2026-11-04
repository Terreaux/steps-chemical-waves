"""Exercise the user-visible playback and WebGL output, including mobile layout."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8765')
    page.wait_for_function("!document.getElementById('play').disabled")
    canvas = page.locator('#scene')
    initial = canvas.screenshot()
    page.locator('#timeline').fill('70')
    assert '1.40' in page.locator('#time').inner_text() if (ROOT/'volume/manifest.json').exists() else '0.70' in page.locator('#time').inner_text()
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
    page.click('#play')
    frame_before = page.locator('#timeline').input_value()
    page.wait_for_timeout(250)
    assert page.locator('#timeline').input_value() != frame_before
    page.click('#play')
    if (ROOT/'volume/manifest.json').exists():
        page.select_option('#species','X');page.locator('#timeline').fill('12');page.locator('#cut').fill('0.86');page.uncheck('#edges')
    else:
        page.select_option('#species','X');page.locator('#timeline').fill('90')
    page.locator('#scene').focus();page.locator('#time').click()
    (ROOT/'docs').mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT/'docs/preview.png'),full_page=True)
    page.select_option('#preset','data')
    page.wait_for_function("document.getElementById('status').textContent.includes('SURFACE DATA')")
    assert page.locator('#cut').is_disabled()
    page.locator('#timeline').fill('90')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    print(json.dumps({'browser':'Chromium', 'errors':errors, 'checks':['load','recorded time','species','mesh edges','orbit','play/pause','cutaway if available','baseline switch','mobile overflow']},indent=2))
    browser.close()
