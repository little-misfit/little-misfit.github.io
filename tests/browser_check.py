#!/usr/bin/env python3
"""Exercise the buildless profile using an already running local server."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CONTRAST = r"""() => {
  function rgba(s) { const a=s.match(/[\d.]+/g); return a ? [+a[0],+a[1],+a[2],a.length>3?+a[3]:1] : [0,0,0,0]; }
  function over(a,b) { const o=a[3]+b[3]*(1-a[3]); return [...[0,1,2].map(i=>(a[i]*a[3]+b[i]*b[3]*(1-a[3]))/(o||1)),o]; }
  function luminance(c) { const v=c.slice(0,3).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2]; }
  const rows=[];
  for(const e of document.querySelectorAll('body *')) {
    const text=[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join(' ').trim().replace(/\s+/g,' ');
    if(!text || !e.getClientRects().length || e.closest('[aria-hidden="true"]')) continue;
    const s=getComputedStyle(e); if(s.visibility==='hidden')continue;
    const ancestry=[]; let p=e; let opacity=1;
    while(p){ancestry.unshift(p);opacity*=Number(getComputedStyle(p).opacity);p=p.parentElement;}
    if(opacity===0)continue;
    let bg=[255,255,255,1]; for(const a of ancestry)bg=over(rgba(getComputedStyle(a).backgroundColor),bg);
    const color=rgba(s.color);color[3]*=opacity;const fg=over(color,bg);
    const a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const size=parseFloat(s.fontSize),large=size>=24||(size>=18.66&&parseInt(s.fontWeight)>=700),minimum=large?3:4.5;
    rows.push({text:text.slice(0,90),tag:e.tagName,classes:e.className,ratio:Number(ratio.toFixed(2)),minimum,size});
  }
  return {minimum:Math.min(...rows.map(r=>r.ratio)),failures:rows.filter(r=>r.ratio<r.minimum),smallText:rows.filter(r=>r.size<12)};
}"""
LAYOUT = """() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
  overflow:[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+.5||r.left<-.5)}).map(e=>({tag:e.tagName,classes:e.className,text:e.textContent.trim().slice(0,60)})),
  fonts:[...document.fonts].map(f=>({family:f.family,status:f.status})),
  images:[...document.images].map(i=>({src:i.getAttribute('src').slice(0,100),loaded:i.complete&&i.naturalWidth>0})),
  theme:document.documentElement.dataset.theme,
  targets:[...document.querySelectorAll('button,.paper-links a,.profile-links a,.nav-links a')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {name:e.getAttribute('aria-label')||e.textContent.trim(),width:r.width,height:r.height}})
})"""


def load_images(page):
    page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
    page.wait_for_function("[...document.images].every(i=>i.complete)")
    page.evaluate("document.fonts.ready")


def check(report, name, condition, detail=None):
    report['checks'].append({'name': name, 'pass': bool(condition), 'detail': detail})


def state(page):
    return page.evaluate("({theme:document.documentElement.dataset.theme, preference:document.documentElement.dataset.themePreference, selected:[document.querySelector('[data-theme-toggle]').dataset.mode]})")


def select_theme(page, mode):
    for _ in range(3):
        if state(page)['preference'] == mode:
            return
        page.locator('[data-theme-toggle]').click()
    assert state(page)['preference'] == mode, f'Cannot cycle to {mode}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8768/')
    parser.add_argument('--browser', default=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'),
                        help='Chromium executable; defaults to PLAYWRIGHT_CHROMIUM_EXECUTABLE or Playwright Chromium')
    args = parser.parse_args()
    output = ROOT / 'preview'; output.mkdir(exist_ok=True)
    report = {'checks': [], 'matrix': [], 'contrast': {}, 'errors': [], 'httpErrors': []}
    with sync_playwright() as pw:
        launch_options = {'args': ['--no-sandbox']}
        if args.browser:
            launch_options['executable_path'] = args.browser
        browser = pw.chromium.launch(**launch_options)
        for width, height in [(1440, 1050), (768, 1024), (390, 844), (320, 780)]:
            context = browser.new_context(viewport={'width':width, 'height':height}, color_scheme='light')
            page = context.new_page()
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.on('response', lambda r: report['httpErrors'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
            page.goto(args.url, wait_until='networkidle'); load_images(page)
            for theme in ['light','dark']:
                select_theme(page, theme); page.wait_for_timeout(500)
                layout = page.evaluate(LAYOUT); layout['viewport'] = [width,height]
                report['matrix'].append(layout)
                check(report, f'{width}/{theme}: no horizontal overflow', layout['scrollWidth']==width and not layout['overflow'], layout['overflow'])
                check(report, f'{width}/{theme}: all images loaded', all(i['loaded'] for i in layout['images']))
                check(report, f'{width}/{theme}: all three web fonts loaded', len(layout['fonts'])==3 and all(f['status']=='loaded' for f in layout['fonts']), layout['fonts'])
                theme_targets=[t for t in layout['targets'] if 'theme' in t['name'].lower()]
                check(report, f'{width}/{theme}: one theme button with 44px target', len(theme_targets)==1 and all(t['width']>=44 and t['height']>=44 for t in theme_targets),theme_targets)
                report['contrast'][f'{width}/{theme}'] = page.evaluate(CONTRAST)
                if width in (1440,390):
                    label = ('day' if theme=='light' else 'night')+('-desktop' if width==1440 else '-mobile')
                    page.screenshot(path=str(output/(label+'.png')))
                    if width==390: page.screenshot(path=str(output/(label+'-full.png')), full_page=True)
                    else:
                        page.locator('.nav-links a[href="#publications"]').click(); page.wait_for_timeout(700)
                        page.screenshot(path=str(output/(('day' if theme=='light' else 'night')+'-research.png')))
                        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                elif width==320:
                    page.screenshot(path=str(output/(f'{theme}-320.png')))
            context.close()

        context = browser.new_context(viewport={'width':1440,'height':1050}, color_scheme='light')
        page = context.new_page(); page.goto(args.url, wait_until='networkidle')
        check(report,'default theme follows light system',state(page)=={'theme':'light','preference':'system','selected':['system']},state(page))
        page.emulate_media(color_scheme='dark')
        page.wait_for_function("document.documentElement.dataset.theme==='dark'")
        check(report,'system follows preference change',state(page)['theme']=='dark',state(page))
        for mode in ['light','dark','system']:
            page.locator('[data-theme-toggle]').click()
            expected = 'dark' if mode=='system' else mode
            check(report,f'{mode}: cycle advances to correct state',state(page)=={'theme':expected,'preference':mode,'selected':[mode]},state(page))
            visible_icons = page.locator('[data-theme-icon]:visible')
            check(report,f'{mode}: one matching icon',visible_icons.count()==1 and visible_icons.first.get_attribute('data-theme-icon')==mode)
            labels = {'light': 'Day', 'dark': 'Night', 'system': 'System'}
            next_label = {'light': 'Night', 'dark': 'System', 'system': 'Day'}[mode]
            label = page.locator('[data-theme-toggle]').get_attribute('aria-label')
            check(report,f'{mode}: button explains current and next mode',label.startswith(f'Theme: {labels[mode]}') and label.endswith(f'Switch to {next_label}.'))
            page.reload(wait_until='networkidle')
            check(report,f'{mode}: persists after reload',state(page)=={'theme':expected,'preference':mode,'selected':[mode]},state(page))
        select_theme(page,'light');page.emulate_media(color_scheme='light');page.emulate_media(color_scheme='dark')
        check(report,'explicit light overrides dark system',state(page)['theme']=='light',state(page))
        second = context.new_page(); second.goto(args.url)
        select_theme(second,'dark'); page.wait_for_function("document.documentElement.dataset.theme==='dark'")
        check(report,'storage changes synchronize tabs',state(page)['preference']=='dark',state(page));second.close()
        page.evaluate("localStorage.setItem('xuanpu-theme','invalid')");page.reload()
        check(report,'invalid saved value falls back to system',state(page)['preference']=='system',state(page))
        page.keyboard.press('Tab')
        check(report,'first keyboard stop is visible skip link',page.evaluate("document.activeElement.className==='skip-link' && document.activeElement.getBoundingClientRect().top>=0"))
        page.keyboard.press('Enter');page.wait_for_timeout(500);page.keyboard.press('Tab')
        check(report,'skip link advances keyboard to main content',page.evaluate("document.querySelector('#main').contains(document.activeElement)"),page.evaluate("document.activeElement.outerHTML"))
        button=page.locator('[data-theme-toggle]');button.focus();page.keyboard.press('Space')
        check(report,'Space activates theme button',state(page)['theme']=='light')
        page.keyboard.press('Enter')
        check(report,'Enter advances theme to night',state(page)['theme']=='dark')
        check(report,'keyboard focus has visible outline',button.evaluate("e=>{const s=getComputedStyle(e);return s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>=2}"))
        page.emulate_media(reduced_motion='reduce')
        check(report,'reduced motion removes transition and smooth scroll',page.evaluate("getComputedStyle(document.documentElement).scrollBehavior==='auto' && [...document.querySelectorAll('body,*')].every(e=>getComputedStyle(e).transitionDuration.split(',').every(t=>parseFloat(t)===0))"))
        for anchor in ['news','publications','experience']:
            page.locator(f'.nav-links a[href="#{anchor}"]').click();page.wait_for_timeout(50)
            check(report,f'{anchor}: anchor heading clears sticky navigation',page.evaluate(f"document.getElementById('{anchor}').getBoundingClientRect().top>=document.querySelector('.site-nav').getBoundingClientRect().bottom"))
        context.close()

        context = browser.new_context(color_scheme='dark')
        context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage blocked','SecurityError')}})")
        page=context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)));page.goto(args.url)
        check(report,'blocked storage falls back to dark system',state(page)['theme']=='dark')
        select_theme(page,'light')
        check(report,'blocked storage still allows switching',state(page)['theme']=='light');context.close()

        for theme in ['light','dark']:
            context=browser.new_context(java_script_enabled=False,color_scheme=theme,viewport={'width':390,'height':844})
            page=context.new_page();page.goto(args.url,wait_until='networkidle')
            # Playwright evaluation remains available for observations with page scripts disabled.
            check(report,f'no JS/{theme}: content readable',page.locator('h1').is_visible() and page.locator('.profile-bio').is_visible() and page.locator('.publication-card').count()>0)
            check(report,f'no JS/{theme}: inactive controls hidden',not page.locator('.theme-toggle').is_visible())
            atmosphere='.ambient-night' if theme=='dark' else '.ambient-day'
            check(report,f'no JS/{theme}: background follows system',page.locator(atmosphere).evaluate("e=>getComputedStyle(e).opacity==='1'"))
            check(report,f'no JS/{theme}: no horizontal overflow',page.evaluate('document.documentElement.scrollWidth===innerWidth'))
            context.close()

        standalone=output/'monet-preview.html'
        if standalone.exists():
            context=browser.new_context(offline=True,color_scheme='light',viewport={'width':1440,'height':1050})
            page=context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.goto(standalone.as_uri(),wait_until='load');load_images(page)
            for theme in ['light','dark']:
                select_theme(page,theme);page.wait_for_timeout(500)
                layout=page.evaluate(LAYOUT)
                check(report,f'file offline/{theme}: switches theme',state(page)['theme']==theme)
                check(report,f'file offline/{theme}: all images loaded',all(i['loaded'] for i in layout['images']))
                check(report,f'file offline/{theme}: all three fonts loaded',len(layout['fonts'])==3 and all(f['status']=='loaded' for f in layout['fonts']),layout['fonts'])
            context.close()
        else:check(report,'standalone preview exists',False)
        browser.close()
    check(report,'no JavaScript errors',not report['errors'],report['errors'])
    check(report,'no HTTP resource errors',not report['httpErrors'],report['httpErrors'])
    for key,result in report['contrast'].items():check(report,f'{key}: text contrast',not result['failures'],result)
    report['summary']={'passed':sum(c['pass'] for c in report['checks']),'total':len(report['checks'])}
    destination=output/'browser-report.json';destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'summary':report['summary'],'failures':[c for c in report['checks'] if not c['pass']],'report':str(destination)},indent=2))
    raise SystemExit(0 if all(c['pass'] for c in report['checks']) else 1)


if __name__=='__main__':main()
