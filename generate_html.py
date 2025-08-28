import os
import pandas as pd


def generate_static_html(input_csv: str = "announcements.csv", output_html: str = "announcements.html"):
    if not os.path.exists(input_csv):
        print(f"{input_csv} not found; skip HTML generation")
        return
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"Failed to read {input_csv}: {e}")
        return

    # Normalize columns and types
    for col in ["exchange", "type", "time", "title", "url", "content", "release_time", "symbol", "action", "comments", "file"]:
        if col not in df.columns:
            df[col] = ""

    # Ensure release_time is ISO-like string for filtering
    def _to_iso(x):
        try:
            return pd.to_datetime(x).isoformat()
        except Exception:
            return ""
    df["release_time"] = df["release_time"].apply(_to_iso)

    # Sort by time descending per requirement
    def _to_date(x):
        try:
            return pd.to_datetime(x)
        except Exception:
            return pd.NaT
    df["_sort_time"] = df["time"].apply(_to_date)
    df = df.sort_values(by=["_sort_time", "exchange"], ascending=[False, True]).drop(columns=["_sort_time"])

    records = df.to_dict(orient="records")

    import json as _json
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        _hk_tz = ZoneInfo("Asia/Hong_Kong")
        _tz_label = "HKT"
    except Exception:
        _hk_tz = None
        _tz_label = "HKT"
    _now_hk = datetime.now(_hk_tz) if _hk_tz else datetime.utcnow()
    gen_time_str = _now_hk.strftime("%Y-%m-%d %H:%M:%S") + f" {_tz_label}"
    data_json = _json.dumps(records, ensure_ascii=False)

    html = """
<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Announcements Dashboard</title>
  <style>
    :root {
      --bg: #f8fafc;
      --panel: #ffffff;
      --muted: #475569;
      --card: #ffffff;
      --accent: #0ea5e9;
      --accent2: #7c3aed;
      --text: #0f172a;
      --danger: #dc2626;
      --success: #16a34a;
      --border: #e5e7eb;
      --hover: #f1f5f9;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; }
    header { position: sticky; top: 0; z-index: 10; background: rgba(255,255,255,.85); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); }
    .container { display: grid; grid-template-columns: 1.4fr .6fr; gap: 16px; padding: 16px; max-width: 1400px; margin: 0 auto; }
    .filters { display: flex; gap: 12px; align-items: center; padding: 12px 16px; }
    .filters input[type=date] { background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 8px 10px; border-radius: 8px; }
    .filters .badge { padding: 4px 10px; border-radius: 999px; background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 12px; }
    .left { padding: 4px 0 24px 0; }
    .right { position: sticky; top: 60px; height: calc(100vh - 90px); border-left: 1px solid var(--border); padding-left: 16px; }
    .viewer { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; height: 100%; padding: 12px; box-shadow: 0 6px 16px rgba(0,0,0,.08); }
    .viewer h3 { margin: 8px 0 12px; font-size: 16px; color: var(--accent); }
    .viewer pre { white-space: pre-wrap; word-break: break-word; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px; height: calc(100% - 48px); overflow: auto; color: #334155; }
    details { margin: 10px 0 18px; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--panel); box-shadow: 0 6px 16px rgba(0,0,0,.06); }
    summary { cursor: pointer; list-style: none; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; font-weight: 600; }
    summary::-webkit-details-marker { display: none; }
    .ex-name { display: flex; align-items: center; gap: 8px; }
    .pill { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); background: #f8fafc; }
    .panel { padding: 12px 16px 18px 16px; }
    .section-title { margin: 10px 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
    table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-bottom: 14px; }
    thead th { position: sticky; top: 0; background: #f8fafc; color: var(--muted); text-align: left; font-weight: 600; font-size: 12px; padding: 10px; border-bottom: 1px solid var(--border); }
    tbody td { padding: 10px; border-top: 1px solid var(--border); font-size: 13px; }
    tbody tr { transition: background .12s ease; }
    tbody tr:hover { background: var(--hover); }
    a.link { color: #2563eb; text-decoration: none; }
    a.link:hover { text-decoration: underline; }
    .tag { padding: 2px 6px; border-radius: 6px; font-size: 12px; border: 1px solid var(--border); }
    .tag.spot { color: #065f46; background: #d1fae5; border-color: #a7f3d0; }
    .tag.futures { color: #7c2d12; background: #ffedd5; border-color: #fed7aa; }
    .muted { color: var(--muted); }
    .controls { margin-left: auto; display: flex; gap: 8px; align-items: center; }
    .counter { font-size: 12px; color: var(--muted); }
    th.col-type, td.col-type { width: 72px; min-width: 72px; white-space: nowrap; }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <div class="filters">
        <span class="pill">Time Range</span>
        <label class="muted">Start: <input type="date" id="startDate"></label>
        <label class="muted">End: <input type="date" id="endDate"></label>
        <div class="controls">
          <span class="counter" id="countLabel"></span>
          <span class="counter" id="genTime">%%GENTIME%%</span>
        </div>
      </div>
    </div>
  </header>
  <div class="container">
    <div class="left" id="leftPane"></div>
    <div class="right">
      <div class="viewer">
        <h3 id="viewerTitle">Select a row to view full content</h3>
        <pre id="viewerContent"></pre>
      </div>
    </div>
  </div>
  <script>
    const DATA = %%DATA%%;
    function fmtDate(d) { try { return new Date(d).toISOString().slice(0,10); } catch(e) { return ''; } }
    function shortText(t, n=120) { if(!t) return ''; const s = String(t).replace(/\s+/g,' ').trim(); return s.length>n ? s.slice(0,n) + '…' : s; }
    function byExchange(items) { const m = new Map(); for (const it of items) { const ex=(it.exchange||'').toLowerCase(); if(!m.has(ex)) m.set(ex, []); m.get(ex).push(it); } return m; }
    function filterByDate(items, start, end) { const s = new Date(start); const e = new Date(end); e.setHours(23,59,59,999); return items.filter(it=>{const v = new Date(it.release_time||it.time||''); return v instanceof Date && !isNaN(v) && v>=s && v<=e;}); }
    function sortByTime(items) { return items.slice().sort((a,b)=>{ const ta = Date.parse(a.time||a.release_time||0)||0; const tb = Date.parse(b.time||b.release_time||0)||0; return tb - ta; }); }

    function tableHtml(rows) {
      const cells = rows.map((r,idx)=>`<tr data-idx="${idx}">
        <td class="col-type"><span class="tag ${r.type==='现货'?'spot':'futures'}">${r.type||''}</span></td>
        <td>${(r.time||'').toString().slice(0,10)}</td>
        <td>${(r.release_time||r.time||'').toString().slice(0,10)}</td>
        <td>${(r.symbol||'').toString().replace('/USDT','')}</td>
        <td><a class="link" href="${r.url||'#'}" target="_blank" rel="noopener">${(r.title||'').toString()}</a></td>
        <td class="muted">${shortText(r.content||'')}</td>
      </tr>`).join('');
      return `<table><thead><tr>
        <th class="col-type">Type</th><th>Date</th><th>Release</th><th>Symbol</th><th>Title</th><th>Content</th>
      </tr></thead><tbody>${cells}</tbody></table>`;
    }

    function render() {
      const left = document.getElementById('leftPane');
      left.innerHTML='';
      const sd = document.getElementById('startDate').value;
      const ed = document.getElementById('endDate').value;
      const filtered = filterByDate(DATA, sd, ed);
      document.getElementById('countLabel').textContent = `${filtered.length} items`;
      const grouped = byExchange(filtered);
      const exchanges = Array.from(grouped.keys()).sort();
      for (const ex of exchanges) {
        const rows = sortByTime(grouped.get(ex));
        const spot = rows.filter(r=> (r.type||'').includes('现货'));
        const futures = rows.filter(r=> (r.type||'').includes('合约'));
        const open = `<details>
          <summary><span class="ex-name"><span>${ex.toUpperCase()}</span><span class="pill">${rows.length} items</span></span></summary>
          <div class="panel">
            <div class="section-title">Spot</div>
            ${tableHtml(spot)}
            <div class="section-title">Futures</div>
            ${tableHtml(futures)}
          </div>
        </details>`;
        const wrapper = document.createElement('div');
        wrapper.innerHTML = open;
        // attach row click listeners
        wrapper.querySelectorAll('tbody tr').forEach(tr=>{
          tr.addEventListener('click', ()=>{
            const idx = Number(tr.getAttribute('data-idx'));
            const tbl = tr.closest('table');
            const titleEl = tbl && tbl.previousElementSibling;
            const inSpot = !!(titleEl && titleEl.classList.contains('section-title') && titleEl.textContent==='Spot');
            const recs = inSpot ? spot : futures;
            const rec = recs[idx];
            document.getElementById('viewerTitle').textContent = `${(rec.exchange||'').toUpperCase()} · ${rec.symbol||''} · ${rec.time||''}`;
            document.getElementById('viewerContent').textContent = rec.content || '';
          });
        });
        left.appendChild(wrapper);
      }
    }

    function setDefaultDates() {
      const today = new Date();
      const end = today.toISOString().slice(0,10);
      const startD = new Date(today.getTime() - 7*24*3600*1000);
      const start = startD.toISOString().slice(0,10);
      document.getElementById('startDate').value = start;
      document.getElementById('endDate').value = end;
    }

    window.addEventListener('DOMContentLoaded', ()=>{
      setDefaultDates();
      ['startDate','endDate'].forEach(id=> document.getElementById(id).addEventListener('change', render));
      render();
    });
  </script>
</body>
</html>
"""

    try:
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html.replace("%%DATA%%", data_json).replace("%%GENTIME%%", gen_time_str))
        print(f"Static HTML generated: {output_html}")
    except Exception as e:
        print(f"Failed to write {output_html}: {e}")


