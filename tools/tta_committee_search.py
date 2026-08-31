"""Search committee.tta.or.kr (EUC-KR JSP site) for candidate Korean ATSC 3.0 / UHD standards and write candidates.csv."""
import re, csv, html, pathlib, urllib.request, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "standards" / "KR" / "candidates.csv"
URL = "https://committee.tta.or.kr/data/standard_list_N.jsp"
KEYWORDS = ["UHD", "UHDTV", "ATSC", "지상파", "재난경보", "MMT", "ROUTE", "하이브리드", "IBB", "MPEG-H", "HEVC", "방송 앱", "부가서비스", "다채널", "이동방송"]
ROW = re.compile(r'<a[^>]+href="(standard_view\.jsp\?[^"]+)"[^>]*>\s*(TTA[A-Z]\.[A-Z]{2}-[0-9]{2}\.[0-9]{4}(?:/R\d+)?(?:-Part\d+)?)\s*</a>', re.I)

def fetch(kw, page):
    data = urllib.parse.urlencode({"kor_standard": kw.encode("euc-kr"), "standard_no": "", "publish_date": "",
                                   "section_code": "", "s_section": "", "s_owned_section": "Y", "nowPage": page})
    req = urllib.request.Request(URL, data=data.encode(), headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("euc-kr", "replace")

def parse(doc):
    text = re.sub(r"<script.*?</script>", "", doc, flags=re.S)
    rows = []
    # Row layout: ... <td>N</td><td>type</td><td><a href=...>ID</a></td><td>title</td><td>date</td>
    for m in re.finditer(r'<tr[^>]*>(.*?)</tr>', text, flags=re.S):
        cells = [re.sub(r"<[^>]+>", " ", c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), flags=re.S)]
        cells = [html.unescape(re.sub(r"\s+", " ", c)).strip() for c in cells]
        idm = re.search(r'TTA[A-Z]\.[A-Z]{2}-[0-9]{2}\.[0-9]{4}(?:/R\d+)?(?:-Part\d+)?', m.group(1))
        href = re.search(r'href="(standard_view\.jsp\?[^"]+)"', m.group(1))
        if idm and href and len(cells) >= 4:
            date = next((c for c in cells if re.fullmatch(r"\d{4}-\d{2}-\d{2}", c)), "")
            title = max((c for c in cells if idm.group(0) not in c and not re.fullmatch(r"[\d-]+", c)), key=len, default="")
            kind = next((c for c in cells if "TTA" in c and "(" in c), "")
            rows.append((idm.group(0), title, date, kind, "https://committee.tta.or.kr/data/" + html.unescape(href.group(1))))
    total = re.search(r"(?:총|전체)\s*<[^>]*>?\s*([\d,]+)\s*건", text)
    return rows, total.group(1) if total else "?"

seen = {}
for kw in KEYWORDS:
    for page in range(1, 8):
        try:
            rows, total = parse(fetch(kw, page))
        except Exception as e:
            print(f"[{kw}] p{page} error {e}"); break
        new = 0
        for r in rows:
            if r[0] not in seen:
                seen[r[0]] = r + (kw,); new += 1
        print(f"[{kw}] p{page}: {len(rows)} rows, {new} new (total={total})")
        if len(rows) < 10 or new == 0: break
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["doc_id", "title", "date", "kind", "view_url", "matched_keyword"])
    for r in sorted(seen.values()): w.writerow(r)
print(f"wrote {len(seen)} candidates -> {OUT}")
