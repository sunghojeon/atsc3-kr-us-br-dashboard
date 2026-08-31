"""Open committee.tta.or.kr login in Edge (persistent profile), wait until the standard-view page shows
download links (i.e. the user is logged in) or the operator creates standards/KR/.committee_login_done."""
import sys, time, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
KR = ROOT / "standards" / "KR"
FLAG = KR / ".committee_login_done"; FLAG.unlink(missing_ok=True)
VIEW = "https://committee.tta.or.kr/data/standard_view.jsp?pk_num=TTAK.KO-07.0151%2FR1&nowSu=1&section_code=R2&std_no=KO"
LOGIN = "https://committee.tta.or.kr/mypage/login.jsp?returnUrl=" + VIEW.replace("&", "%26").replace("?", "%3F")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=False,
                                               accept_downloads=True, viewport={"width": 1400, "height": 950})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(LOGIN, wait_until="domcontentloaded")
    print("Edge opened at committee.tta.or.kr login. Please log in.", flush=True)
    deadline, ok = time.time() + 1500, False
    while time.time() < deadline:
        if FLAG.exists(): ok = "flag"; break
        try:
            body = ctx.request.get(VIEW, timeout=20000).body().decode("euc-kr", "replace")
            if "Download.jsp" in body or "stnfile" in body or "logout" in body.lower():
                ok = "download-link-visible"; break
        except Exception as e:
            print("poll error", e, flush=True)
        time.sleep(3)
    if not ok:
        print("TIMEOUT", flush=True); ctx.close(); sys.exit(1)
    ctx.storage_state(path=str(KR / ".committee_state.json"))
    print(f"LOGIN_DETECTED ({ok}); cookies={sorted({c['name'] for c in ctx.cookies() if 'committee' in c.get('domain','')})}", flush=True)
    ctx.close()
