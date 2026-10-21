(async function () {
  'use strict';
  let data = window.STANDARDS_DATA;
  if (!data) {
    try {
      const response = await fetch('data/standards.json');
      if (!response.ok) throw new Error('HTTP ' + response.status);
      data = await response.json();
    } catch (error) {
      document.querySelector('.sheet').insertAdjacentHTML('afterbegin', '<p role="alert">Comparison data could not be loaded. Keep index.html, app.js and the data folder together.</p>');
      return;
    }
  }
  const orgs = data.orgs, V = data.verdicts, titles = data.docTitles || {};
  const REL = data.relations || {}, CONF = data.confidence || {}, NK = data.noneKinds || {};
  const state = {cat: 'all', open: null, q: '', tta: 'all', sbtvd: 'all', conf: 'all', diff: false, unv: false};
  const byId = new Map(data.rows.map(row => [row.id, row]));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reEsc = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const baseId = value => value.replace(/:\d{4}-\d{2}$/, '');
  const titleOf = value => titles[baseId(value)];
  const safeUrl = value => /^(https?:\/\/|docs\/refs\/)/i.test(value || '') ? esc(value) : '';
  const link = (url, label) => safeUrl(url) ? '<a href="' + safeUrl(url) + '">' + esc(label) + '</a>' : esc(label);
  function hl(value) {
    const text = String(value ?? '');
    if (!state.q) return esc(text);
    const regex = new RegExp(reEsc(state.q), 'ig');
    let result = '', cursor = 0;
    for (const match of text.matchAll(regex)) {
      result += esc(text.slice(cursor, match.index)) + '<mark>' + esc(match[0]) + '</mark>';
      cursor = match.index + match[0].length;
    }
    return result + esc(text.slice(cursor));
  }
  function strings(value) {
    if (value == null) return [];
    if (typeof value === 'string' || typeof value === 'number') return [String(value)];
    if (Array.isArray(value)) return value.flatMap(strings);
    if (typeof value === 'object') return Object.values(value).flatMap(strings);
    return [];
  }
  function haystack(row) {
    const parts = strings(row);
    orgs.forEach(org => (row.cells[org.id]?.docs || []).forEach(doc => parts.push(...strings(titleOf(doc)))));
    return parts.join(' ').toLowerCase();
  }
  const searchable = new Map(data.rows.map(row => [row.id, haystack(row)]));
  function hasDifferences(row) {
    return ['TTA','SBTVD'].some(org => ['partial','diff'].includes(row.verdicts?.[org]?.code) ||
      (row.comparisons || []).some(feature => ['partial','diff'].includes(feature.verdicts?.[org]?.code)));
  }
  function hasUnverified(row) {
    return ['TTA','SBTVD'].some(org => {
      const cell = row.cells[org] || {}, verdict = row.verdicts?.[org] || {};
      return cell.flag || cell.unverified?.length || ['partial','metadata','unverified','inferred'].includes(cell.conf) ||
        verdict.code === 'review' || verdict.kind === 'pending' ||
        (row.comparisons || []).some(feature => {
          const c = feature.cells?.[org] || {}, v = feature.verdicts?.[org] || {};
          return c.flag || c.unverified?.length || ['partial','metadata','unverified','inferred'].includes(c.conf) || v.code === 'review';
        });
    });
  }
  function passes(row) {
    if (state.tta !== 'all' && row.verdicts?.TTA?.code !== state.tta) return false;
    if (state.sbtvd !== 'all' && row.verdicts?.SBTVD?.code !== state.sbtvd) return false;
    if (state.conf !== 'all' && !['TTA','SBTVD'].some(org => row.cells[org]?.conf === state.conf)) return false;
    if (state.diff && !hasDifferences(row)) return false;
    if (state.unv && !hasUnverified(row)) return false;
    return !state.q || searchable.get(row.id).includes(state.q);
  }
  function fill(id, values) {
    const select = document.getElementById(id);
    for (const [key, value] of Object.entries(values)) {
      const option = document.createElement('option');
      option.value = key; option.textContent = (value.icon ? value.icon + ' ' : '') + value.label;
      select.append(option);
    }
    return select;
  }
  const ftta = fill('f-tta', V), fsbtvd = fill('f-sbtvd', V), fconf = fill('f-conf', CONF);
  for (const [select,key] of [[ftta,'tta'],[fsbtvd,'sbtvd'],[fconf,'conf']]) select.addEventListener('change', () => {state[key] = select.value; render();});
  for (const [id,key] of [['f-diff','diff'],['f-unv','unv']]) document.getElementById(id).addEventListener('change', event => {state[key] = event.target.checked; render();});
  document.getElementById('q').addEventListener('input', event => {state.q = event.target.value.trim().toLowerCase(); render();});
  document.getElementById('reset').addEventListener('click', reset);
  function reset() {
    Object.assign(state, {cat:'all',open:null,q:'',tta:'all',sbtvd:'all',conf:'all',diff:false,unv:false});
    document.getElementById('q').value = ''; ftta.value = fsbtvd.value = fconf.value = 'all';
    document.getElementById('f-diff').checked = document.getElementById('f-unv').checked = false;
    render();
  }
  document.getElementById('title').textContent = data.meta.title;
  document.getElementById('subtitle').textContent = data.meta.subtitle || '';
  document.getElementById('purpose').textContent = data.meta.purpose;
  document.getElementById('meta').innerHTML = '<span><b>Scope</b> ' + esc(data.meta.scope) + '</span><span><b>Verified</b> ' + esc(data.meta.updated) + '</span>';
  document.getElementById('legend').innerHTML = Object.entries(V).map(([key,value]) => '<span class="v '+key+'"><span class="i">'+esc(value.icon)+'</span>'+esc(value.label)+'</span><span>'+esc(value.desc)+'</span>').join('');
  const legends = (values,label) => '<p class="legend2"><b>'+esc(label)+'</b> '+Object.values(values).map(value => '<span>'+esc(typeof value === 'string' ? value : value.label + (value.desc ? ': '+value.desc : ''))+'</span>').join(' ')+'</p>';
  document.getElementById('legend-extra').innerHTML = legends(NK,'Document status') + legends(REL,'Relation') + legends(CONF,'Verification scope');
  const baseline = data.baseline || {};
  document.getElementById('baseline-list').innerHTML = '<p>The current approved editions are the comparison baseline. A/300 fixed references and national incorporation dates can differ. National rules, normative standards and non-normative operational guidance are identified separately.</p><p>'+ (baseline.sources || []).map(source => link(source.url,source.label)).join(' · ')+'</p><div class="wrap"><table class="baseline-table"><thead><tr><th>ATSC document</th><th>Current edition</th><th>Type</th><th>Official document</th><th>SHA-256 (prefix)</th></tr></thead><tbody>'+ (baseline.documents || []).map(doc => '<tr><td>'+esc(doc.id)+'</td><td>'+esc(doc.edition)+'</td><td>'+esc(doc.kind)+'</td><td>'+link(doc.url,doc.title)+'</td><td><code title="'+esc(doc.sha256)+'">'+esc(doc.sha256?.slice(0,12))+'</code></td></tr>').join('')+'</tbody></table></div>';
  document.getElementById('baseline-count').textContent = (baseline.documents || []).length + ' approved ATSC documents · verified ' + (baseline.verified || data.meta.updated);
  document.getElementById('candidate-list').innerHTML = '<p>'+link(baseline.candidate_url,'Official Candidate Standards list')+'</p><ul>'+ (baseline.candidates || []).map(candidate => '<li><b>'+esc(candidate.id)+'</b> · '+esc(candidate.date)+' · candidate period to '+esc(candidate.expires)+'. '+esc(candidate.note)+'</li>').join('')+'</ul>';
  const regCard = regulation => {
    const dates = [['signed','Signed'],['published','Published'],['effective','Effective']].filter(([key]) => regulation[key]).map(([key,label]) => label+' '+regulation[key]);
    if (regulation.effective_rule) dates.push(regulation.effective_rule);
    return '<div class="reg-card" data-reg="'+esc(regulation.id)+'"><h4>'+esc(regulation.id)+'</h4><span class="t" lang="'+esc(regulation.title_lang || 'en')+'">'+esc(regulation.title)+'</span><span class="m">'+esc([regulation.issuer,...dates].filter(Boolean).join(' · '))+'</span><p>'+link(regulation.url,'Official source')+(regulation.local ? ' · '+link(regulation.local,'Local excerpt') : '')+'</p><p>'+esc(regulation.note)+'</p>'+ (regulation.unverified?.length ? '<p class="limits">'+esc(regulation.unverified.join(' '))+'</p>' : '')+'</div>';
  };
  document.getElementById('regs').innerHTML = orgs.map(org => {
    const regulations = (data.regulations || []).filter(reg => reg.org === org.id);
    return !regulations.length ? '' : '<div class="reg-country" style="--org:'+esc(org.color)+'"><h3>'+esc(regulations[0].country)+'</h3>'+regulations.map(regCard).join('')+'</div>';
  }).join('');
  const tabs = document.getElementById('tabs');
  function makeTab(id,label) {
    const button = document.createElement('button'); button.type = 'button';button.dataset.id = id;button.textContent = label;
    button.setAttribute('aria-controls','matrix-region');
    button.addEventListener('click', () => {state.cat=id;state.open=null;render();}); return button;
  }
  tabs.append(makeTab('all','All'));
  data.categories.forEach(category => tabs.append(makeTab(category.id,category.name)));
  function docHtml(doc) {
    const title = titleOf(doc), current = baseline.documents?.find(item => item.id === baseId(doc));
    const edition = /:(\d{4}-\d{2})$/.exec(doc)?.[1];
    const name = current && (!edition || edition === current.edition) ? link(current.url,doc) : hl(doc);
    return '<span class="d"><span class="n">'+name+'</span>'+(title ? '<span class="t" lang="'+esc(title.lang)+'">'+hl(title.title)+'</span>'+(title.lang !== 'en' && title.title_en ? '<span class="t en">'+hl(title.title_en)+'</span>' : '') : '')+'</span>';
  }
  function regulationHtml(cell,full) {
    return (cell?.reg || []).map(reg => '<span class="reg"><span class="l">Regulatory context</span>'+hl(reg.id)+' · '+hl(reg.ref)+(full ? '<span class="q">'+hl(reg.text)+'</span>' : '')+'</span>').join('');
  }
  function cellHtml(cell) {
    if (!cell) return '<span class="dash">—</span>';
    return (cell.docs || []).map(docHtml).join('')+(cell.note ? '<span class="note">'+hl(cell.note)+'</span>' : '')+regulationHtml(cell,false) || '<span class="dash">—</span>';
  }
  function verdictLabel(verdict) {
    if (verdict.code === 'none' && verdict.kind) return NK[verdict.kind] || V.none.label;
    return (V[verdict.code] || V.review).label;
  }
  function verdictHtml(verdict,cell={},reason=true) {
    verdict = verdict || {code:'review',text:'Comparison not established.'};
    const value = V[verdict.code] || V.review;
    const tags = [REL[cell.rel]?.label,CONF[cell.conf]?.label].filter(Boolean).join(' · ');
    return '<span class="v '+esc(verdict.code)+'"><span class="i">'+esc(value.icon)+'</span>'+esc(verdictLabel(verdict))+'</span>'+(tags ? '<span class="vk">'+esc(tags)+'</span>' : '')+(cell.flag ? '<span class="vk flag">'+esc(cell.flag)+'</span>' : '')+(reason && verdict.text ? '<span class="verdict-reason">'+hl(verdict.text)+'</span>' : '');
  }
  function evidenceHtml(evidence) {
    return !evidence?.length ? '<p class="history">No additional clause citation is recorded for this mapping.</p>' : '<ul class="evidence">'+evidence.map(item => '<li>'+esc([item.org,item.doc || item.label,item.clause].filter(Boolean).join(' · '))+(item.url ? ' · '+link(item.url,'Source') : '')+'</li>').join('')+'</ul>';
  }
  function detailHtml(row) {
    const columns = orgs.map(org => {
      const cell = row.cells[org.id] || {};
      return '<div><h4 style="--org:'+esc(org.color)+'"><span></span>'+esc(org.label)+'</h4>'+(cell.docs || []).map(docHtml).join('')+'<p>'+hl(cell.note || '')+'</p>'+regulationHtml(cell,true)+(cell.unverified?.length ? '<p class="limits">Verification scope: '+hl(cell.unverified.join(' '))+'</p>' : '')+'</div>';
    }).join('');
    const chapter = row.chapters;
    const chapters = !chapter?.rows?.length ? '' : '<div class="full"><h4>Chapter correspondence</h4><p class="history">Correspondence to a cited national edition is not a declaration of current-edition equivalence. '+esc((chapter.sources || []).join(' · '))+'</p><div class="wrap"><table class="cmp chap"><thead><tr><th>ATSC chapter</th><th>TTA chapter</th><th>Relation</th><th>SBTVD chapter</th><th>Relation</th><th>Scope and differences</th></tr></thead><tbody>'+chapter.rows.map(c => '<tr>'+[c.atsc,c.tta,c.tta_rel,c.sbtvd,c.sbtvd_rel,c.note].map(value => '<td>'+hl(value || '—')+'</td>').join('')+'</tr>').join('')+'</tbody></table></div></div>';
    const features = !(row.comparisons || []).length ? '' : '<div class="full"><h4>Feature comparison</h4><div class="wrap"><table class="cmp features"><thead><tr><th>Feature</th><th>ATSC current baseline</th><th>TTA</th><th>SBTVD Forum</th><th>Difference and impact</th><th>TTA vs ATSC</th><th>SBTVD vs ATSC</th><th>Reviewed</th></tr></thead><tbody>'+row.comparisons.map(feature => {
      const side = org => {const s=feature.sides?.[org];return !s ? '<span class="dash">Not established</span>' : '<b>'+hl(s.doc || '')+'</b><span class="t">'+hl([s.clause,s.table,s.page].filter(Boolean).join(' · '))+'</span><span class="val">'+hl(s.value || '')+'</span>'+(s.req ? '<span class="req">'+hl(s.req)+'</span>' : '');};
      return '<tr data-feature="'+esc(feature.id)+'"><td><b>'+hl(feature.feature)+'</b><span class="t">'+hl(feature.group || '')+'</span></td>'+['ATSC','TTA','SBTVD'].map(org => '<td>'+side(org)+'</td>').join('')+'<td>'+hl(feature.difference || '')+(feature.impact ? '<p class="t">Impact: '+hl(feature.impact)+'</p>' : '')+(feature.recommendation ? '<p class="t">Recommendation: '+hl(feature.recommendation)+'</p>' : '')+evidenceHtml(feature.evidence)+'</td>'+['TTA','SBTVD'].map(org => '<td>'+verdictHtml(feature.verdicts?.[org],feature.cells?.[org])+'</td>').join('')+'<td>'+esc(feature.reviewed?.date || '')+(feature.reviewed?.by ? '<br>'+esc(feature.reviewed.by) : '')+'</td></tr>';
    }).join('')+'</tbody></table></div></div>';
    return '<div class="panel"><div><h4>Comparison scope</h4><p>'+hl(row.summary)+'</p>'+['TTA','SBTVD'].map(org => '<h4>'+esc(org)+' vs ATSC</h4>'+verdictHtml(row.verdicts?.[org],row.cells[org])).join('')+'</div>'+columns+chapters+features+(row.impact ? '<div class="full"><h4>Impact</h4><p>'+hl(row.impact)+'</p></div>' : '')+(row.recommendation ? '<div class="full reco"><h4>Recommendation</h4><p>'+hl(row.recommendation)+'</p></div>' : '')+'<div class="full"><h4>Evidence and review</h4>'+evidenceHtml(row.evidence)+'<p class="history">'+esc(row.review?.status || 'Not reviewed')+' · '+esc(row.review?.by || '')+' · '+esc(row.review?.updated || '')+'</p>'+(row.review?.scope ? '<p class="history">'+esc(row.review.scope)+'</p>' : '')+'</div></div>';
  }
  function openRow(id,resetFilters=false) {
    if (resetFilters) {reset();state.cat=byId.get(id).category;}
    state.open = state.open === id && !resetFilters ? null : id; render(id);
    if (resetFilters) document.querySelector('tr.row[data-id="'+CSS.escape(id)+'"]')?.scrollIntoView({block:'start'});
  }
  function renderOverview() {
    document.getElementById('ov-legend').innerHTML = Object.entries(V).map(([key,value]) => '<span><i class="'+esc(key)+'"></i>'+esc(value.icon)+' '+esc(value.label)+'</span>').join('');
    document.getElementById('overview').innerHTML = data.categories.map(category => {
      const rows = data.rows.filter(row => row.category === category.id);
      if (!rows.length) return '';
      return '<div class="ov-block"><h3>'+esc(category.name)+'</h3><div class="wrap"><table class="ov"><thead><tr><th>Document</th><th class="c">TTA</th><th class="c">SBTVD Forum</th></tr></thead><tbody>'+rows.map(row => '<tr data-row="'+esc(row.id)+'"><td class="id"><b>'+esc(row.id)+'</b><span>'+esc(row.title)+'</span></td>'+['TTA','SBTVD'].map(org => '<td class="cell '+esc(row.verdicts[org].code)+'"><button type="button" data-open="'+esc(row.id)+'" aria-label="'+esc('Open '+row.id+', '+org+': '+verdictLabel(row.verdicts[org]))+'" title="'+esc(row.verdicts[org].text)+'">'+esc((V[row.verdicts[org].code] || V.review).icon)+' '+esc(verdictLabel(row.verdicts[org]))+'</button></td>').join('')+'</tr>').join('')+'</tbody></table></div></div>';
    }).join('');
    document.querySelectorAll('#overview [data-open]').forEach(button => button.addEventListener('click',() => openRow(button.dataset.open,true)));
  }
  function render(focusId) {
    tabs.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.id === state.cat)));
    // Verdicts are shown in the overview table and in each row's detail panel, not as matrix columns.
    document.querySelector('#matrix thead').innerHTML = '<tr><th>Document<small>ATSC current baseline</small></th>'+orgs.map(org => '<th class="org" style="--org:'+esc(org.color)+'">'+esc(org.label)+'<small>'+esc(org.sub)+'</small></th>').join('')+'</tr>';
    const cols = 1+orgs.length;
    let html='',shown=0,total=0;
    for (const category of data.categories) {
      if (state.cat !== 'all' && state.cat !== category.id) continue;
      const all = data.rows.filter(row => row.category === category.id);total+=all.length;
      const rows = all.filter(passes);shown+=rows.length;if(!rows.length)continue;
      html+='<tr class="group"><td colspan="'+cols+'">'+esc(category.name)+'<small>'+esc(category.desc)+'</small></td></tr>';
      for (const row of rows) {
        const index = data.rows.indexOf(row), open=state.open===row.id, detailId='detail-'+index;
        html+='<tr class="row" data-id="'+esc(row.id)+'" aria-expanded="'+open+'"><td class="doc"><button type="button" class="row-toggle" data-row="'+esc(row.id)+'" aria-expanded="'+open+'" aria-controls="'+detailId+'"><span aria-hidden="true">'+(open?'−':'+')+'</span> '+hl(row.id)+'</button>'+(row.type==='RP'?'<span class="type">RP</span>':'')+'<span class="title">'+hl(row.title)+'</span></td>'+orgs.map(org=>'<td class="org" data-col="'+esc(org.label)+'">'+cellHtml(row.cells[org.id])+'</td>').join('')+'</tr>';
        html+='<tr class="detail" id="'+detailId+'" data-row="'+esc(row.id)+'"'+(open?'':' hidden')+'><td colspan="'+cols+'">'+(open?detailHtml(row):'')+'</td></tr>';
      }
    }
    document.querySelector('#matrix tbody').innerHTML = html || '<tr><td colspan="'+cols+'">No documents match these filters.</td></tr>';
    document.getElementById('count').textContent = shown+' of '+total+' documents';
    document.querySelectorAll('.row-toggle').forEach(button=>button.addEventListener('click',()=>openRow(button.dataset.row)));
    document.querySelectorAll('tr.row').forEach(row=>row.addEventListener('click',event=>{if(!event.target.closest('a,button,input,select')&&!String(window.getSelection()||'').trim())openRow(row.dataset.id);}));
    if(focusId)document.querySelector('.row-toggle[data-row="'+CSS.escape(focusId)+'"]')?.focus({preventScroll:true});
    window.DASHBOARD_NOTES?.refresh();
  }
  renderOverview();render();
  // Pure selectors/renderers are exported for reproducible local regression checks.
  window.COMPARISON_APP = {state,passes,hasDifferences,hasUnverified,haystack,detailHtml,hl,render,openRow,reset,data};
  document.dispatchEvent(new CustomEvent('comparison:ready'));
})();
