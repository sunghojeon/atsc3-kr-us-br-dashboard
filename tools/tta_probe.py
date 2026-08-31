"""Headless Edge with the logged-in profile: capture X-API-KEY, verify login, dump standard-related menus."""
import json, pathlib, sys
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
KR = ROOT / "standards" / "KR"
hdr = {}
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    def on_req(r):
        if "/api/" in r.url and "X-API-KEY" in {k.upper(): v for k, v in r.headers.items()} and "X-API-KEY" not in hdr:
            hdr["X-API-KEY"] = {k.upper(): v for k, v in r.headers.items()}["X-API-KEY"]
            hdr["Authorization"] = {k.upper(): v for k, v in r.headers.items()}.get("AUTHORIZATION", "")
    page.on("request", on_req)
    page.goto("https://www.tta.or.kr/tta/", wait_until="networkidle")
    page.wait_for_timeout(2000)
    print("HEADERS:", json.dumps(hdr)[:300], flush=True)
    (KR / ".tta_headers.json").write_text(json.dumps(hdr))
    h = {"X-API-KEY": hdr.get("X-API-KEY", "")}
    if hdr.get("Authorization"): h["Authorization"] = hdr["Authorization"]
    r = ctx.request.get("https://www.tta.or.kr/api/1.0/user/info", headers=h)
    print("USER/INFO:", r.status, r.text()[:400], flush=True)
    r = ctx.request.get("https://www.tta.or.kr/api/1.0/menu/all", headers=h)
    print("MENU/ALL:", r.status, len(r.text()), flush=True)
    try:
        j = r.json()
    except Exception:
        print(r.text()[:300]); ctx.close(); sys.exit(0)
    (KR / ".tta_menu.json").write_text(json.dumps(j, ensure_ascii=False))
    def walk(o, path=""):
        if isinstance(o, dict):
            name = str(o.get("menuNm") or o.get("menuName") or o.get("name") or o.get("title") or "")
            url = str(o.get("menuUrl") or o.get("url") or o.get("link") or o.get("path") or "")
            if any(k in name + url for k in ("표준", "tandard", "검색", "ttas", "TTAS", "search")):
                print(f"MENU {path}/{name} -> {url}")
            for v in o.values(): walk(v, path + "/" + name if name else path)
        elif isinstance(o, list):
            for x in o: walk(x, path)
    walk(j)
    ctx.close()
