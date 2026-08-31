"""Download the selected Korean standards from committee.tta.or.kr using the saved (logged-in) session.
Flow per doc: standard_view.jsp -> ttasVote('kind', pk, fileGubun) links -> ttasDown.jsp?pk_num&fileGubun&content_num=1 -> file."""
import re, html, json, csv, pathlib, urllib.parse, sys, time
from playwright.sync_api import sync_playwright
KR = pathlib.Path("standards/KR").resolve()
sel = json.load(open(KR / "selected.json", encoding="utf-8"))
rows, problems = [], []
def variants(pk, owned):
    q = urllib.parse.quote(pk, safe="")
    return [f"https://committee.tta.or.kr/data/standard_view.jsp?s_owned_section={owned}&kor_standard=&nowPage=1&pk_num={q}&nowSu=1&rn=1",
            f"https://committee.tta.or.kr/data/standard_view.jsp?s_owned_section=&kor_standard=&nowPage=1&pk_num={q}&nowSu=1&rn=1",
            f"https://committee.tta.or.kr/data/standard_view.jsp?pk_num={q}&nowSu=1&section_code=R2&std_no=KO",
            f"https://committee.tta.or.kr/data/standard_view.jsp?pk_num={q}&nowSu=1"]
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(KR / ".edge-profile"), channel="msedge", headless=True, accept_downloads=True)
    st = json.loads((KR / ".committee_state.json").read_text())
    ctx.add_cookies([c for c in st["cookies"] if "tta.or.kr" in c["domain"]])
    for d in sel:
        pk = d["rawStandardNo"].strip().replace("　", "")
        owned = "N" if d.get("ownedSection") == "N" else "Y"
        links, used = [], None
        for u in variants(pk, owned):
            r = ctx.request.get(u); body = r.body().decode("euc-kr", "replace")
            if "login.jsp" in body: problems.append((pk, "LOGIN REQUIRED (session lost)")); print("!! session lost at", pk); break
            links = re.findall(r"ttasVote\('([^']+)','([^']+)',\s*(\d+)\)", body)
            names = re.findall(r'alt="([^"]+\.(?:pdf|hwp|hwpx|zip|docx?))"', body, flags=re.I)
            if links: used = u; break
        if not links:
            problems.append((pk, "no file links found")); print(f"-- {pk}: no file links"); continue
        for (kind, pkq, gubun), name in zip(links, names + [None] * len(links)):
            dl = f"https://committee.tta.or.kr/data/ttasDown.jsp?pk_num={pkq}&fileGubun={gubun}&content_num=1&etc="
            r = ctx.request.get(dl, headers={"Referer": "https://committee.tta.or.kr/data/ttasVote.jsp"}, timeout=120000)
            ct = r.headers.get("content-type", ""); cd = r.headers.get("content-disposition", ""); data = r.body()
            if data[:4] != b"%PDF" and "html" in ct:
                # maybe an HTML page with a redirect to Download.jsp
                h = data.decode("euc-kr", "replace")
                m = re.search(r"(?:location(?:\.href)?\s*=\s*|href=)[\"']([^\"']*Download[^\"']*)", h)
                if m:
                    u2 = urllib.parse.urljoin(dl, html.unescape(m.group(1)))
                    r = ctx.request.get(u2, timeout=120000); ct = r.headers.get("content-type", ""); cd = r.headers.get("content-disposition", ""); data = r.body()
            fname = None
            m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
            if m: fname = urllib.parse.unquote(m.group(1)).strip()
            if not fname or fname.lower().endswith((".jsp",)): fname = name or (pk.replace("/", "") + ".pdf")
            fname = re.sub(r'[\/:*?"<>|]', "_", fname)
            ok = data[:4] == b"%PDF" or data[:4] == b"PK\x03\x04" or (name and name.lower().endswith(".hwp") and len(data) > 20000)
            if not ok:
                problems.append((pk, f"not a document: ct={ct} len={len(data)} head={data[:60]!r}")); print(f"!! {pk} gubun{gubun}: ct={ct} len={len(data)}"); continue
            (KR / fname).write_bytes(data)
            rows.append([d["standardNo"], d["korStandard"], d.get("engStandard") or "", d["publishDate"], d["kind"], d["group"], fname, len(data), used])
            print(f"OK {pk} -> {fname} ({len(data)//1024} KB)", flush=True)
            time.sleep(1.0)
    ctx.close()
with open(KR / "index.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["doc_id", "title_ko", "title_en", "version_date", "kind", "group", "filename", "bytes", "source_url"]); w.writerows(rows)
print(f"\nDONE: {len(rows)} files; problems: {len(problems)}")
for pr in problems: print("PROBLEM:", pr)
