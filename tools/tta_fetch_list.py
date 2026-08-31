"""(1) Collect Korean standard candidates via www.tta.or.kr search API; (2) inspect logged-in committee view page for download link format."""
import json, re, csv, pathlib, html
from playwright.sync_api import sync_playwright
KR = pathlib.Path("standards/KR")
KEY = "iCbdc1b8k+S1r5EoTG5h8qZ+tNxhu9nJuiIDyvQBsNc="   # public constant from the site's JS bundle
KWS = ["UHD", "UHDTV", "지상파", "ATSC", "재난경보", "재난", "IBB", "하이브리드", "HEVC", "MPEG-H", "MMT", "ROUTE", "방송 서비스", "방송망", "수신기"]
API = "https://www.tta.or.kr/api/1.0/standard/search"
seen = {}
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=True)
    H = {"X-API-KEY": KEY, "Accept": "application/json"}
    r = ctx.request.get(API, params={"ttas": "Y", "ttar": "Y", "searchKorStandard": "UHD", "page": 0, "size": 100}, headers=H)
    j = r.json(); print("RESP KEYS:", {k: (v if not isinstance(v, list) else f"list[{len(v)}]") for k, v in j.items()})
    for kw in KWS:
        for page in range(0, 20):
            r = ctx.request.get(API, params={"ttas": "Y", "ttar": "Y", "searchKorStandard": kw, "page": page, "size": 100}, headers=H)
            if r.status != 200: print(kw, page, "HTTP", r.status); break
            j = r.json(); items = j.get("content", [])
            new = 0
            for it in items:
                if it["standardNo"] not in seen: seen[it["standardNo"]] = dict(it, matchedKw=kw); new += 1
            print(f"[{kw}] page{page}: {len(items)} items, {new} new, total={j.get('totalElements')}, last={j.get('last')}")
            if j.get("last", True) or not items: break
    (KR / "tta_search_results.json").write_text(json.dumps(list(seen.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    with open(KR / "tta_search_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["standardNo", "korStandard", "engStandard", "publishDate", "kindNm", "sectionCode", "ownedSection", "delName", "managementNo", "managementSeq", "matchedKw"])
        for it in sorted(seen.values(), key=lambda x: x["standardNo"]):
            w.writerow([it.get(k) for k in ["standardNo", "korStandard", "engStandard", "publishDate", "kindNm", "sectionCode", "ownedSection", "delName", "managementNo", "managementSeq", "matchedKw"]])
    print("TOTAL candidates:", len(seen))
    # (2) committee view page, logged in
    view = "https://committee.tta.or.kr/data/standard_view.jsp?pk_num=TTAK.KO-07.0151%2FR1&nowSu=1&section_code=R2&std_no=KO"
    r = ctx.request.get(view); body = r.body().decode("euc-kr", "replace")
    (KR / ".view_sample.html").write_text(body, encoding="utf-8")
    print("VIEW status", r.status, "len", len(body))
    for m in re.findall(r'(?:href|onclick|action)="([^"]*(?:Download|stnfile|file|File|down)[^"]*)"', body): print("LINK:", html.unescape(m)[:300])
    for m in re.findall(r'function\s+\w*(?:down|Down|file)\w*\s*\([^)]*\)\s*\{[^}]{0,400}', body): print("FUNC:", re.sub(r"\s+", " ", m)[:400])
    txt = re.sub(r"<script.*?</script>", "", body, flags=re.S); txt = re.sub(r"<[^>]+>", " ", txt); txt = html.unescape(re.sub(r"\s+", " ", txt))
    i = txt.find("표준번호"); print("VIEW TEXT:", txt[i:i+1200])
    ctx.close()
