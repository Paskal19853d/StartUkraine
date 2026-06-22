function _validateDates() {
  const today = new Date().toISOString().slice(0, 10);
  const bEl = document.getElementById('e-birth');
  const dEl = document.getElementById('e-death');
  if (!bEl || !dEl) return;
  const b = bEl.value, d = dEl.value;
  bEl.max = d || today;
  dEl.min = b || '1900-01-01';
  dEl.max = today;
}

let _BANNED_WORDS = [];
async function _loadBannedWords() {
  try {
    const r = await fetch(`${API}/api/admin/chat/banned-words`, { headers: authH() });
    if (r.ok) { const d = await r.json(); _BANNED_WORDS = (d.words||[]).map(w => w.word.toLowerCase()); }
  } catch {}
}
function _checkNameBadWords(val) {
  const v = (val||'').toLowerCase();
  return _BANNED_WORDS.some(w => w && v.includes(w));
}

async function unapproveMem(id) {
  if (!confirm('Відправити запис на модерацію?')) return;
  try {
    const r = await fetch(`${API}/api/admin/unapprove/${id}`, { method: 'POST', headers: authH() });
    if (!r.ok) throw new Error(r.status);
    const idx = allPeople.findIndex(x => x.id === id);
    if (idx >= 0) allPeople[idx].approved = 0;
    _memApplyFilter(_memSearchQ);
    showN('Відправлено на модерацію');
    loadStats();
  } catch { showN('Помилка відправки на модерацію', true); }
}
