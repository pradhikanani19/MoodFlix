// TOAST
function showToast(msg, duration=2800) {
  const c = document.getElementById('toasts');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transition='opacity 0.3s'; setTimeout(()=>t.remove(),300); }, duration);
}

// CARD HTML — single clean definition
function cardHTML(item) {
  const poster = item.poster_path || null;
  const year = (item.release_date||'').slice(0,4);
  const genres = (item.genre_names||[]).slice(0,2).map(g=>`<span class="gbadge">${g}</span>`).join('');
  const mt = item.media_type || 'movie';
  const safeTitle = (item.title||'').replace(/'/g,"&#39;").replace(/"/g,'&quot;');
  // Store item as JSON in a script tag approach — avoids attribute escaping issues
  const itemId = 'item_' + item.tmdb_id + '_' + Math.random().toString(36).slice(2,6);
  // Use data attributes safely
  const safeItem = encodeURIComponent(JSON.stringify(item));
  return `
  <div class="card" onclick="go('${mt}',${item.tmdb_id})">
    <div class="card-img">
      ${poster?`<img src="${poster}" alt="${safeTitle}" loading="lazy">`:'<div class="card-fb">🎬</div>'}
      <div class="card-ov">
        <button onclick="event.stopPropagation();wlEncoded(this)" data-enc="${safeItem}">+ Watchlist</button>
      </div>
    </div>
    <div class="card-body">
      <div class="ctitle">${safeTitle}</div>
      <div class="cmeta">
        <span class="crat">⭐${item.vote_average}</span>
        <span class="clang">${(item.original_language||'').toUpperCase()}</span>
        ${year?`<span style="font-size:11px;color:var(--t3)">${year}</span>`:''}
      </div>
      <div class="cgenres">${genres}</div>
    </div>
  </div>`;
}

function wlEncoded(btn) {
  try {
    const item = JSON.parse(decodeURIComponent(btn.dataset.enc));
    wl(item);
  } catch(e) { showToast('Error adding to watchlist'); }
}

// Keep old wlFromBtn for backward compatibility
function wlFromBtn(btn) {
  try {
    const item = JSON.parse(btn.dataset.item);
    wl(item);
  } catch(e) { showToast('Error adding to watchlist'); }
}

// NAVIGATE
function go(mediaType, tmdbId) {
  window.location.href = `/${mediaType}/${tmdbId}`;
}

// ADD TO WATCHLIST
async function wl(item) {
  try {
    let poster = item.poster_path || null;
    if (poster && poster.startsWith('http')) {
      const m = poster.match(/\/[^\/]+\.[a-z]+$/i);
      poster = m ? m[0] : null;
    }
    const res = await fetch('/api/watchlist', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        tmdb_id: item.tmdb_id,
        media_type: item.media_type || 'movie',
        title: item.title,
        poster_path: poster,
        genre_ids: item.genre_ids || [],
        overview: item.overview || '',
        vote_average: item.vote_average || 0,
        release_date: item.release_date || '',
        original_language: item.original_language || ''
      })
    });
    const data = await res.json();
    if (res.ok) showToast(`✨ Added "${item.title}"`);
    else showToast(data.error === 'Already in watchlist' ? '📋 Already in watchlist' : '❌ '+(data.error||'Error'));
  } catch(e) { showToast('❌ Error adding to watchlist'); }
}

// REMOVE FROM WATCHLIST
async function removeFromWatchlist(tmdbId) {
  try {
    await fetch(`/api/watchlist/${tmdbId}`, {method:'DELETE'});
    showToast('Removed from watchlist');
    const el = document.getElementById('wli-'+tmdbId);
    if (el) { el.style.opacity='0'; el.style.transition='opacity 0.3s'; setTimeout(()=>el.remove(),300); }
    else setTimeout(()=>location.reload(),800);
  } catch(e) { showToast('❌ Error'); }
}

// MARK WATCHED
async function markWatched(tmdbId) {
  const ta = document.querySelector(`.wl-rev[data-id="${tmdbId}"]`);
  const review = ta ? ta.value : '';
  try {
    await fetch(`/api/watchlist/${tmdbId}/watched`, {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({watched:true, review})
    });
    showToast('✅ Marked as watched!');
    setTimeout(()=>location.reload(),900);
  } catch(e) { showToast('❌ Error'); }
}

// SURPRISE ME
async function surpriseMe() {
  try {
    showToast('🎲 Finding a surprise...');
    const data = await (await fetch('/api/recommend/surprise')).json();
    if (data.item) {
      showToast(`🎬 How about: ${data.item.title}?`);
      setTimeout(()=>go(data.item.media_type||'movie', data.item.tmdb_id), 1500);
    } else {
      showToast('Set your TMDB API key first!');
    }
  } catch(e) { showToast('❌ Error'); }
}

// GLOBAL SEARCH
const gs = document.getElementById('globalSearch');
const sd = document.getElementById('searchDropdown');
let st;
if (gs) {
  gs.addEventListener('input', () => {
    clearTimeout(st);
    const q = gs.value.trim();
    if (!q) { sd.classList.remove('show'); sd.innerHTML=''; return; }
    st = setTimeout(() => doGlobalSearch(q), 350);
  });
  document.addEventListener('click', e => {
    if (!gs.contains(e.target)) sd.classList.remove('show');
  });
}

async function doGlobalSearch(q) {
  try {
    const data = await (await fetch(`/api/search?q=${encodeURIComponent(q)}`)).json();
    if (!data.length) {
      sd.innerHTML='<div class="sri" style="color:var(--t3)">No results found</div>';
      sd.classList.add('show'); return;
    }
    sd.innerHTML = data.slice(0,7).map(r=>`
      <a class="sri" href="/${r.media_type}/${r.tmdb_id}">
        ${r.poster_path?`<img src="${r.poster_path}" alt="${r.title}">`:'<div class="sri-fb">🎬</div>'}
        <div>
          <div class="sri-title">${r.title}</div>
          <div class="sri-meta">⭐${r.vote_average} · ${(r.original_language||'').toUpperCase()} · ${r.media_type}</div>
        </div>
      </a>`).join('');
    sd.classList.add('show');
  } catch(e) {}
}