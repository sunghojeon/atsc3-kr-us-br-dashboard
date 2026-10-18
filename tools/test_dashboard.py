"""Regression checks for comparison integrity and the rendered local HTML.

python tools/test_dashboard.py [--browser --artifacts PATH]
The optional browser check uses an isolated headless Chromium, never a user's profile.
"""
from pathlib import Path
import argparse,json,re

ROOT=Path(__file__).resolve().parent.parent

def load(): return json.loads((ROOT/'data/standards.json').read_text(encoding='utf-8'))

def check_data():
    data=load();rows=data['rows'];features=data['comparisons'];baseline=data['baseline']['documents']
    ids={row['id'] for row in rows}; assert len(ids)==len(rows),'Duplicate rows'
    official={doc['id'] for doc in baseline}; assert len(official)==35
    assert {row['id'] for row in rows if re.fullmatch(r'A/\d+(?: Part \d)?',row['id'])}==official
    assert len({feature['id'] for feature in features})==len(features),'Duplicate features'
    assert next(doc for doc in baseline if doc['id']=='A/362')['edition']=='2026-09'
    assert next(row for row in rows if row['id']=='A/362')['cells']['ATSC']['docs']==['A/362:2026-09']
    # These public OG links were previously lost by a generic “unreviewed” fallback.
    by_id={row['id']:row for row in rows}
    assert by_id['A/327']['verdicts']['SBTVD']['code']=='partial'
    assert 'SBTVD OG-01' in by_id['(no ATSC document / monitoring)']['cells']['SBTVD']['docs']
    assert 'SBTVD OG-03' in by_id['(no ATSC document / 3DTV)']['cells']['SBTVD']['docs']
    assert all(re.fullmatch(r'[a-f0-9]{64}',doc['sha256']) for doc in baseline)
    for row in rows:
        assert row.get('evidence'),row['id']+' has no evidence'
        assert row['review']['updated']==data['meta']['updated'],row['id']+' stale review'
        for org in ('TTA','SBTVD'):
            verdict=row['verdicts'][org]
            assert verdict['code'] in data['verdicts']
            assert verdict.get('kind')!='pending','Unreviewed conflated with no counterpart'
            if verdict['code']=='same':
                assert not any(f.get('verdicts',{}).get(org,{}).get('code') in ('partial','diff','review') for f in row.get('comparisons',[])),row['id']+' summary contradicts a feature'
            if any('ABNT NBR' in doc for doc in row['cells'][org].get('docs',[])):
                assert row['cells'][org].get('unverified'),row['id']+' ABNT scope hidden'
        for evidence in row['evidence']:
            assert evidence.get('url','').startswith(('https://','http://','docs/refs/')),str(evidence)
    for feature in features:
        assert set(feature.get('atsc_docs',[]))<=ids,feature['id']+' orphan'
        assert feature.get('evidence'),feature['id']+' source missing'
        assert feature['reviewed']['date']==data['meta']['updated'],feature['id']+' stale review'
        for org in ('TTA','SBTVD'):
            assert feature.get('verdicts',{}).get(org,{}).get('text'),feature['id']+' reason missing'
    js=(ROOT/'data/standards.js').read_text(encoding='utf-8')
    assert json.loads(js.split('=',1)[1].strip().removesuffix(';'))==data
    reg=next(r for r in data['regulations'] if 'Resolução nº 789' in r['id'])
    assert reg['signed']=='2026-07-06' and reg['published']=='2026-07-13' and not reg['effective']
    assert '250–298' in reg['note'] and '298–322' in reg['note']
    assert len(next(r for r in data['regulations'] if r['org']=='ATSC')['clauses'])==2
    return {'rows':len(rows),'features':len(features),'chapter_documents':sum(bool(r.get('chapters')) for r in rows),'chapter_rows':sum(len(r.get('chapters',{}).get('rows',[])) for r in rows),'approved_atsc':len(official)}

def check_browser(artifacts):
    from playwright.sync_api import sync_playwright
    artifacts.mkdir(parents=True,exist_ok=True)
    result={'row_details':[],'searches':{},'viewports':[],'errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda error:result['errors'].append(str(error)))
        # Test the offline fallback fonts too; HTML/JS/data remain local.
        page.route('https://fonts.googleapis.com/**',lambda route:route.abort())
        page.route('https://fonts.gstatic.com/**',lambda route:route.abort())
        page.goto((ROOT/'index.html').as_uri(),wait_until='load')
        page.wait_for_function('Boolean(window.COMPARISON_APP)')
        data=load(); assert page.locator('tr.row').count()==len(data['rows'])
        page.screenshot(path=str(artifacts/'desktop-top.png'))
        # Native button keyboard activation must expand and collapse, retaining focus.
        first=page.locator('.row-toggle').first
        first.focus();first.press('Enter');assert first.get_attribute('aria-expanded')=='true'
        page.locator('.row-toggle').first.press('Space');assert page.locator('.row-toggle').first.get_attribute('aria-expanded')=='false'
        feature_ids=set()
        for index,row in enumerate(data['rows']):
            button=page.locator('.row-toggle').nth(index);button.click()
            panel=page.locator('tr.detail:not([hidden])')
            assert panel.count()==1,row['id']
            assert panel.locator('.panel').is_visible(),row['id']
            # “undefined transmission scope” is legitimate standard terminology.
            assert not any(text.strip() in ('undefined','null','NaN','[object Object]') for text in panel.locator('td').all_text_contents()),row['id']
            for feature in row.get('comparisons',[]):
                feature_ids.add(feature['id'])
                rendered=panel.locator('[data-feature="'+feature['id']+'"]')
                assert rendered.count()==1
                text=rendered.inner_text()
                for org in ('TTA','SBTVD'): assert feature['verdicts'][org]['text'] in text,feature['id']+' reason hidden'
                if feature.get('recommendation'): assert feature['recommendation'] in text,feature['id']+' recommendation hidden'
            if row['id'] in ('A/200','A/322','A/331','A/341','A/338','A/345','A/362'):
                panel.scroll_into_view_if_needed();page.screenshot(path=str(artifacts/('detail-'+re.sub(r'[^a-zA-Z0-9]','_',row['id'])+'.png')))
            result['row_details'].append(row['id'])
        assert feature_ids=={f['id'] for f in data['comparisons']}
        for term,required in [('currentUtcOffset','A/331'),('dsHour','A/331'),('ZIP_BR','A/331 §AEA'),('AEAVoiceText','A/331 §AEA'),('MP24_2','A/322'),('Service Linkage','A/338'),('QUOTA_EXCEEDED_ERROR','A/362')]:
            page.locator('#q').fill(term)
            matches=page.locator('tr.row').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)')
            assert required in matches,(term,matches)
            result['searches'][term]=matches
        page.locator('#reset').click();page.locator('#f-diff').check()
        differences=page.locator('tr.row').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)')
        assert 'A/321' in differences and 'A/322' in differences
        page.locator('#reset').click();page.locator('#f-unv').check()
        unverified=page.locator('tr.row').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)')
        assert 'A/321' in unverified and 'A/322' in unverified
        result['differences']=differences;result['unverified']=unverified
        page.locator('#reset').click()
        for category in data['categories']:
            page.locator('#tabs button[data-id="'+category['id']+'"]').click()
            actual=page.locator('tr.row').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)')
            assert set(actual)=={r['id'] for r in data['rows'] if r['category']==category['id']},category['id']
        page.locator('#reset').click()
        # Combined verdict/category filters must exactly match the source predicate.
        for org,selector in [('TTA','#f-tta'),('SBTVD','#f-sbtvd')]:
            for code in data['verdicts']:
                page.locator(selector).select_option(code)
                actual=page.locator('tr.row').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)')
                assert set(actual)=={r['id'] for r in data['rows'] if r['verdicts'][org]['code']==code},(org,code)
            page.locator('#reset').click()
        # A raw-text highlight must not split an encoded HTML entity or inject markup.
        escaped=page.evaluate("() => { const a=window.COMPARISON_APP; a.state.q='amp'; const x=a.hl('& amp <tag>'); a.reset(); return x; }")
        assert escaped=='&amp; <mark>amp</mark> &lt;tag&gt;',escaped
        for width,height,theme in [(1440,1100,'light'),(1024,900,'light'),(390,844,'light'),(390,844,'dark')]:
            page.set_viewport_size({'width':width,'height':height});page.emulate_media(color_scheme=theme)
            page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(artifacts/f'overview-{width}-{theme}.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(width,theme,'page overflow')
            page.locator('#q').fill('currentUtcOffset');page.locator('.row-toggle').first.click()
            panel=page.locator('tr.detail:not([hidden]) .panel')
            assert panel.bounding_box()['width'] <= width, (width,'panel too wide')
            panel.locator('div').first.scroll_into_view_if_needed()
            page.screenshot(path=str(artifacts/f'signaling-{width}-{theme}.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(width,theme,'detail overflow')
            result['viewports'].append({'width':width,'theme':theme,'page_overflow':False})
            page.locator('#reset').click()
        # The downloadable single file must also work without companion assets.
        single=ROOT/'dist/atsc3-kr-us-br-reviewed.html'
        if single.exists():
            page.route('**/*',lambda route:route.abort() if route.request.url.startswith(('https://','http://')) else route.continue_())
            page.goto(single.as_uri(),wait_until='load');page.wait_for_function('Boolean(window.COMPARISON_APP)')
            assert page.locator('tr.row').count()==len(data['rows'])
            result['standalone']=True
        assert not result['errors'],result['errors']
        result['features_rendered']=len(feature_ids);result['browser']=browser.version
        browser.close()
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',action='store_true');parser.add_argument('--artifacts',type=Path,default=ROOT/'dist/qa')
    args=parser.parse_args();result={'data':check_data()}
    if args.browser:result['browser']=check_browser(args.artifacts)
    args.artifacts.mkdir(parents=True,exist_ok=True)
    (args.artifacts/'test-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result if not args.browser else {'data':result['data'],'rendered_rows':len(result['browser']['row_details']),'rendered_features':result['browser']['features_rendered'],'browser_errors':result['browser']['errors'],'viewports':result['browser']['viewports']},ensure_ascii=False,indent=2))
