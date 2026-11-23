#!/usr/bin/env python3
"""Browser checks for the photo wall, chronological layout, map and photo details.

Uses the existing local browser and server; never requests external map tiles.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import sync_playwright
from browser_check import check, select_theme, state

ROOT = Path(__file__).resolve().parents[1]
PHOTO_SELECTOR = '.event-photo'


def ready(page):
    page.wait_for_selector('.photo-journal.is-enhanced')
    page.evaluate('document.fonts.ready')
    page.wait_for_function("[...document.querySelectorAll('.event-photo img')].every(i=>i.complete&&i.naturalWidth>0)")


def settle(page):
    page.wait_for_function("[...document.querySelectorAll('.event-photo')].every(e=>e.getAnimations().every(a=>a.playState!=='running'))")


def mode(page, name):
    if page.locator('.photo-journal').get_attribute('data-view') != name:
        page.locator('.view-toggle').click()
        page.locator(f'.view-menu [data-view="{name}"]').click()
        page.wait_for_function('(v)=>document.querySelector(".photo-journal").dataset.view===v',arg=name)
        settle(page)


def viewer_ready(page):
    page.wait_for_function("document.querySelector('.photo-viewer').open && !document.querySelector('.viewer-image').hidden && document.querySelector('.viewer-image').naturalWidth>0")


def close_viewer(page):
    page.keyboard.press('Escape')
    page.wait_for_function("!document.querySelector('.photo-viewer').open && !document.body.classList.contains('viewer-open')")


def geometry(page):
    return page.evaluate("""() => [...document.querySelectorAll('.event-photo')].map(e=>({
      id:e.dataset.id,date:e.dataset.date,x:e.offsetLeft,y:e.offsetTop,w:e.offsetWidth,h:e.offsetHeight,
      stack:e.dataset.stack,hidden:e.getAttribute('aria-hidden'),tab:e.tabIndex,opacity:Number(getComputedStyle(e).opacity)
    }))""")


def check_transition(report, page, destination):
    """Verify movement during the transition, excluding unrelated CSS fades."""
    source=page.locator('.photo-journal').get_attribute('data-view')
    target=page.locator('[data-id="sample-01"]')
    page.locator('.view-toggle').click()
    before=target.bounding_box()
    page.locator(f'.view-menu [data-view="{destination}"]').evaluate('e=>e.click()')
    samples=[]
    for delay in (100,150):
        page.wait_for_timeout(delay)
        samples.append({'box':target.bounding_box(),'moving':page.evaluate("""[...document.querySelectorAll('.event-photo')].some(e=>
          e.getAnimations().some(a=>a.playState==='running' && a.effect.getKeyframes().some(k=>'transform' in k)))""")})
    settle(page)
    after=target.bounding_box()
    between=lambda box:any(abs(box[axis]-before[axis])>2 and abs(box[axis]-after[axis])>2 and min(before[axis],after[axis])-2<=box[axis]<=max(before[axis],after[axis])+2 for axis in ('x','y','width','height'))
    detail={'before':before,'at100ms':samples[0],'at250ms':samples[1],'after':after}
    check(report,f'{source} to {destination}: photo transform animations remain active at 100 and 250 ms',all(sample['moving'] for sample in samples),detail)
    check(report,f'{source} to {destination}: intermediate photo geometry travels between layouts',all(between(sample['box']) for sample in samples),detail)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8768/')
    parser.add_argument('--browser',default=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
    args = parser.parse_args()
    output = ROOT/'preview';output.mkdir(exist_ok=True)
    report = {'checks':[],'errors':[],'httpErrors':[],'externalRequests':[]}
    origin = urlsplit(args.url).netloc
    with sync_playwright() as pw:
        settings = {'args':['--no-sandbox']}
        if args.browser: settings['executable_path']=args.browser
        browser = pw.chromium.launch(**settings)

        def instrument(page):
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.on('response',lambda r:report['httpErrors'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
            page.on('request',lambda r:report['externalRequests'].append(r.url) if urlsplit(r.url).scheme in ('http','https') and urlsplit(r.url).netloc != origin else None)

        context=browser.new_context(viewport={'width':1440,'height':1050},color_scheme='light')
        page=context.new_page();instrument(page)
        page.goto(args.url,wait_until='networkidle');select_theme(page,'dark')
        page.locator('.nav-links a[href="events.html"]').click();page.wait_for_url('**/events.html');ready(page)
        check(report,'homepage opens Events and retains selected theme',state(page)['theme']=='dark')
        check(report,'default view is a scrollable photo wall',page.locator('.photo-journal').get_attribute('data-view')=='wall' and page.locator('.photo-stage').evaluate('e=>e.scrollHeight>e.clientHeight'))
        photo_count=page.locator(PHOTO_SELECTOR).count()
        check(report,'sample metadata is explicitly identified',page.locator('.collection-note').inner_text().lower().find('illustrative')>=0)

        # Actual movement, pause and hover response rather than only checking flags.
        stage=page.locator('.photo-stage');page.mouse.move(0,0)
        stage.scroll_into_view_if_needed();page.wait_for_timeout(2300)
        start=stage.evaluate('e=>e.scrollTop');page.wait_for_timeout(650)
        check(report,'wall slowly scrolls by default',stage.evaluate('e=>e.scrollTop')>start+3)
        first=page.locator(PHOTO_SELECTOR).first;first.hover();page.wait_for_timeout(600)
        paused=stage.evaluate('e=>e.scrollTop');page.wait_for_timeout(400)
        check(report,'hover pauses movement and reveals photo feedback',abs(stage.evaluate('e=>e.scrollTop')-paused)<1 and float(first.locator('.photo-hover').evaluate('e=>getComputedStyle(e).opacity'))>.9)
        check(report,'hover gently scales the image',first.locator('img').evaluate('e=>getComputedStyle(e).transform')!='none')
        page.mouse.move(0,0);first.focus();page.wait_for_timeout(100)
        paused=stage.evaluate('e=>e.scrollTop');page.wait_for_timeout(450)
        check(report,'keyboard focus pauses movement while reading a photo',abs(stage.evaluate('e=>e.scrollTop')-paused)<1)
        page.locator('.motion-toggle').click()
        check(report,'pause button stops the wall',page.locator('.motion-toggle').get_attribute('aria-pressed')=='false')
        paused=stage.evaluate('e=>e.scrollTop');page.wait_for_timeout(450)
        check(report,'paused wall remains still',abs(stage.evaluate('e=>e.scrollTop')-paused)<1)
        page.locator('.motion-toggle').click();stage.hover();page.mouse.wheel(0,120);page.wait_for_timeout(120)
        check(report,'manual scrolling pauses automatic movement',page.locator('.motion-toggle').get_attribute('aria-pressed')=='false')
        stage.evaluate('e=>e.scrollTop=0')

        # All views reuse the same photo nodes and animate their geometry.
        page.evaluate('window.__originalPhotos=[...document.querySelectorAll(".event-photo")]')
        old=geometry(page)
        page.locator('.view-toggle').click()
        start_box=page.locator('[data-id="sample-02"]').bounding_box()
        page.locator('.view-menu [data-view="time"]').evaluate('e=>e.click()')
        moving=page.evaluate("[...document.querySelectorAll('.event-photo')].filter(e=>e.getAnimations().some(a=>a.playState==='running' && a.effect.getKeyframes().some(k=>'transform' in k))).length")
        check(report,'view change animates the photos themselves',moving>0)
        page.wait_for_timeout(200)
        middle_box=page.locator('[data-id="sample-02"]').bounding_box()
        settle(page);new=geometry(page)
        final_box=page.locator('[data-id="sample-02"]').bounding_box()
        moving_between=any(abs(middle_box[axis]-start_box[axis])>2 and abs(middle_box[axis]-final_box[axis])>2 and min(start_box[axis],final_box[axis])-2<=middle_box[axis]<=max(start_box[axis],final_box[axis])+2 for axis in ('x','y'))
        check(report,'intermediate photo position lies between old and new arrangements',moving_between,{'before':start_box,'during':middle_box,'after':final_box})
        check(report,'photos retain DOM identity across rearrangement',page.evaluate('window.__originalPhotos.every(e=>document.querySelector(".photo-canvas").contains(e))'))
        check(report,'time mode visibly rearranges the wall',any(a['x']!=b['x'] or a['y']!=b['y'] for a in old for b in new if a['id']==b['id']))
        expected=sorted(new,key=lambda p:p['date'],reverse=True)
        visual=sorted(new,key=lambda p:(round(p['y']),p['x']))
        check(report,'time mode orders photos newest first in visual reading order',[p['id'] for p in visual]==[p['id'] for p in expected])
        check(report,'month groups label the timeline',page.locator('.time-heading').count()==len({p['date'][:7] for p in new}))
        check_transition(report,page,'place')
        check_transition(report,page,'wall')
        check_transition(report,page,'place')
        check_transition(report,page,'time')
        check_transition(report,page,'wall')

        for width in [1440,768,390,320]:
            page.set_viewport_size({'width':width,'height':1050 if width>=768 else 844})
            for theme in ['light','dark']:
                select_theme(page,theme)
                for view in ['wall','time','place']:
                    mode(page,view);page.mouse.move(0,0);page.wait_for_timeout(120)
                    data=page.evaluate("""() => ({overflow:document.documentElement.scrollWidth>innerWidth,
                      stage:document.querySelector('.photo-stage').clientWidth,
                      canvas:document.querySelector('.photo-canvas').scrollWidth,
                      count:document.querySelectorAll('.event-photo').length,
                      images:[...document.querySelectorAll('.event-photo img')].every(i=>i.complete&&i.naturalWidth>0)})""")
                    check(report,f'{width}/{theme}/{view}: responsive content and assets',not data['overflow'] and data['images'] and data['count']==photo_count and (view=='place' or data['canvas']<=data['stage']+1),data)
                    if view=='place':
                        check(report,f'{width}/{theme}: real geographic basemap and accessible photo stacks',page.locator('.map-land').count()>100 and page.locator('.event-photo[data-stack="front"]').count()>0)
                    if width in [1440,390]:
                        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                        page.screenshot(path=str(output/f'event-qa-{view}-{theme}-{width}.png'),full_page=True)

        # Map exploration and place-specific details, tested at a stable desktop size.
        page.set_viewport_size({'width':1440,'height':1050});mode(page,'place')
        page.locator('.map-reset').click();page.wait_for_timeout(150)
        locations={p['id']:p for p in geometry(page)}
        check(report,'map positions preserve known east-west and north-south geography',locations['sample-01']['x']>locations['sample-03']['x'] and locations['sample-01']['y']<locations['sample-03']['y'] and locations['sample-02']['x']>locations['sample-03']['x'])
        top=page.locator('.event-photo[data-stack="front"][data-place="Tianjin"]')
        top.click();viewer_ready(page)
        check(report,'map photo opens its location group with title, date and notes',page.locator('.viewer-count').text_content()=='1 / 3' and page.locator('.viewer-place').text_content()=='Tianjin' and bool(page.locator('#viewer-title').text_content()) and bool(page.locator('.viewer-date').text_content()) and bool(page.locator('#viewer-caption').text_content()))
        close_viewer(page)
        cluster=page.locator('.event-photo[data-stack="front"]').filter(has=page.locator('.photo-map-label:text("2 places")'))
        if cluster.count():
            before=geometry(page);cluster.first.click();page.wait_for_timeout(850)
            after=geometry(page)
            check(report,'nearby-place cluster zooms and separates into individual locations',page.locator('.photo-viewer').evaluate('e=>!e.open') and len([p for p in after if p['stack']=='front'])>len([p for p in before if p['stack']=='front']))
        else:
            check(report,'nearby-place cluster available at overview',False)
        page.locator('.map-reset').click();page.wait_for_timeout(200)
        before=geometry(page)
        bounds=page.locator('.map-canvas').bounding_box()
        page.mouse.move(bounds['x']+bounds['width']/2,bounds['y']+bounds['height']/2)
        page.mouse.down();page.mouse.move(bounds['x']+bounds['width']/2+110,bounds['y']+bounds['height']/2+30,steps=8);page.mouse.up();page.wait_for_timeout(350)
        after=geometry(page)
        check(report,'map drag moves photo locations with the basemap',any(abs(a['x']-b['x'])>20 for a in before for b in after if a['id']==b['id']))
        page.locator('.map-reset').click()
        before=geometry(page);page.locator('.leaflet-control-zoom-in').click();page.wait_for_timeout(180)
        after=geometry(page)
        check(report,'map zoom controls change geographic photo spacing',any(abs(a['x']-b['x'])>20 or abs(a['y']-b['y'])>20 for a in before for b in after if a['id']==b['id']))

        # Modal keyboard/focus, boundary behavior, and error recovery.
        mode(page,'wall');first=page.locator(PHOTO_SELECTOR).first;first.focus();page.keyboard.press('Enter');viewer_ready(page)
        check(report,'keyboard opens full photo details',page.locator('.photo-viewer').is_visible())
        page.evaluate("document.querySelector('.photo-viewer').close();document.querySelector('.event-photo').click()")
        page.wait_for_timeout(100);viewer_ready(page)
        check(report,'immediate close/reopen does not lose the image or scroll lock',page.locator('body').evaluate("e=>e.classList.contains('viewer-open')") and bool(page.locator('.viewer-image').get_attribute('src')))
        trapped=True
        for key in ['Tab','Shift+Tab']:
            for _ in range(5):
                page.keyboard.press(key);trapped=trapped and page.evaluate("document.querySelector('.photo-viewer').contains(document.activeElement)")
        check(report,'Tab and Shift+Tab remain within the dialog',trapped)
        for _ in range(photo_count-1):page.keyboard.press('ArrowRight')
        viewer_ready(page)
        check(report,'arrow keys reach the last photo and disable Next',page.locator('.viewer-count').text_content()==f'{photo_count} / {photo_count}' and page.locator('[data-photo-step="1"]').is_disabled())
        check(report,'boundary navigation keeps focus on an enabled dialog control',page.evaluate("document.querySelector('.photo-viewer').contains(document.activeElement) && !document.activeElement.disabled"))
        close_viewer(page)
        check(report,'Escape restores focus and page scrolling',first.evaluate('e=>document.activeElement===e') and not page.locator('body').evaluate("e=>e.classList.contains('viewer-open')"))
        original=first.get_attribute('href');first.evaluate("e=>e.href='data:image/png;base64,not-an-image'")
        first.click();page.wait_for_function("document.querySelector('.viewer-status').textContent==='This photo could not be loaded.'")
        check(report,'failed photo has a readable error',page.locator('.viewer-status').is_visible() and not page.locator('.viewer-image').is_visible())
        page.locator('[data-photo-step="1"]').click();viewer_ready(page)
        check(report,'next valid photo recovers from an image error',not page.locator('.viewer-status').is_visible())
        close_viewer(page);first.evaluate('(e,v)=>e.setAttribute("href",v)',original)
        page.set_viewport_size({'width':390,'height':844});first.click();viewer_ready(page)
        check(report,'mobile dialog fits and scrolls all information into reach',page.locator('.photo-viewer').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight&&e.scrollHeight>=e.clientHeight}'))
        page.locator('.viewer-place').scroll_into_view_if_needed()
        check(report,'mobile location text is accessible',page.locator('.viewer-place').is_visible())
        close_viewer(page)

        page.locator('.view-toggle').click();page.keyboard.press('ArrowDown');page.keyboard.press('Enter');settle(page)
        check(report,'view picker supports arrow and Enter keys',page.locator('.photo-journal').get_attribute('data-view')=='time')
        page.locator('.view-toggle').click();page.keyboard.press('Escape')
        check(report,'Escape closes picker and restores trigger focus',not page.locator('.view-menu').is_visible() and page.locator('.view-toggle').evaluate('e=>document.activeElement===e'))
        page.evaluate("for(const v of ['place','wall','time','place','wall']) document.querySelector(`.view-menu [data-view=${v}]`).click()")
        settle(page)
        check(report,'rapid view changes settle into the requested mode with all photos',page.locator('.photo-journal').get_attribute('data-view')=='wall' and page.locator(PHOTO_SELECTOR).count()==photo_count and all(p['w']>100 and p['hidden'] is None for p in geometry(page)))
        page.locator('.nav-links a[href="index.html"]').click();page.wait_for_url('**/index.html')
        check(report,'Events returns to homepage with the chosen theme',page.locator('.profile-bio').is_visible() and state(page)['theme']=='dark')
        context.close()

        # Reduced motion must govern both ambient scrolling and layout transitions.
        context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        page=context.new_page();instrument(page);page.goto(urljoin(args.url,'events.html'));ready(page)
        page.mouse.move(0,0);page.wait_for_timeout(2500)
        check(report,'reduced motion starts with no automatic scrolling',page.locator('.motion-toggle').get_attribute('aria-pressed')=='false' and page.locator('.photo-stage').evaluate('e=>e.scrollTop')==0)
        page.locator('.view-toggle').click();page.locator('.view-menu [data-view="time"]').evaluate('e=>e.click()')
        check(report,'reduced motion rearranges without animation',page.evaluate("[...document.querySelectorAll('.event-photo')].every(e=>e.getAnimations().length===0)"))
        context.close()

        # Render missing metadata before application initialization, without modifying source.
        context=browser.new_context(viewport={'width':1440,'height':1050})
        def incomplete(route):
            response=route.fetch();body=response.text()
            body=body.replace('data-date="2026-10-18"','data-date=""',1).replace('data-lat="39.13" data-lng="117.20"','data-lat="" data-lng=""',1)
            route.fulfill(response=response,body=body)
        context.route('**/events.html',incomplete)
        page=context.new_page();instrument(page);page.goto(urljoin(args.url,'events.html'));ready(page)
        mode(page,'time');heads=page.locator('.time-heading').all_text_contents()
        check(report,'missing dates are retained in an Undated group at the end',heads[-1].startswith('Undated'))
        mode(page,'place')
        check(report,'photos without coordinates retain an accessible map stack',page.locator('.map-unlocated').is_visible() and page.locator('[data-id="sample-01"]').get_attribute('tabindex')=='0')
        page.locator('[data-id="sample-01"]').click();viewer_ready(page)
        check(report,'ungeotagged photo remains openable with Undated information',page.locator('.viewer-date').text_content()=='Undated' and page.locator('.viewer-count').text_content()=='1 / 1')
        context.close()

        context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        page=context.new_page();instrument(page);page.goto(urljoin(args.url,'events.html'),wait_until='networkidle')
        check(report,'no-JS photo wall preserves image links and hides unavailable controls',page.locator(PHOTO_SELECTOR).count()==photo_count and not page.locator('.view-picker').is_visible() and not page.locator('.motion-toggle').is_visible())
        page.locator(PHOTO_SELECTOR).first.click();page.wait_for_url('**/placeholder.svg')
        check(report,'no-JS photos open directly',page.url.endswith('/placeholder.svg'))
        context.close()

        context=browser.new_context(offline=True,viewport={'width':390,'height':844})
        page=context.new_page();instrument(page);page.goto((output/'monet-preview.html').as_uri())
        page.locator('.nav-links a[href="events-preview.html"]').click();page.wait_for_url('**/events-preview.html');ready(page)
        mode(page,'time');mode(page,'place')
        check(report,'offline export includes functional geographic map and photo stacks',page.locator('.map-land').count()>100 and page.locator('.event-photo[data-stack="front"]').count()>0)
        mode(page,'wall');page.locator(PHOTO_SELECTOR).first.click();viewer_ready(page)
        check(report,'offline photo details use embedded image data',page.locator('.viewer-image').get_attribute('src').startswith('data:image/'))
        close_viewer(page);page.locator('.nav-links a[href="monet-preview.html"]').click();page.wait_for_url('**/monet-preview.html')
        check(report,'offline Events returns to its paired homepage export',page.locator('.profile-bio').is_visible())
        context.close();browser.close()

    check(report,'no JavaScript errors',not report['errors'],report['errors'])
    check(report,'no unexpected HTTP errors',not report['httpErrors'],report['httpErrors'])
    check(report,'map and UI make no external runtime requests',not report['externalRequests'],report['externalRequests'])
    report['summary']={'passed':sum(c['pass'] for c in report['checks']),'total':len(report['checks'])}
    destination=output/'event-browser-report.json';destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'summary':report['summary'],'failures':[c for c in report['checks'] if not c['pass']],'report':str(destination)},indent=2))
    raise SystemExit(0 if all(c['pass'] for c in report['checks']) else 1)


if __name__=='__main__':main()
