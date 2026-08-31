"""Open TTA in Edge, wait for the user to log in, save the session, close.
Detection: (a) flag file standards/KR/.tta_login_done appears (created by the operator), or
(b) the cookie set changes vs. the pre-login baseline (new cookie name, or JSESSIONID value regenerated)."""
import sys, time, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
KR = ROOT / "standards" / "KR"
STATE, FLAG = KR / ".tta_state.json", KR / ".tta_login_done"
FLAG.unlink(missing_ok=True)

def snap(ctx):
    return {c["name"]: c["value"] for c in ctx.cookies() if "tta.or.kr" in c.get("domain", "")}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=False,
        accept_downloads=True, viewport={"width": 1400, "height": 950})
    ctx.clear_cookies()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.tta.or.kr/tta/", wait_until="networkidle")
    time.sleep(3)
    base = snap(ctx)
    print(f"Edge opened. Baseline cookies={sorted(base)}. Please log in to TTA.", flush=True)
    deadline, reason = time.time() + 1500, None
    while time.time() < deadline:
        cur = snap(ctx)
        if FLAG.exists():
            reason = "flag"; break
        new = sorted(set(cur) - set(base))
        changed = sorted(k for k in cur if k in base and cur[k] != base[k])
        if new or changed:
            time.sleep(5); cur = snap(ctx); reason = f"new={new} changed={changed}"; break
        time.sleep(2)
    if not reason:
        print("TIMEOUT waiting for login", flush=True); ctx.close(); sys.exit(1)
    ctx.storage_state(path=str(STATE))
    print(f"LOGIN_DETECTED ({reason}); cookies={sorted(cur)}; url={page.url}", flush=True)
    ctx.close()
