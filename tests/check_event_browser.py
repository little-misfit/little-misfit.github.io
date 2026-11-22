#!/usr/bin/env python3
"""Check the Event page, navigation and native photo viewer with Playwright."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from browser_check import check, select_theme, state

ROOT = Path(__file__).resolve().parents[1]


def loaded_photos(page):
    page.evaluate("document.fonts.ready")
    page.wait_for_function("[...document.querySelectorAll('.event-photo img')].every(i=>i.complete&&i.naturalWidth>0)")


def viewer_loaded(page):
    page.wait_for_function("document.querySelector('.photo-viewer').open && !document.querySelector('.viewer-image').hidden && document.querySelector('.viewer-image').naturalWidth>0")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8768/')
    parser.add_argument('--browser', default=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
    args = parser.parse_args()
    output = ROOT / 'preview'; output.mkdir(exist_ok=True)
    report = {'checks': [], 'errors': [], 'httpErrors': []}
    with sync_playwright() as pw:
        options = {'args': ['--no-sandbox']}
        if args.browser: options['executable_path'] = args.browser
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width':1440,'height':1050}, color_scheme='light')
        page = context.new_page()
        page.on('pageerror', lambda e:report['errors'].append(str(e)))
        page.on('response', lambda r:report['httpErrors'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(args.url, wait_until='networkidle')
        select_theme(page, 'dark')
        page.locator('.nav-links a[href="event.html"]').click()
        page.wait_for_url('**/event.html'); loaded_photos(page)
        check(report, 'homepage opens Event with the chosen theme', state(page)['preference']=='dark' and state(page)['theme']=='dark')
        page.locator('.nav-links a[href="index.html"]').click()
        page.wait_for_url('**/index.html')
        check(report, 'Event returns to homepage with the chosen theme', page.locator('.profile-bio').is_visible() and state(page)['preference']=='dark')
        page.locator('.nav-links a[href="event.html"]').click(); page.wait_for_url('**/event.html')

        for width in [1440,768,390,320]:
            page.set_viewport_size({'width':width,'height':1050 if width>=768 else 844})
            for mode in ['light','dark']:
                select_theme(page, mode); page.mouse.move(0,0); page.wait_for_timeout(450)
                data = page.evaluate("""() => ({overflow:document.documentElement.scrollWidth>innerWidth,
                  photos:[...document.querySelectorAll('.event-photo img')].every(i=>i.complete&&i.naturalWidth>0),
                  active:[...document.querySelectorAll('.nav-links [aria-current=page]')].map(e=>e.textContent),
                  entry:document.querySelector('.event-entry').getBoundingClientRect().width})""")
                check(report, f'{width}/{mode}: layout and photo assets', not data['overflow'] and data['photos'] and data['entry']<=width, data)
                check(report, f'{width}/{mode}: Event navigation remains visible and active', page.locator('.nav-links [aria-current="page"]').is_visible() and data['active']==['Event'])
                if width in [1440,390]:
                    name=('day' if mode=='light' else 'night')+('-desktop' if width==1440 else '-mobile')
                    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                    page.screenshot(path=str(output/('event-qa-'+name+'.png')), full_page=True)
                page.locator('.event-photo').first.click(); viewer_loaded(page)
                check(report, f'{width}/{mode}: viewer fits viewport', page.locator('.photo-viewer').evaluate("e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}"))
                page.keyboard.press('Escape')
                page.wait_for_function("!document.querySelector('.photo-viewer').open")

        page.set_viewport_size({'width':1440,'height':1050})
        page.evaluate("const g=document.querySelector('.event-gallery').cloneNode(true);g.dataset.testExtra='';document.querySelector('.event-content').append(g)")
        first = page.locator('.event-photo').first
        first.focus(); page.keyboard.press('Enter'); viewer_loaded(page)
        check(report,'keyboard opens the photo viewer', page.locator('.photo-viewer').is_visible())
        check(report,'viewer stays within the selected photo group', page.locator('.viewer-count').text_content()=='1 / 3' and page.locator('.event-photo').count()==6)
        check(report,'first image has the expected caption and navigation boundary', page.locator('#viewer-caption').text_content()=='Photo placeholder' and page.locator('[data-photo-step="-1"]').is_disabled())
        page.evaluate("document.querySelector('.photo-viewer').close();document.querySelector('.event-photo').click()")
        page.wait_for_timeout(150);viewer_loaded(page)
        check(report,'immediate close/reopen survives queued close events',page.locator('body').evaluate("e=>e.classList.contains('viewer-open')") and bool(page.locator('.viewer-image').get_attribute('src')))
        trapped = True
        for key in ['Tab', 'Shift+Tab']:
            for _ in range(6):
                page.keyboard.press(key)
                trapped = trapped and page.evaluate("document.querySelector('.photo-viewer').contains(document.activeElement)")
        check(report,'Tab and Shift+Tab keep focus in the modal',trapped)
        page.locator('[data-photo-step="1"]').click(); viewer_loaded(page)
        check(report,'Next moves to the second photo',page.locator('.viewer-count').text_content()=='2 / 3')
        page.keyboard.press('ArrowRight'); viewer_loaded(page)
        page.wait_for_timeout(150)
        check(report,'Right arrow reaches the last photo and disables Next',page.locator('.viewer-count').text_content()=='3 / 3' and page.locator('[data-photo-step="1"]').is_disabled())
        check(report,'last photo keeps focus on an enabled viewer control',page.evaluate("document.querySelector('.photo-viewer').contains(document.activeElement) && !document.activeElement.disabled"))
        page.keyboard.press('ArrowLeft'); viewer_loaded(page)
        check(report,'Left arrow moves back',page.locator('.viewer-count').text_content()=='2 / 3')
        page.locator('[data-photo-step="-1"]').click(); viewer_loaded(page)
        page.wait_for_timeout(150)
        check(report,'Previous returns to first photo',page.locator('.viewer-count').text_content()=='1 / 3')
        check(report,'first photo keeps focus on an enabled viewer control',page.evaluate("document.querySelector('.photo-viewer').contains(document.activeElement) && !document.activeElement.disabled"))
        page.keyboard.press('Escape');page.wait_for_function("!document.querySelector('.photo-viewer').open")
        page.wait_for_function("!document.body.classList.contains('viewer-open')")
        check(report,'Escape closes, restores focus and unlocks scrolling',first.evaluate('e=>document.activeElement===e') and not page.locator('body').evaluate("e=>e.classList.contains('viewer-open')"))
        page.locator('[data-test-extra]').evaluate('(e)=>e.remove()')
        first.click();viewer_loaded(page);page.mouse.click(2,2)
        check(report,'outside click closes the viewer',not page.locator('.photo-viewer').evaluate('e=>e.open'))
        original = first.get_attribute('href')
        first.evaluate("e=>e.href='data:image/png;base64,not-an-image'")
        first.click();page.wait_for_function("document.querySelector('.viewer-status').textContent==='This photo could not be loaded.'")
        check(report,'invalid image shows a readable error',page.locator('.viewer-status').is_visible() and not page.locator('.viewer-image').is_visible())
        page.locator('[data-photo-step="1"]').click();viewer_loaded(page)
        check(report,'viewer recovers by moving to a valid image',page.locator('.viewer-count').text_content()=='2 / 3' and not page.locator('.viewer-status').is_visible())
        page.locator('.viewer-close').click()
        first.evaluate('(e,href)=>e.setAttribute("href",href)',original)
        context.close()

        for mode in ['light','dark']:
            context=browser.new_context(java_script_enabled=False,color_scheme=mode,viewport={'width':390,'height':844})
            page=context.new_page();page.goto(urljoin(args.url,'event.html'),wait_until='networkidle')
            check(report,f'no JS/{mode}: content and native image links remain usable',page.locator('.event-entry').is_visible() and page.locator('.event-photo').first.get_attribute('href').endswith('.svg') and not page.locator('.photo-viewer').is_visible() and not page.locator('.theme-toggle').is_visible())
            photo=page.locator('.event-photo').first;target=photo.get_attribute('href');photo.click();page.wait_for_url('**/placeholder.svg')
            check(report,f'no JS/{mode}: image opens directly',page.url.endswith('/placeholder.svg'))
            context.close()

        context=browser.new_context(offline=True,color_scheme='light',viewport={'width':390,'height':844})
        page=context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.goto((output/'monet-preview.html').as_uri(),wait_until='load')
        page.locator('.nav-links a[href="event-preview.html"]').click();page.wait_for_url('**/event-preview.html');loaded_photos(page)
        select_theme(page,'dark');page.locator('.event-photo').first.click();viewer_loaded(page)
        check(report,'offline export supports linked navigation, theme and photo viewing',state(page)['theme']=='dark' and page.locator('.viewer-image').get_attribute('src').startswith('data:image/'))
        page.keyboard.press('Escape');page.locator('.nav-links a[href="monet-preview.html"]').click();page.wait_for_url('**/monet-preview.html')
        check(report,'offline Event returns to the paired homepage export',page.locator('.profile-bio').is_visible())
        context.close();browser.close()
    check(report,'no JavaScript errors',not report['errors'],report['errors'])
    check(report,'no unexpected HTTP errors',not report['httpErrors'],report['httpErrors'])
    report['summary']={'passed':sum(c['pass'] for c in report['checks']),'total':len(report['checks'])}
    destination=output/'event-browser-report.json';destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'summary':report['summary'],'failures':[c for c in report['checks'] if not c['pass']],'report':str(destination)},indent=2))
    raise SystemExit(0 if all(c['pass'] for c in report['checks']) else 1)


if __name__=='__main__':main()
