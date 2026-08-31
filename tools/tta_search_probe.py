"""Headless Edge (logged-in profile): open ttaSearch?key=12, record API calls, run a search for a keyword, print API traffic."""
import json, pathlib, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
KR = ROOT / "standards" / "KR"
kw = sys.argv[1] if len(sys.argv) > 1 else "UHD"
log = []
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    def on_resp(r):
        u = r.url
        if "/api/" in u or "ttaSearch" in u or "download" in u.lower() or "file" in u.lower():
            try: body = r.text()
            except Exception: body = ""
            log.append({"m": r.request.method, "url": u, "status": r.status, "post": (r.request.post_data or "")[:300], "body": body[:1500]})
    page.on("response", on_resp)
    page.goto("https://www.tta.or.kr/tta/ttaSearch?key=12", wait_until="networkidle")
    page.wait_for_timeout(1500)
    print("TITLE:", page.title())
    print("LOGIN STATE TEXT:", "로그아웃" in page.content(), flush=True)
    # find a search input
    inputs = page.locator("input[type='text'], input[type='search'], input:not([type])")
    n = inputs.count(); print("text inputs:", n)
    for i in range(n):
        el = inputs.nth(i)
        try: print(f"  input[{i}] placeholder={el.get_attribute('placeholder')!r} name={el.get_attribute('name')!r} id={el.get_attribute('id')!r} visible={el.is_visible()}")
        except Exception as e: print("  err", e)
    target = None
    for i in range(n):
        el = inputs.nth(i)
        if el.is_visible(): target = el; break
    if target:
        target.fill(kw); target.press("Enter")
        page.wait_for_timeout(4000)
        try: page.wait_for_load_state("networkidle", timeout=15000)
        except Exception: pass
    print("URL after search:", page.url)
    txt = page.inner_text("body")
    import re
    ids = sorted(set(re.findall(r"TTA[A-Z]\.[A-Z]{2}-\d{2}\.\d{4}(?:/R\d+)?(?:-Part\d+)?", txt)))
    print("IDS on page:", ids[:40])
    print("BODY SNIPPET:", re.sub(r"\s+", " ", txt)[:1200])
    print("\n=== API LOG ===")
    for e in log: print(json.dumps(e, ensure_ascii=False)[:1800])
    (KR / ".search_probe.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    ctx.close()
