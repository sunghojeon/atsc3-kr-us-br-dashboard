"""Open the ITU-R WP 6A documents page in Edge, wait for the user to log in with a TIES account, then save the session.
Detection: a protected page (WP 6A contributions list) loads without redirecting to the ITU login, or the operator creates
standards/ITU/.ties_login_done. Nothing about the account is stored except the browser session cookies (git-ignored)."""
import sys, time, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
ITU = ROOT / "standards" / "ITU"
FLAG = ITU / ".ties_login_done"; FLAG.unlink(missing_ok=True)
PROTECTED = "https://www.itu.int/md/R23-WP6A-C/en"   # WP 6A contributions (2023-2027 study period)

def logged_in(ctx):
    try:
        r = ctx.request.get(PROTECTED, timeout=30000, max_redirects=5)
        body = r.text()
        return r.status == 200 and "login" not in r.url.lower() and ("Contribution" in body or "Document" in body) and "TIES" not in body[:3000]
    except Exception:
        return False

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(ITU / ".edge-profile"), channel="msedge", headless=False,
                                               accept_downloads=True, viewport={"width": 1400, "height": 950})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(PROTECTED, wait_until="domcontentloaded")
    print("Edge opened at the WP 6A documents page. Please log in with your TIES account.", flush=True)
    deadline, ok = time.time() + 1500, None
    time.sleep(8)
    while time.time() < deadline:
        if FLAG.exists(): ok = "flag"; break
        if logged_in(ctx): ok = "protected-page-accessible"; break
        time.sleep(4)
    if not ok:
        print("TIMEOUT waiting for login", flush=True); ctx.close(); sys.exit(1)
    ctx.storage_state(path=str(ITU / ".ties_state.json"))
    print(f"LOGIN_DETECTED ({ok}); cookies={sorted({c['name'] for c in ctx.cookies() if 'itu.int' in c.get('domain', '')})[:12]}", flush=True)
    ctx.close()
