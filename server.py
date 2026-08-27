#!/usr/bin/env python3
import os

from flask import Flask, jsonify, request, render_template_string

import staleness

app = Flask(__name__)

PER_PAGE = 100


def _int_or(v, default):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _sort_key_fn(sort_key: str):
    def key(r):
        v = r.get(sort_key)
        if v is None:
            return float("inf") if sort_key == "days_since" else ""
        if isinstance(v, str):
            return v.lower()
        return v
    return key


def _apply_query(rows, args, sortable_fields, default_sort="days_since"):
    genre = (args.get("genre") or "").strip().lower()
    label = (args.get("label") or "").strip().lower()
    artist = (args.get("artist") or "").strip().lower()
    album = (args.get("album") or "").strip().lower()
    never = args.get("never_listened")
    qbittorrent = args.get("qbittorrent")

    filtered = rows
    if genre:
        filtered = [r for r in filtered if genre in (r.get("genre") or "").lower()]
    if label:
        filtered = [r for r in filtered if label in (r.get("label") or "").lower()]
    if artist:
        filtered = [r for r in filtered if artist in (r.get("artist") or "").lower()]
    if album:
        filtered = [r for r in filtered if album in (r.get("album") or "").lower()]
    if never == "yes":
        filtered = [r for r in filtered if r["days_since"] is None]
    elif never == "no":
        filtered = [r for r in filtered if r["days_since"] is not None]
    if qbittorrent == "yes":
        filtered = [r for r in filtered if r.get("in_qbittorrent")]
    elif qbittorrent == "no":
        filtered = [r for r in filtered if not r.get("in_qbittorrent")]

    sort_key = args.get("sort") or default_sort
    if sort_key not in sortable_fields:
        sort_key = default_sort
    sort_dir = args.get("dir") or ("desc" if sort_key == "days_since" else "asc")

    rows_sorted = sorted(filtered, key=_sort_key_fn(sort_key), reverse=(sort_dir == "desc"))

    page = max(1, _int_or(args.get("page"), 1))
    per_page = min(500, max(1, _int_or(args.get("per_page"), PER_PAGE)))
    total = len(rows_sorted)
    items = rows_sorted[(page - 1) * per_page: page * per_page]
    return {"total": total, "page": page, "per_page": per_page, "items": items}


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/albums")
def api_albums():
    rows = staleness.get_report("albums")
    return jsonify(_apply_query(
        rows, request.args,
        {"artist", "album", "year", "label", "genre", "days_since", "in_qbittorrent"},
    ))


@app.route("/api/artists")
def api_artists():
    rows = staleness.get_report("artists")
    return jsonify(_apply_query(
        rows, request.args,
        {"artist", "album_count", "backed_up_count", "days_since"},
    ))


@app.route("/api/filters/meta")
def api_filters_meta():
    albums = staleness.get_report("albums")
    genres = sorted({r["genre"] for r in albums if r.get("genre")})
    labels = sorted({r["label"] for r in albums if r.get("label")})
    return jsonify({"genres": genres, "labels": labels})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    staleness.refresh_all()
    return jsonify({"ok": True, "computed_at": staleness.computed_at()})


@app.route("/api/status")
def api_status():
    return jsonify({"computed_at": staleness.computed_at()})


HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Discos Olvidados</title>
<style>
:root {
    --bg: #0a0e27; --surface: #16213e; --surface-2: #1f2d4a; --border: #2d3e5f;
    --text: #b0b8c9; --text-muted: #7a8694; --accent: #35bf88; --accent-2: #8e44ad;
    --warning: #f39c12; --danger: #e74c3c;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg); color: var(--text); padding: 20px; }
h1 { color: #fff; margin-bottom: 4px; font-size: 20px; }
#status { color: var(--text-muted); font-size: 12px; margin-bottom: 16px; }
.tabs { display: flex; gap: 6px; margin-bottom: 16px; }
.tab-btn { background: var(--surface); color: var(--text-muted); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }
.tab-btn.active { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; background: var(--surface); padding: 16px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 16px; }
.filters label { font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px; }
.filters input, .filters select { width: 100%; padding: 6px 8px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 13px; }
.filters input:focus, .filters select:focus { outline: none; border-color: var(--accent); }
.actions { grid-column: 1 / -1; display: flex; gap: 8px; }
button { background: var(--accent); color: var(--bg); border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 13px; }
button.secondary { background: var(--surface-2); color: var(--text); }
#summary, #summary-artists { color: var(--text-muted); font-size: 13px; margin-bottom: 10px; }
table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 10px; overflow: hidden; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 11px; }
th.sortable { cursor: pointer; user-select: none; }
th.sortable:hover { color: var(--text); }
th .sort-arrow { color: var(--accent); margin-left: 3px; }
tr:hover td { background: var(--surface-2); }
.clickable { cursor: pointer; }
.clickable:hover { color: #fff; text-decoration: underline; }
.never { color: var(--danger); font-weight: 600; }
.stale-high { color: var(--warning); }
.pagination { display: flex; gap: 6px; justify-content: center; margin-top: 14px; }
.pagination button { background: var(--surface-2); color: var(--text); padding: 6px 10px; }
.pagination button.active { background: var(--accent); color: var(--bg); }
.pagination button:disabled { opacity: 0.4; cursor: default; }
</style>
</head>
<body>
<h1>Discos Olvidados — REPEAT-ONE</h1>
<div id="status"></div>
<button class="secondary" style="margin-bottom:16px" onclick="refreshData()">Actualizar (recalcular)</button>
<div class="tabs">
    <button class="tab-btn active" data-tab="albumes" onclick="switchTab('albumes')">Álbumes</button>
    <button class="tab-btn" data-tab="artistas" onclick="switchTab('artistas')">Artistas</button>
</div>

<div id="tab-albumes" class="tab-panel active">
    <div class="filters">
        <div><label>Artista</label><input type="text" id="fa_artist"></div>
        <div><label>Álbum</label><input type="text" id="fa_album"></div>
        <div><label>Género</label><input type="text" id="fa_genre" list="genres_list"></div>
        <div><label>Sello</label><input type="text" id="fa_label" list="labels_list"></div>
        <div><label>Escuchado</label>
            <select id="fa_never"><option value="">Todos</option><option value="yes">Nunca</option><option value="no">Alguna vez</option></select>
        </div>
        <div><label>En qBittorrent</label>
            <select id="fa_qbittorrent"><option value="">Todos</option><option value="yes">Sí</option><option value="no">No</option></select>
        </div>
        <datalist id="genres_list"></datalist>
        <datalist id="labels_list"></datalist>
        <div class="actions">
            <button onclick="searchAlbums(1)">Buscar</button>
            <button class="secondary" onclick="clearAlbumFilters()">Limpiar</button>
        </div>
    </div>
    <div id="summary"></div>
    <table>
        <thead><tr>
            <th class="sortable" data-sort="artist">Artista<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="album">Álbum<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="year">Año<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="label">Sello<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="genre">Género<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="days_since">Sin escuchar<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="in_qbittorrent">qBittorrent<span class="sort-arrow"></span></th>
        </tr></thead>
        <tbody id="albums-results"></tbody>
    </table>
    <div class="pagination" id="albums-pagination"></div>
</div>

<div id="tab-artistas" class="tab-panel">
    <div class="filters">
        <div><label>Artista</label><input type="text" id="fr_artist"></div>
        <div><label>Escuchado</label>
            <select id="fr_never"><option value="">Todos</option><option value="yes">Nunca</option><option value="no">Alguna vez</option></select>
        </div>
        <div class="actions">
            <button onclick="searchArtists(1)">Buscar</button>
            <button class="secondary" onclick="clearArtistFilters()">Limpiar</button>
        </div>
    </div>
    <div id="summary-artists"></div>
    <table>
        <thead><tr>
            <th class="sortable" data-sort="artist">Artista<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="album_count">Álbumes<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="backed_up_count">En qBittorrent<span class="sort-arrow"></span></th>
            <th class="sortable" data-sort="days_since">Sin escuchar<span class="sort-arrow"></span></th>
        </tr></thead>
        <tbody id="artists-results"></tbody>
    </table>
    <div class="pagination" id="artists-pagination"></div>
</div>

<script>
function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function formatDaysSince(days) {
    if (days === null || days === undefined) return '<span class="never">Nunca</span>';
    const cls = days > 365 ? 'stale-high' : '';
    if (days < 1) return '<span class="' + cls + '">hoy</span>';
    if (days < 30) return `<span class="${cls}">${Math.round(days)} días</span>`;
    if (days < 365) return `<span class="${cls}">${Math.round(days / 30)} meses</span>`;
    return `<span class="${cls}">${(days / 365).toFixed(1)} años</span>`;
}

async function loadStatus() {
    const r = await fetch('/api/status');
    const data = await r.json();
    document.getElementById('status').textContent = data.computed_at
        ? `Calculado: ${new Date(data.computed_at).toLocaleString('es-ES')}`
        : 'Calculando...';
}

async function refreshData() {
    document.getElementById('status').textContent = 'Recalculando (puede tardar unos segundos)...';
    await fetch('/api/refresh', { method: 'POST' });
    await loadStatus();
    searchAlbums(albumsPage);
    searchArtists(artistsPage);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tab));
    if (tab === 'artistas' && !window._artistsLoaded) {
        window._artistsLoaded = true;
        searchArtists(1);
    }
}

// ── Álbumes ─────────────────────────────────────────────────────────────

let albumsPage = 1, albumsTotalPages = 1;
let albumsSortKey = 'days_since', albumsSortDir = 'desc';

async function loadMeta() {
    const r = await fetch('/api/filters/meta');
    const data = await r.json();
    document.getElementById('genres_list').innerHTML = data.genres.map(g => `<option value="${escapeHtml(g)}">`).join('');
    document.getElementById('labels_list').innerHTML = data.labels.map(l => `<option value="${escapeHtml(l)}">`).join('');
}

function clearAlbumFilters() {
    document.querySelectorAll('#tab-albumes .filters input').forEach(i => i.value = '');
    document.getElementById('fa_never').value = '';
    document.getElementById('fa_qbittorrent').value = '';
    searchAlbums(1);
}

function soloFiltroAlbum(field, value) {
    if (!value) return;
    document.querySelectorAll('#tab-albumes .filters input').forEach(i => i.value = '');
    const map = { artist: 'fa_artist', album: 'fa_album', genre: 'fa_genre', label: 'fa_label' };
    if (map[field]) document.getElementById(map[field]).value = value;
    searchAlbums(1);
}

document.querySelectorAll('#tab-albumes th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (albumsSortKey === key) albumsSortDir = albumsSortDir === 'asc' ? 'desc' : 'asc';
        else { albumsSortKey = key; albumsSortDir = key === 'days_since' ? 'desc' : 'asc'; }
        searchAlbums(1);
    });
});

function renderSortIndicators(prefix, key, dir) {
    document.querySelectorAll(`#tab-${prefix} th.sortable`).forEach(th => {
        const arrow = th.querySelector('.sort-arrow');
        arrow.textContent = th.dataset.sort === key ? (dir === 'asc' ? '▲' : '▼') : '';
    });
}

async function searchAlbums(page) {
    albumsPage = page;
    const params = new URLSearchParams({ page: page, sort: albumsSortKey, dir: albumsSortDir });
    const artist = document.getElementById('fa_artist').value.trim();
    const album = document.getElementById('fa_album').value.trim();
    const genre = document.getElementById('fa_genre').value.trim();
    const label = document.getElementById('fa_label').value.trim();
    const never = document.getElementById('fa_never').value;
    const qbittorrent = document.getElementById('fa_qbittorrent').value;
    if (artist) params.set('artist', artist);
    if (album) params.set('album', album);
    if (genre) params.set('genre', genre);
    if (label) params.set('label', label);
    if (never) params.set('never_listened', never);
    if (qbittorrent) params.set('qbittorrent', qbittorrent);

    const r = await fetch('/api/albums?' + params.toString());
    const data = await r.json();
    albumsTotalPages = Math.max(1, Math.ceil(data.total / data.per_page));

    document.getElementById('summary').textContent = `${data.total} álbumes encontrados`;
    document.getElementById('albums-results').innerHTML = data.items.map(it => `
        <tr>
            <td class="clickable" data-field="artist" data-value="${escapeHtml(it.artist)}">${escapeHtml(it.artist)}</td>
            <td class="clickable" data-field="album" data-value="${escapeHtml(it.album)}">${escapeHtml(it.album)}</td>
            <td>${escapeHtml(it.year || '')}</td>
            <td class="clickable" data-field="label" data-value="${escapeHtml(it.label || '')}">${escapeHtml(it.label || '')}</td>
            <td class="clickable" data-field="genre" data-value="${escapeHtml(it.genre || '')}">${escapeHtml(it.genre || '')}</td>
            <td>${formatDaysSince(it.days_since)}</td>
            <td>${it.in_qbittorrent ? '✓' : '✗'}</td>
        </tr>
    `).join('');
    document.querySelectorAll('#albums-results [data-field]').forEach(el => {
        el.addEventListener('click', () => soloFiltroAlbum(el.dataset.field, el.dataset.value));
    });

    renderSortIndicators('albumes', albumsSortKey, albumsSortDir);
    renderPagination('albums-pagination', albumsPage, albumsTotalPages, searchAlbums);
}

// ── Artistas ────────────────────────────────────────────────────────────

let artistsPage = 1, artistsTotalPages = 1;
let artistsSortKey = 'days_since', artistsSortDir = 'desc';

function clearArtistFilters() {
    document.getElementById('fr_artist').value = '';
    document.getElementById('fr_never').value = '';
    searchArtists(1);
}

document.querySelectorAll('#tab-artistas th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (artistsSortKey === key) artistsSortDir = artistsSortDir === 'asc' ? 'desc' : 'asc';
        else { artistsSortKey = key; artistsSortDir = key === 'days_since' ? 'desc' : 'asc'; }
        searchArtists(1);
    });
});

async function searchArtists(page) {
    artistsPage = page;
    const params = new URLSearchParams({ page: page, sort: artistsSortKey, dir: artistsSortDir });
    const artist = document.getElementById('fr_artist').value.trim();
    const never = document.getElementById('fr_never').value;
    if (artist) params.set('artist', artist);
    if (never) params.set('never_listened', never);

    const r = await fetch('/api/artists?' + params.toString());
    const data = await r.json();
    artistsTotalPages = Math.max(1, Math.ceil(data.total / data.per_page));

    document.getElementById('summary-artists').textContent = `${data.total} artistas encontrados`;
    document.getElementById('artists-results').innerHTML = data.items.map(it => `
        <tr>
            <td class="clickable" data-value="${escapeHtml(it.artist)}">${escapeHtml(it.artist)}</td>
            <td>${it.album_count}</td>
            <td>${it.backed_up_count} / ${it.album_count}</td>
            <td>${formatDaysSince(it.days_since)}</td>
        </tr>
    `).join('');
    document.querySelectorAll('#artists-results [data-value]').forEach(el => {
        el.addEventListener('click', () => {
            document.getElementById('fr_artist').value = el.dataset.value;
            searchArtists(1);
        });
    });

    renderSortIndicators('artistas', artistsSortKey, artistsSortDir);
    renderPagination('artists-pagination', artistsPage, artistsTotalPages, searchArtists);
}

// ── Paginación (compartida) ─────────────────────────────────────────────

function renderPagination(elId, page, totalPages, fn) {
    const el = document.getElementById(elId);
    let html = `<button ${page <= 1 ? 'disabled' : ''} onclick="(${fn.name})(${page - 1})">&laquo;</button>`;
    const start = Math.max(1, page - 3), end = Math.min(totalPages, page + 3);
    for (let p = start; p <= end; p++) {
        html += `<button class="${p === page ? 'active' : ''}" onclick="(${fn.name})(${p})">${p}</button>`;
    }
    html += `<button ${page >= totalPages ? 'disabled' : ''} onclick="(${fn.name})(${page + 1})">&raquo;</button>`;
    el.innerHTML = html;
}

loadStatus();
loadMeta();
searchAlbums(1);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
