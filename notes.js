/* Review notes: select text on the page and attach a note to it.
   Notes are stored only in this browser (localStorage) and can be exported or imported as files.
   Highlights are re-anchored after every render by quote text plus surrounding context, so they
   survive filtering, row toggling and page reloads. */
(function () {
  'use strict';
  const KEY = 'atsc3-kr-us-br-dashboard/notes/v1', MODE_KEY = KEY + '/mode', NAME_KEY = KEY + '/reviewer';
  const CTX = 40, MAX_QUOTE = 2000, SKIP = '.memo-ui, script, style, select, option, textarea';
  let app = null, notes = [], storageOk = true, mode = false, pending = null, editing = null, shown = new Set();
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clip = (text, n) => text.length > n ? text.slice(0, n - 1) + '…' : text;
  const flat = text => String(text || '').replace(/\s+/g, ' ').trim();
  const pad = n => String(n).padStart(2, '0');
  const stamp = iso => { const d = new Date(iso); return isNaN(d) ? '' : d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+' '+pad(d.getHours())+':'+pad(d.getMinutes()); };
  const valid = note => note && typeof note.id === 'string' && typeof note.quote === 'string' && note.anchor && typeof note.anchor === 'object';

  // ---------- storage (every access guarded: private windows and blocked site data throw)
  function readStore(key) { try { return localStorage.getItem(key); } catch (error) { storageOk = false; return null; } }
  function writeStore(key, value) { try { localStorage.setItem(key, value); return true; } catch (error) { storageOk = false; return false; } }
  function load() {
    try { const parsed = JSON.parse(readStore(KEY) || '{}'); notes = Array.isArray(parsed.notes) ? parsed.notes.filter(valid) : []; }
    catch (error) { notes = []; }
  }
  const persist = () => writeStore(KEY, JSON.stringify({version: 1, notes}));

  // ---------- where a selection sits, and how to find that place again
  function colOf(el) {
    const cell = el.closest('td, th');
    if (!cell) return '';
    if (cell.dataset.col) return cell.dataset.col;
    const head = cell.closest('table')?.tHead?.rows[0], th = head && head.cells[cell.cellIndex];
    return th ? flat(th.firstChild?.textContent || th.textContent) : '';
  }
  function headingIn(el) {
    const block = el.closest('.panel > div');
    let found = '';
    if (block) for (const h of block.querySelectorAll('h4')) if (h.contains(el) || (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) found = flat(h.textContent);
    return found;
  }
  function anchorFor(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    const feature = el.closest('[data-feature]'), detail = el.closest('tr.detail[data-row]'), row = el.closest('tr.row[data-id]');
    const ov = el.closest('#overview tr[data-row]'), reg = el.closest('.reg-card[data-reg]');
    if (feature && detail) return {scope: 'feature', rowId: detail.dataset.row, featureId: feature.dataset.feature, col: colOf(el)};
    if (detail) return {scope: 'detail', rowId: detail.dataset.row, col: [headingIn(el), el.closest('table.cmp') ? colOf(el) : ''].filter(Boolean).join(' · ')};
    if (row) return {scope: 'row', rowId: row.dataset.id, col: colOf(el)};
    if (ov) return {scope: 'overview', rowId: ov.dataset.row, col: colOf(el)};
    if (reg) return {scope: 'reg', regId: reg.dataset.reg};
    const section = el.closest('section, header, footer');
    return {scope: 'page', section: flat(section?.querySelector('h2')?.textContent) || (section?.tagName === 'HEADER' ? 'Header' : section?.tagName === 'FOOTER' ? 'Footer' : 'Page')};
  }
  function scopeEl(a) {
    const q = selector => document.querySelector(selector), v = value => CSS.escape(value || '');
    switch (a.scope) {
      case 'feature': return q('tr.detail[data-row="'+v(a.rowId)+'"]:not([hidden]) [data-feature="'+v(a.featureId)+'"]');
      case 'detail': return q('tr.detail[data-row="'+v(a.rowId)+'"]:not([hidden])');
      case 'row': return q('tr.row[data-id="'+v(a.rowId)+'"]');
      case 'overview': return q('#overview tr[data-row="'+v(a.rowId)+'"]');
      case 'reg': return q('.reg-card[data-reg="'+v(a.regId)+'"]');
      default: return q('.sheet');
    }
  }
  function groupOf(a) {
    if (a.rowId) { const row = app.data.rows.find(r => r.id === a.rowId); return a.rowId + (row ? ' — ' + row.title : ''); }
    return a.scope === 'reg' ? 'Regulatory technical standards' : (a.section || 'Page');
  }
  function whereOf(a) {
    const feature = a.featureId && app.data.comparisons.find(f => f.id === a.featureId);
    const parts = {feature: ['Feature “' + (feature ? feature.feature : a.featureId) + '”', a.col], detail: ['Details', a.col], row: ['Table', a.col],
      overview: ['At a glance', a.col], reg: [a.regId]}[a.scope] || [];
    return parts.filter(Boolean).join(' · ');
  }
  const describe = a => [groupOf(a), whereOf(a)].filter(Boolean).join(' · ');

  // ---------- text index of a scope element (memo UI, form controls and scripts excluded)
  function textIndex(root) {
    const nodes = [];
    let text = '', node;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n => n.parentElement?.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
    while ((node = walker.nextNode())) { nodes.push({node, start: text.length}); text += node.nodeValue; }
    return {text, nodes};
  }
  function offsetOf(index, container, offset) {
    if (container.nodeType === 3) {
      const item = index.nodes.find(n => n.node === container);
      if (item) return item.start + Math.min(offset, container.nodeValue.length);
    }
    const point = document.createRange();
    point.setStart(container, offset);
    for (const item of index.nodes) if (point.comparePoint(item.node, 0) >= 0) return item.start;
    return index.text.length;
  }
  function capture() {
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount || selection.isCollapsed) return null;
    const range = selection.getRangeAt(0), sheet = document.querySelector('.sheet');
    if (!sheet || !sheet.contains(range.commonAncestorContainer)) return null;
    let anchor = anchorFor(range.commonAncestorContainer), root = scopeEl(anchor);
    if (!root || !root.contains(range.commonAncestorContainer)) { anchor = anchorFor(sheet); anchor.scope = 'page'; root = sheet; }
    const index = textIndex(root);
    const start = offsetOf(index, range.startContainer, range.startOffset), end = offsetOf(index, range.endContainer, range.endOffset);
    const quote = index.text.slice(start, end);
    if (!quote.trim()) return null;
    return {anchor, quote: quote.slice(0, MAX_QUOTE), prefix: index.text.slice(Math.max(0, start - CTX), start),
      suffix: index.text.slice(start + Math.min(quote.length, MAX_QUOTE), start + Math.min(quote.length, MAX_QUOTE) + CTX), rect: range.getBoundingClientRect()};
  }
  function locate(note) {
    const root = scopeEl(note.anchor);
    if (!root || !note.quote) return null;
    const index = textIndex(root), q = note.quote;
    let best = -1, bestScore = -1, at = index.text.indexOf(q);
    while (at !== -1) {
      const before = index.text.slice(Math.max(0, at - CTX), at), after = index.text.slice(at + q.length, at + q.length + CTX);
      let score = 0;
      for (let i = 1; i <= Math.min(before.length, (note.prefix || '').length) && before[before.length - i] === note.prefix[note.prefix.length - i]; i++) score++;
      for (let i = 0; i < Math.min(after.length, (note.suffix || '').length) && after[i] === note.suffix[i]; i++) score++;
      if (score > bestScore) { best = at; bestScore = score; }
      at = index.text.indexOf(q, at + 1);
    }
    return best < 0 ? null : {index, start: best, end: best + q.length};
  }
  function wrap(loc, note) {
    for (const item of loc.index.nodes) {
      const s = Math.max(loc.start, item.start), e = Math.min(loc.end, item.start + item.node.nodeValue.length);
      if (s >= e) continue;
      let node = item.node;
      if (e - item.start < node.nodeValue.length) node.splitText(e - item.start);
      if (s > item.start) node = node.splitText(s - item.start);
      const mark = document.createElement('mark');
      mark.className = 'memo-hl' + (note.status === 'done' ? ' done' : '');
      mark.dataset.note = note.id;
      mark.title = note.text || 'Note';
      node.parentNode.replaceChild(mark, node);
      mark.appendChild(node);
    }
  }
  function clearMarks() {
    document.querySelectorAll('mark.memo-hl').forEach(mark => {
      const parent = mark.parentNode;
      while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
      parent.removeChild(mark);
      parent.normalize();
    });
    document.querySelectorAll('.memo-count').forEach(badge => badge.remove());
  }
  function refresh() {
    if (!app) return;
    clearMarks();
    shown = new Set();
    for (const note of notes) { const loc = locate(note); if (loc) { wrap(loc, note); shown.add(note.id); } }
    const perRow = new Map();
    notes.forEach(note => note.anchor.rowId && perRow.set(note.anchor.rowId, (perRow.get(note.anchor.rowId) || 0) + 1));
    const badge = (id, n) => '<button type="button" class="memo-count memo-ui" data-row="'+esc(id)+'" title="'+n+' note'+(n > 1 ? 's' : '')+'">✎ '+n+'</button>';
    document.querySelectorAll('tr.row[data-id]').forEach(tr => { const n = perRow.get(tr.dataset.id); if (n) tr.querySelector('td.doc')?.insertAdjacentHTML('beforeend', badge(tr.dataset.id, n)); });
    document.querySelectorAll('#overview tr[data-row]').forEach(tr => { const n = perRow.get(tr.dataset.row); if (n) tr.querySelector('td.id')?.insertAdjacentHTML('beforeend', badge(tr.dataset.row, n)); });
    renderPanel();
  }

  // ---------- user interface
  const ui = document.createElement('div');
  ui.className = 'memo-ui';
  ui.innerHTML = '<button type="button" class="memo-add" hidden>✎ Add note</button>'+
    '<div class="memo-pop" role="dialog" aria-label="Note" hidden><p class="memo-ctx"></p><blockquote class="memo-quote"></blockquote>'+
    '<textarea rows="4" placeholder="What needs to change? (Ctrl+Enter to save)"></textarea>'+
    '<div class="memo-actions"><label class="memo-donewrap"><input type="checkbox" class="memo-done"> Done</label><span class="grow"></span>'+
    '<button type="button" class="memo-del">Delete</button><button type="button" class="memo-cancel">Cancel</button><button type="button" class="memo-save">Save</button></div></div>'+
    '<div class="memo-bar"><button type="button" class="memo-mode" aria-pressed="false" title="When on, select text to add a note">✎ Memo off</button>'+
    '<button type="button" class="memo-open" aria-expanded="false">Notes <b class="memo-n">0</b></button></div>'+
    '<aside class="memo-panel" aria-label="Review notes" hidden><div class="memo-head"><b>Review notes</b><button type="button" class="memo-close" aria-label="Close">×</button></div>'+
    '<p class="memo-help">Turn on Memo, select text on the page, then choose “Add note”. Notes are saved only in this browser; export them to keep or share.</p>'+
    '<label class="memo-name">Reviewer <input type="text" maxlength="60" autocomplete="name"></label>'+
    '<div class="memo-tools"><button type="button" data-act="md">Export .md</button><button type="button" data-act="json">Export .json</button>'+
    '<button type="button" data-act="copy">Copy text</button><button type="button" data-act="import">Import .json</button><button type="button" data-act="clear">Delete all</button>'+
    '<input type="file" accept=".json,application/json" hidden></div><p class="memo-warn" hidden></p><textarea class="memo-copybox" rows="6" readonly hidden></textarea>'+
    '<ol class="memo-items"></ol></aside>';
  const $ = selector => ui.querySelector(selector);
  const addBtn = $('.memo-add'), pop = $('.memo-pop'), textarea = $('.memo-pop textarea'), doneBox = $('.memo-done'), modeBtn = $('.memo-mode');
  const panel = $('.memo-panel'), openBtn = $('.memo-open'), list = $('.memo-items'), nameInput = $('.memo-name input'), fileInput = $('.memo-tools input[type=file]');

  function place(el, rect) {
    if (!rect) return;
    const width = el.offsetWidth || 360, height = el.offsetHeight || 40;
    let top = rect.bottom + 6;
    if (top + height > innerHeight - 8 && rect.top - height - 6 > 8) top = rect.top - height - 6;
    el.style.left = (Math.min(Math.max(8, rect.left), innerWidth - width - 8) + scrollX) + 'px';
    el.style.top = (top + scrollY) + 'px';
  }
  function offer() {
    if (!mode || !pop.hidden) { addBtn.hidden = true; return; }
    pending = capture();
    addBtn.hidden = !pending;
    if (pending) place(addBtn, pending.rect);
  }
  function openEditor(note, rect) {
    editing = note || null;
    const source = note || pending;
    if (!source) return;
    $('.memo-ctx').textContent = describe(source.anchor);
    $('.memo-quote').textContent = clip(flat(source.quote), 400);
    textarea.value = note ? note.text : '';
    doneBox.checked = !!note && note.status === 'done';
    $('.memo-donewrap').hidden = $('.memo-del').hidden = !note;
    addBtn.hidden = true;
    pop.hidden = false;
    place(pop, rect || source.rect);
    textarea.focus();
  }
  function closeEditor() { pop.hidden = true; editing = null; }
  function saveEditor() {
    const text = textarea.value.trim(), now = new Date().toISOString();
    if (editing) Object.assign(editing, {text, status: doneBox.checked ? 'done' : 'open', updated: now});
    else if (pending && text) notes.push({id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7), created: now, updated: now,
      author: nameInput.value.trim(), dataVersion: app.data.meta.updated, anchor: pending.anchor, quote: pending.quote,
      prefix: pending.prefix, suffix: pending.suffix, text, status: 'open'});
    persist();
    closeEditor();
    pending = null;
    window.getSelection()?.removeAllRanges();
    refresh();
  }
  function remove(id) {
    notes = notes.filter(note => note.id !== id);
    persist();
    closeEditor();
    refresh();
  }
  function setMode(on) {
    mode = !!on;
    writeStore(MODE_KEY, mode ? 'on' : 'off');
    modeBtn.setAttribute('aria-pressed', String(mode));
    modeBtn.textContent = mode ? '✎ Memo on' : '✎ Memo off';
    document.body.classList.toggle('memo-on', mode);
    if (!mode) addBtn.hidden = true;
  }
  function openPanel(rowId) {
    panel.hidden = false;
    openBtn.setAttribute('aria-expanded', 'true');
    renderPanel();
    if (rowId) list.querySelector('[data-row="'+CSS.escape(rowId)+'"]')?.scrollIntoView({block: 'start'});
  }
  function sorted() {
    const order = new Map(app.data.rows.map((row, index) => [row.id, index]));
    return [...notes].sort((a, b) => (order.get(a.anchor.rowId) ?? 1e6) - (order.get(b.anchor.rowId) ?? 1e6) || String(a.created).localeCompare(String(b.created)));
  }
  function renderPanel() {
    $('.memo-n').textContent = notes.length;
    const warn = $('.memo-warn');
    warn.hidden = storageOk;
    warn.textContent = 'This browser is not saving notes (site storage is blocked). Export them before closing the page.';
    if (panel.hidden) return;
    let group = null;
    list.innerHTML = notes.length ? sorted().map(note => {
      const g = groupOf(note.anchor), head = g !== group ? '<li class="memo-group" data-row="'+esc(note.anchor.rowId || '')+'">'+esc(g)+'</li>' : '';
      group = g;
      return head + '<li class="memo-item'+(note.status === 'done' ? ' done' : '')+'" data-id="'+esc(note.id)+'"><div class="memo-item-ctx">'+esc(whereOf(note.anchor) || 'Text')+'</div>'+
        '<blockquote>'+esc(clip(flat(note.quote), 240))+'</blockquote><p>'+esc(note.text || '(no text)')+'</p>'+
        '<div class="memo-item-meta">'+esc([note.author, stamp(note.updated)].filter(Boolean).join(' · '))+(shown.has(note.id) ? '' : ' · <span class="memo-off">not on screen — use Show</span>')+'</div>'+
        '<div class="memo-item-acts"><label><input type="checkbox" data-act="done"'+(note.status === 'done' ? ' checked' : '')+'> Done</label>'+
        '<button type="button" data-act="go">Show</button><button type="button" data-act="edit">Edit</button><button type="button" data-act="delete">Delete</button></div></li>';
    }).join('') : '<li class="memo-empty">No notes yet.</li>';
  }
  function show(note) {
    const selector = 'mark.memo-hl[data-note="'+CSS.escape(note.id)+'"]', a = note.anchor;
    // Detail/feature notes need their row open; any row note that is filtered out needs the filters reset.
    if (a.rowId && ((['detail', 'feature'].includes(a.scope) && app.state.open !== a.rowId) || !document.querySelector(selector))) app.openRow(a.rowId, true);
    const mark = document.querySelector(selector);
    if (!mark) { alert('This note’s text was not found on the page. The content may have changed since the note was made.'); return; }
    if (innerWidth < 900) { panel.hidden = true; openBtn.setAttribute('aria-expanded', 'false'); }
    mark.scrollIntoView({block: 'center', inline: 'nearest'});
    document.querySelectorAll('mark.memo-hl[data-note="'+CSS.escape(note.id)+'"]').forEach(m => { m.classList.add('flash'); setTimeout(() => m.classList.remove('flash'), 1600); });
  }

  // ---------- export / import
  function exportJSON() {
    return JSON.stringify({version: 1, title: app.data.meta.title, dataVersion: app.data.meta.updated, page: location.origin + location.pathname, exported: new Date().toISOString(), notes}, null, 2);
  }
  function exportMarkdown() {
    const done = notes.filter(note => note.status === 'done').length;
    const lines = ['# Review notes — ' + app.data.meta.title, '', '- Data version: ' + app.data.meta.updated, '- Exported: ' + stamp(new Date().toISOString()),
      '- Notes: ' + notes.length + ' (open ' + (notes.length - done) + ', done ' + done + ')', '- Page: ' + location.origin + location.pathname, ''];
    let group = null, n = 0;
    for (const note of sorted()) {
      const g = groupOf(note.anchor);
      if (g !== group) { lines.push('## ' + g, ''); group = g; }
      lines.push((++n) + '. ' + (note.status === 'done' ? '[x] ' : '[ ] ') + '**' + (whereOf(note.anchor) || 'Text') + '**' + (note.author ? ' — ' + note.author : '') + ' (' + stamp(note.updated) + ')');
      lines.push('   > ' + flat(note.quote));
      lines.push('', '   ' + (note.text || '(no text)').replace(/\n/g, '\n   '), '');
    }
    return lines.join('\n') + '\n';
  }
  function importJSON(text) {
    const parsed = JSON.parse(text), incoming = (Array.isArray(parsed) ? parsed : parsed.notes || []).filter(valid);
    let added = 0, updated = 0;
    for (const note of incoming) {
      const existing = notes.find(n => n.id === note.id);
      if (!existing) { notes.push(note); added++; }
      else if (String(note.updated || '') > String(existing.updated || '')) { Object.assign(existing, note); updated++; }
    }
    persist();
    refresh();
    return {added, updated};
  }
  function download(name, text, type) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], {type}));
    a.download = name;
    document.body.append(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  const fileStamp = () => { const d = new Date(); return d.getFullYear()+pad(d.getMonth()+1)+pad(d.getDate())+'-'+pad(d.getHours())+pad(d.getMinutes()); };

  // ---------- events
  let timer = 0;
  document.addEventListener('selectionchange', () => { clearTimeout(timer); timer = setTimeout(offer, 180); });
  addBtn.addEventListener('mousedown', event => event.preventDefault());   // keep the page selection while clicking
  addBtn.addEventListener('click', () => openEditor(null));
  $('.memo-save').addEventListener('click', saveEditor);
  $('.memo-cancel').addEventListener('click', closeEditor);
  $('.memo-del').addEventListener('click', () => { if (editing && confirm('Delete this note?')) remove(editing.id); });
  textarea.addEventListener('keydown', event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) saveEditor(); });
  modeBtn.addEventListener('click', () => setMode(!mode));
  openBtn.addEventListener('click', () => panel.hidden ? openPanel() : (panel.hidden = true, openBtn.setAttribute('aria-expanded', 'false')));
  $('.memo-close').addEventListener('click', () => { panel.hidden = true; openBtn.setAttribute('aria-expanded', 'false'); });
  nameInput.addEventListener('change', () => writeStore(NAME_KEY, nameInput.value.trim()));
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (!pop.hidden) { if (editing || !textarea.value.trim() || confirm('Discard this note?')) closeEditor(); }
    else if (!panel.hidden) { panel.hidden = true; openBtn.setAttribute('aria-expanded', 'false'); }
  });
  // Clicking a highlight opens its note; capture phase so the row underneath does not toggle. Ctrl/⌘-click keeps link behaviour.
  document.addEventListener('click', event => {
    const badge = event.target.closest?.('button.memo-count');
    if (badge) { event.stopPropagation(); openPanel(badge.dataset.row); return; }
    const mark = event.target.closest?.('mark.memo-hl');
    if (!mark || event.ctrlKey || event.metaKey || String(window.getSelection() || '').trim()) return;
    event.preventDefault();
    event.stopPropagation();
    const note = notes.find(n => n.id === mark.dataset.note);
    if (note) openEditor(note, mark.getBoundingClientRect());
  }, true);
  list.addEventListener('click', event => {
    const act = event.target.dataset?.act, item = event.target.closest('.memo-item'), note = item && notes.find(n => n.id === item.dataset.id);
    if (!act || !note) return;
    if (act === 'done') { note.status = event.target.checked ? 'done' : 'open'; note.updated = new Date().toISOString(); persist(); refresh(); }
    else if (act === 'go') show(note);
    else if (act === 'edit') { show(note); const mark = document.querySelector('mark.memo-hl[data-note="'+CSS.escape(note.id)+'"]'); openEditor(note, mark ? mark.getBoundingClientRect() : {left: 16, bottom: 80, top: 80}); }
    else if (act === 'delete' && confirm('Delete this note?')) remove(note.id);
  });
  $('.memo-tools').addEventListener('click', event => {
    const act = event.target.dataset?.act;
    if (act === 'md') download('atsc3-review-notes-' + fileStamp() + '.md', exportMarkdown(), 'text/markdown;charset=utf-8');
    else if (act === 'json') download('atsc3-review-notes-' + fileStamp() + '.json', exportJSON(), 'application/json');
    else if (act === 'copy') {
      const text = exportMarkdown(), box = $('.memo-copybox');
      const fallback = () => { box.hidden = false; box.value = text; box.select(); };
      if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(() => alert('Copied ' + notes.length + ' notes as text.'), fallback); else fallback();
    }
    else if (act === 'import') fileInput.click();
    else if (act === 'clear' && notes.length && confirm('Delete all ' + notes.length + ' notes saved in this browser?')) { notes = []; persist(); refresh(); }
  });
  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;
    file.text().then(text => { const r = importJSON(text); alert('Imported: ' + r.added + ' new, ' + r.updated + ' updated.'); })
      .catch(() => alert('This file could not be read as exported notes (.json).')).finally(() => { fileInput.value = ''; });
  });

  function init() {
    app = window.COMPARISON_APP;
    if (!app) return;
    document.body.append(ui);
    load();
    nameInput.value = readStore(NAME_KEY) || '';
    setMode(readStore(MODE_KEY) === 'on');
    window.DASHBOARD_NOTES = {refresh, list: () => notes.slice(), exportJSON, exportMarkdown, importJSON, setMode, capture, openEditor, saveEditor};
    refresh();
  }
  if (window.COMPARISON_APP) init(); else document.addEventListener('comparison:ready', init, {once: true});
})();
