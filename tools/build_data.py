"""Build data/standards.json: rows = ATSC 3.0 documents (from standards/US/index.csv), grouped by ATSC
number series, each mapped to corresponding ITU-R / TTA / SBTVD Forum documents. All text in English."""
import csv, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
US = list(csv.DictReader(open(ROOT / "standards/US/index.csv", encoding="utf-8-sig")))

# Native-language document titles: {doc_id: {"title": ..., "lang": "en|ko|pt", "title_en": ...}}
DOC_TITLES = {}
for r in US:  # ATSC — English
    DOC_TITLES[r["doc_id"]] = {"title": r["title"], "lang": "en", "title_en": r["title"]}
try:  # TTA — Korean (English title kept for tooltips)
    for it in json.load(open(ROOT / "standards/KR/tta_search_results.json", encoding="utf-8")):
        sid = it["standardNo"].strip().replace("　", "")
        if sid.startswith(("TTAK.KO-07", "TTAK.KO-06.0523", "TTAR-07")):
            DOC_TITLES[sid] = {"title": it["korStandard"].strip(), "lang": "ko", "title_en": (it.get("engStandard") or "").strip().replace(" ? ", " - ")}  # " ? " = dash mis-encoded in the TTA API response
except FileNotFoundError:
    pass
ITU_TITLES = {  # ITU-R — English (overridden by standards/ITU/index.csv when present)
    "BT.709": "Parameter values for the HDTV standards for production and international programme exchange",
    "BT.1306": "Error-correction, data framing, modulation and emission methods for digital terrestrial television broadcasting",
    "BT.1877": "Error-correction, data framing, modulation and emission methods and selection guidance for second generation digital terrestrial television broadcasting systems",
    "BT.2020": "Parameter values for ultra-high definition television systems for production and international programme exchange",
    "BT.2053": "Technical requirements for integrated broadcast-broadband systems",
    "BT.2075": "Integrated broadcast-broadband system",
    "BT.2100": "Image parameter values for high dynamic range television for use in production and international programme exchange",
    "BT.2160": "Features of three-dimensional television video systems for broadcasting",
    "BS.1770": "Algorithms to measure audio programme loudness and true-peak audio level",
    "BS.2051": "Advanced sound system for programme production",
    "BS.2088": "Long-form file format for the international exchange of audio programme materials with metadata",
    "Report BT.2267": "Integrated broadcast-broadband systems",
    "Report BT.2295": "Digital terrestrial broadcasting systems",
    "Report BT.2343": "Collection of field trials of ultra-high definition television over digital terrestrial television broadcasting networks",
}
for k, v in ITU_TITLES.items():
    DOC_TITLES[k] = {"title": v, "lang": "en", "title_en": v}
for folder, lang in (("ITU", "en"), ("BR", "pt")):  # agent-produced indexes: ITU (English), SBTVD Forum (language column)
    p = ROOT / "standards" / folder / "index.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            did = (r.get("doc_id") or "").strip()
            if not did or not r.get("title") or did.startswith("ABNT-") or did.startswith("BR-REG-"):
                continue  # ABNT and regulation titles are set explicitly below (verified against the catalogue / official text)
            l = (r.get("language") or lang).strip() or lang
            if folder == "ITU" and (r.get("type") or "").lower().startswith("rep"): did = "Report " + did
            title = re.sub(r"\s*\[.*?\]\s*", " ", r["title"]).strip()  # drop collector annotations in brackets
            DOC_TITLES[did] = {"title": title, "lang": l, "title_en": title if l == "en" else ""}
# ABNT NBR 25601–25609:2025 (TV 3.0 series). Titles verified on abntcatalogo.com.br (2026-08-31): Portuguese title plus the
# official English secondary title where ABNT provides one; 25601, 25607 and 25608 carry an English title only.
ABNT_TITLES = {
    "ABNT NBR 25601:2025": ("TV 3.0 — Over-the-air physical layer", "en", ""),
    "ABNT NBR 25602:2025": ("TV 3.0 — Camada de transporte", "pt", "TV 3.0 — Transport layer"),
    "ABNT NBR 25603:2025": ("TV 3.0 — Codificação de vídeo", "pt", "TV 3.0 — Video coding"),
    "ABNT NBR 25604:2025": ("TV 3.0 — Codificação de áudio", "pt", "TV 3.0 — Audio coding"),
    "ABNT NBR 25605:2025": ("TV 3.0 — Legendas", "pt", "TV 3.0 — Closed captioning"),
    "ABNT NBR 25606:2025": ("TV 3.0 — Língua de sinais", "pt", "TV 3.0 — Closed signing"),
    "ABNT NBR 25607:2025": ("TV 3.0 — Emergency warning system", "en", ""),
    "ABNT NBR 25608:2025": ("TV 3.0 — Application coding", "en", ""),
    "ABNT NBR 25609:2025": ("TV 3.0 — Receptores", "pt", "TV 3.0 — Receivers"),
}
for k, (t, l, en) in ABNT_TITLES.items():
    DOC_TITLES[k] = {"title": t, "lang": l, "title_en": en}
OG = {  # Fórum SBTVD TV 3.0 Operational Guidelines (English documents), ids as used in the cells
    "SBTVD OG-01": "TV 3.0 Operational Guidelines — Over-the-Air Physical Layer",
    "SBTVD OG-02": "TV 3.0 Operational Guidelines — Transport Layer",
    "SBTVD OG-03": "TV 3.0 Operational Guidelines — Video Coding",
    "SBTVD OG-04": "TV 3.0 Operational Guidelines — Audio Coding",
    "SBTVD OG-05": "TV 3.0 Operational Guidelines — Closed Captioning",
    "SBTVD OG-06": "TV 3.0 Operational Guidelines — Closed Signing",
    "SBTVD OG-07 v1": "TV 3.0 Operational Guidelines — Emergency Warning System",
    "SBTVD OG-08": "TV 3.0 Operational Guidelines — Application Coding",
    "SBTVD OG-CPC (draft)": "TV 3.0 Operational Guidelines — Common Public Communication and Digital Government Platform Support (final draft)",
}
for k, t in OG.items():
    DOC_TITLES[k] = {"title": t, "lang": "en", "title_en": t}

TODAY = "2026-08-31"
REVIEW = {"status": "draft", "by": "", "updated": TODAY}

def series_of(doc_id):
    m = re.match(r"A/(\d)(\d)(\d)", doc_id)
    if not m: return "other"
    h, t = m.group(1), m.group(2)
    if h != "3": return None  # only the A/300 series is in scope (A/200 etc. excluded)
    if t == "0": return "s300"
    return {"2": "s320", "3": "s330", "4": "s340", "5": "s350", "6": "s360", "7": "s370", "8": "s380"}.get(t, "other")

CATEGORIES = [
    {"id": "s300", "name": "A/300 · System", "desc": "System architecture and umbrella document"},
    {"id": "s320", "name": "A/320 series · Physical Layer", "desc": "Bootstrap, physical layer protocol, return channel, STL, PHY test plans"},
    {"id": "s330", "name": "A/330 series · Management and Protocols", "desc": "Link layer, signaling/delivery, ESG, usage reporting, watermarks, app events, companion devices"},
    {"id": "s340", "name": "A/340 series · Presentation", "desc": "Video, audio, captions, interactive content"},
    {"id": "s350", "name": "A/350 series · Recommended Practices (Protocols)", "desc": "Guides to link layer and signaling/delivery"},
    {"id": "s360", "name": "A/360 series · Security", "desc": "Security, service protection, DRM"},
    {"id": "s370", "name": "A/370 series · Redistribution", "desc": "Conversion and delivery of ATSC 3.0 services for redistribution"},
    {"id": "s380", "name": "A/380 series · Haptics and Interactive Use", "desc": ""},
    {"id": "datacast", "name": "Datacasting services", "desc": "Data services carried over the broadcast, anchored to A/331 NRT delivery where applicable; broadcast positioning (BPS) listed separately"},
]

V = lambda code, text="", kind="": {"code": code, "text": text, **({"kind": kind} if kind else {})}
def C(docs=(), note="", rel="", conf=""):
    """Cell: documents of one body, an annotation, the mapping relation to the ATSC document and the confidence of that mapping."""
    c = {"docs": list(docs), "note": note}
    if rel: c["rel"] = rel
    if conf: c["conf"] = conf
    return c
ITU_NONE, NONE = C(), C()

RELATIONS = {  # how a body's document relates to the ATSC baseline document
    "baseline":     {"label": "Baseline",                 "desc": "The ATSC document itself"},
    "incorporated": {"label": "Incorporated by reference", "desc": "The ATSC document is adopted by citing it (law or standard)"},
    "profile":      {"label": "Profile",                  "desc": "Adopts the ATSC technology with national constraints or options"},
    "normative":    {"label": "Normative equivalent",     "desc": "Independent standard specifying the same function"},
    "alternative":  {"label": "Alternative technology",   "desc": "A different technology fulfils the function"},
    "related":      {"label": "Related",                  "desc": "Covers the topic; equivalence not established"},
    "reference":    {"label": "International reference",  "desc": "ITU-R Recommendation/Report used as reference"},
}
CONFIDENCE = {  # how well the mapping has been verified
    "confirmed":  {"label": "Confirmed",     "desc": "Verified against the official text (clause level)"},
    "partial":    {"label": "Partly verified", "desc": "Key clauses checked; full comparison pending"},
    "metadata":   {"label": "Title-level",   "desc": "Mapped from titles, scopes and catalogue metadata only"},
    "inferred":   {"label": "Inferred",      "desc": "Deduced from secondary sources"},
    "unverified": {"label": "Unverified",    "desc": "Not yet checked"},
}
NONE_KINDS = {  # sub-types of 'No counterpart'
    "not-adopted": "Officially not adopted",
    "not-found":   "Searched, none found",
    "pending":     "Not yet reviewed",
    "n/a":         "Not applicable",
}

# Per-document mapping. Keys: ATSC doc id as in index.csv.
MAP = {
 "A/300": dict(summary="Top-level document defining the ATSC 3.0 system architecture and the relationship between the individual standards.",
   ITU=C(["Report BT.2295", "BT.1299", "Report BT.2400"], "DTTB system specifications (ATSC 3.0 description); common family of DTTB systems (BT.1299); global platform for broadcasting (Report BT.2400)."),
   TTA=C(["TTAK.KO-07.0147", "TTAK.KO-07.0148/R1"], "Umbrella standard and Part 1: Service and System Requirements."),
   SBTVD=C((), "TV 3.0 system overview document to be confirmed."),
   verdict=V("review", "TTA Part 1 appears to play the role of A/300 system requirements; clause-by-clause comparison pending.")),
 "A/321": dict(summary="Bootstrap signal structure, emergency-alert wake-up bits, physical-layer version signaling.",
   ITU=C(["BT.1877", "BT.1306"], "Second-generation DTTB system specifications (ATSC 3.0 included)."),
   TTA=C(["TTAK.KO-07.0151/R1"], "Part 4: Physical Layer includes the bootstrap."),
   SBTVD=C((), "TV 3.0 physical layer is ATSC 3.0-based; bootstrap version to be confirmed."),
   verdict=V("review", "TTA Part 4 is understood to adopt A/321 and A/322; use of the EA wake-up bits needs confirmation."),
   impact="Whether EA wake-up is used affects receiver requirements."),
 "A/322": dict(summary="OFDM physical layer: LDPC/BCH channel coding, PLPs, LDM, frame structure, 6/7/8 MHz channel bandwidths.",
   ITU=C(["BT.1877", "BT.1306", "Report BT.2295", "Report BT.2468", "Report BT.2467", "BT.1206"], "Second-generation DTTB system in Rec. BT.1877; parameter selection and QoS evaluation guidance (Reports BT.2468, BT.2467); spectrum limit masks (BT.1206)."),
   TTA=C(["TTAK.KO-07.0151/R1"], "Part 4: Physical Layer (revised Dec 2025). 6 MHz; defines broadcast gateway and exciter functions."),
   SBTVD=C((), "TV 3.0 physical layer (ATSC 3.0 PHY-based) specification to be confirmed."),
   verdict=V("partial", "TTA adopts the ATSC 3.0 PHY but restricts it to Korean operating parameters (6 MHz etc.)."),
   impact="Transmission equipment (gateway, exciter) is largely compatible; operating profiles (PLP configuration, LDM use) need checking.",
   recommendation="Compare the mandatory/optional parameter tables of Part 4 with the A/322 annexes."),
 "A/323": dict(summary="Dedicated return channel over broadcast spectrum.", ITU=ITU_NONE, TTA=C((), "No counterpart (within the reviewed set)."), SBTVD=NONE,
   verdict=V("none", "Neither Korea nor Brazil specifies a dedicated return channel.")),
 "A/324": dict(summary="STLTP interface between the broadcast gateway (scheduler) and transmitters; timing and SFN synchronization.",
   ITU=C(["Report BT.2386"], "Design and implementation of single frequency networks."),
   TTA=C(["TTAK.KO-07.0151/R1", "TTAR-07.0026/R1"], "Part 4 defines gateway/exciter functions; technical report gives TxID/BSID assignment guidelines."),
   SBTVD=NONE, verdict=V("review", "Adoption of STLTP and Korean SFN operating rules to be compared.")),
 "A/325": dict(summary="Laboratory performance test plan for the ATSC 3.0 physical layer.",
   ITU=C(["Report BT.2495", "Report BT.2389"], "Laboratory and field measurement methods for ATSC 3.0 reception quality; DTTB measurement guidelines."), TTA=C(["TTAK.KO-07.0157"], "Guideline for test methods of terrestrial UHD radio equipment (2022)."), SBTVD=NONE, verdict=V("review")),
 "A/326": dict(summary="Field test plan for ATSC 3.0.",
   ITU=C(["Report BT.2343", "Report BT.2495", "Report BT.2035"], "UHDTV-over-DTTB field trials; ATSC 3.0 measurement methods; DTTB system evaluation guidelines."), TTA=C(["TTAK.KO-07.0157"], ""), SBTVD=NONE, verdict=V("review")),
 "A/327": dict(summary="Guidelines for using the physical layer protocol.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0154/R1"], "Terrestrial UHD system monitoring guideline (related, not equivalent)."), SBTVD=NONE, verdict=V("review")),
 "A/330": dict(summary="ATSC Link-layer Protocol (ALP): encapsulation of IP packets into PLPs, header compression, signaling.",
   ITU=C(["Report BT.2295", "BT.1869", "BT.1209"], "Multiplexing scheme for variable-length packets (BT.1869); service multiplex methods (BT.1209)."), TTA=C(["TTAK.KO-07.0150/R3"], "Inclusion in Part 3: Systems to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/331": dict(summary="LLS/SLS signaling, ROUTE/DASH and MMTP delivery, advanced emergency alerting (AEA), time synchronization.",
   ITU=C(["Report BT.2295", "BT.1300", "Report BT.2557", "BT.1774", "Report BT.2299"], "Transport/multiplex methods (BT.1300), MMT-based Smart Media Transport (Report BT.2557); public warning via broadcasting (BT.1774, Report BT.2299)."),
   TTA=C(["TTAK.KO-07.0150/R3", "TTAK.KO-07.0142/R4", "TTAK.KO-07.0140"], "Part 3: Systems (revised Dec 2024); emergency alert implementation guide and requirements."),
   SBTVD=C((), "TV 3.0 transport layer (ROUTE/DASH) specification to be confirmed."),
   verdict=V("partial", "Korean operating profile of ROUTE/DASH and MMT is restricted; emergency alerting is extended in separate standards."),
   impact="Mandatory delivery protocols and the AEAT handling scope differ by country.",
   recommendation="Compare the mandatory signaling tables of Part 3 with the A/331 tables item by item."),
 "A/332": dict(summary="Electronic service guide (ESG) data model and delivery.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0150/R3"], "ESG provisions in Part 3 to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/333": dict(summary="Service usage reporting (consumption data messages).",
   ITU=ITU_NONE, TTA=C((), "No counterpart identified."), SBTVD=NONE, verdict=V("review", "Check whether the Korean IBB standard includes usage reporting.")),
 "A/334": dict(summary="Audio watermark for service recovery in redistribution scenarios.", ITU=ITU_NONE, TTA=C((), "No counterpart (within the reviewed set)."), SBTVD=NONE, verdict=V("none")),
 "A/335": dict(summary="Video watermark for service recovery in redistribution scenarios.", ITU=ITU_NONE, TTA=C((), "No counterpart (within the reviewed set)."), SBTVD=NONE, verdict=V("none")),
 "A/336": dict(summary="Recovery of interactive services using watermark-carried information.", ITU=ITU_NONE, TTA=C((), "No counterpart (within the reviewed set)."), SBTVD=NONE, verdict=V("none")),
 "A/337": dict(summary="Delivery of events (EventStream, emsg) to broadcaster applications.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0128/R3", "TTAK.KO-07.0150/R3"], "Event provisions in the IBB standard and Part 3 to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/338": dict(summary="Discovery and communication between the TV and companion devices.",
   ITU=C(["BT.2053", "BT.2075"], "IBB requirements and system specifications."),
   TTA=C(["TTAK.KO-07.0128/R3"], "Companion-screen provisions of the IBB standard."), SBTVD=NONE,
   verdict=V("review", "TTA IBB appears to follow the HbbTV 2.0 companion-screen approach, so protocols may differ from A/338.")),
 "A/339": dict(summary="Modification and erasure of audio watermarks.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/341": dict(summary="HEVC Main 10 video format, HDR (PQ/HLG), frame rates and resolution constraints.",
   ITU=C(["BT.2073", "BT.2020", "BT.2100", "Report BT.2390"], "Use of HEVC for UHDTV/HDTV broadcasting (BT.2073); UHDTV and HDR-TV image parameters; HDR report."),
   TTA=C(["TTAK.KO-07.0149/R1"], "Part 2: Components — HEVC adopted."),
   SBTVD=C((), "TV 3.0 adopts VVC (+LCEVC); HEVC not used."),
   verdict=V("partial", "TTA adopts HEVC (profile and HDR options to be compared); SBTVD differs (VVC)."),
   impact="Brazilian receivers are not compatible with the HEVC profile; HDR method and frame-rate constraints may also differ between Korea and the US.",
   recommendation="Compare the video constraint tables of Part 2 with A/341 Table 6.x."),
 "A/342 Part 1": dict(summary="Common audio system requirements (presentations, accessibility, dialogue enhancement).",
   ITU=C(["BS.2051", "BS.1770"], "Advanced sound systems; loudness."), TTA=C(["TTAK.KO-07.0149/R1"], "Audio clauses of Part 2: Components."), SBTVD=NONE, verdict=V("review")),
 "A/342 Part 2": dict(summary="Dolby AC-4 audio system.",
   ITU=ITU_NONE, TTA=C((), "AC-4 not adopted: MSIT Notice 2023-34 Art. 13 ①4 mandates MPEG-H (ISO/IEC 23008-3, LC profile) only."), SBTVD=C((), "TV 3.0 adopts MPEG-H; AC-4 not adopted."),
   verdict=V("diff", "Korea and Brazil both adopt MPEG-H only, not AC-4."),
   impact="AC-4 decoders in US-oriented receiver chipsets are unnecessary in Korea/Brazil, while MPEG-H is mandatory."),
 "A/342 Part 3": dict(summary="MPEG-H 3D Audio system.",
   ITU=C(["BS.2051", "BS.2088"], "Advanced sound systems; ADM/BW64."), TTA=C(["TTAK.KO-07.0149/R1"], "Part 2: Components — MPEG-H 3D Audio as the sole audio codec."),
   SBTVD=C((), "TV 3.0 audio: MPEG-H adopted."),
   verdict=V("partial", "All three regions adopt MPEG-H; profile/level and channel-configuration constraints to be compared.")),
 "A/343": dict(summary="IMSC1 (TTML) caption and subtitle format and delivery.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0149/R1"], "Caption provisions of Part 2 (Korean fonts, character codes) to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/344": dict(summary="HTML5-based Broadcaster Application runtime with WebSocket/REST APIs.",
   ITU=C(["BT.2053", "BT.2075", "BT.2037", "BT.1699", "Report BT.2267", "Report BT.2568"], "IBB requirements and systems; broadcast-oriented IBB applications (BT.2037); declarative application formats (BT.1699); application-oriented broadcasting report."),
   TTA=C(["TTAK.KO-07.0128/R3"], "Terrestrial UHD IBB service — HbbTV 2.0-based browser environment."),
   SBTVD=C((), "Ginga-based application environment."),
   verdict=V("diff", "Application runtimes differ: A/344 vs HbbTV 2.0 vs Ginga."),
   impact="Broadcaster applications are hard to reuse across countries and receiver browser requirements differ."),
 "A/345": dict(summary="VVC (H.266) video format.",
   ITU=C(["Report BT.2538"], "VVC multilayer-profile use cases for broadcasting; a draft new Recommendation on the use of VVC is in progress in WP 6B."),
   TTA=C((), "VVC not adopted: MSIT Notice 2023-34 Art. 13 ①3 mandates HEVC (ISO/IEC 23008-2, Main 10 / Scalable Main 10, Level 5.2) only."), SBTVD=C((), "TV 3.0 video: VVC (+LCEVC) adopted."),
   verdict=V("review", "SBTVD VVC specification and A/345 profiles to be compared; no TTA counterpart.")),
 "A/350": dict(summary="Guide to the link-layer protocol.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/351": dict(summary="Techniques for signaling, delivery and synchronization.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/360": dict(summary="Signaling signatures, certificates, application code signing, service protection.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0152"], "Part 5: Content Protection (June 2021)."), SBTVD=NONE,
   verdict=V("review", "The scope of Part 5 (content protection) may be narrower than A/360 (which also covers signaling signatures).")),
 "A/361": dict(summary="Recommended practice on security and content protection.", ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0152"], ""), SBTVD=NONE, verdict=V("review")),
 "A/362": dict(summary="Digital rights management for ATSC 3.0.", ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0152"], ""), SBTVD=NONE, verdict=V("review")),
 "A/370": dict(summary="Conversion of ATSC 3.0 services for redistribution.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/371": dict(summary="Delivery of ATSC 3.0 services for redistribution.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/380": dict(summary="Haptics for ATSC 3.0.", ITU=ITU_NONE, TTA=NONE, SBTVD=NONE, verdict=V("none")),
 "A/381": dict(summary="Use of ATSC 3.0 interactive content.", ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0128/R3"], ""), SBTVD=NONE, verdict=V("review")),
}

def official(doc_id, fallback):
    """Row label for rows anchored to a non-ATSC document: the official English title if the issuing body provides one, else the native title."""
    t = DOC_TITLES.get(doc_id)
    return (t.get("title_en") or t["title"]) if t else fallback

EXTRA_ROWS = [  # rows without an ATSC document anchor
 dict(id="(no ATSC document / monitoring)", category="s320", type="—", title=official("TTAK.KO-07.0154/R1", "TTAK.KO-07.0154/R1"), title_ko="",
      summary="Operational guideline for monitoring terrestrial UHD (ATSC 3.0) transmission systems.",
      cells=dict(ITU=ITU_NONE, ATSC=C((), "No ATSC standard; related material in A/327 guidelines."), TTA=C(["TTAK.KO-07.0154/R1"], "Terrestrial UHD system monitoring guideline (Dec 2023)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="(no ATSC document / 3DTV)", category="s340", type="—", title=official("TTAK.KO-07.0153", "TTAK.KO-07.0153"), title_ko="",
      summary="3DTV service over terrestrial UHDTV broadcasting.",
      cells=dict(ITU=C(["BT.2160"], "3DTV broadcasting features (reference)."), ATSC=C((), "No ATSC 3.0 standard."), TTA=C(["TTAK.KO-07.0153"], "Part 6: 3DTV (June 2021)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="(no ATSC document / closed signing)", category="s340", type="—", title="TV 3.0 — Closed signing", title_ko="",
      summary="Sign-language (closed signing) presentation for accessibility.",
      cells=dict(ITU=ITU_NONE, ATSC=C((), "No ATSC 3.0 standard."), TTA=C((), "No counterpart identified."), SBTVD=C(["ABNT NBR 25606:2025", "SBTVD OG-06"], "Closed signing standard and operational guideline.")),
      verdict=V("none", "SBTVD Forum-only provision.")),
 dict(id="(no ATSC document / receivers)", category="s300", type="—", title="Receivers", title_ko="",
      summary="Receiver requirements and minimum specifications.",
      cells=dict(ITU=C(["BT.2036"], "Reference receiving system for frequency planning."), ATSC=C((), "No single ATSC receiver standard (requirements spread across the A/300 series)."),
                 TTA=C(["TTAR-07.0022"], "Minimum technical specification for terrestrial UHD set-top boxes (technical report, 2017)."),
                 SBTVD=C(["ABNT NBR 25609:2025"], "TV 3.0 receiver standard (113 pp.).")),
      verdict=V("review")),
 dict(id="A/331 §NRT", category="datacast", type="Standard", title="Datacasting — NRT file and data delivery", title_ko="",
      summary="Non-real-time file delivery over ROUTE sessions and data service signaling. There is no dedicated ATSC datacasting standard; the NRT provisions of A/331 apply.",
      cells=dict(ITU=C(["Report BT.2295", "Report BT.2545"], "Inter-tower communications network for broadcasting and datacasting systems."), ATSC=C(["A/331:2026-04"], "Baseline (NRT/ROUTE clauses)."), TTA=C(["TTAK.KO-07.0150/R3"], "NRT provisions in Part 3: Systems to be confirmed."), SBTVD=NONE),
      verdict=V("review")),
 dict(id="(no ATSC document / RTK)", category="datacast", type="—", title=official("TTAK.KO-07.0165", "Broadcast RTK correction data service"), title_ko="",
      summary="Datacasting of RTK (real-time kinematic) correction signals and high-precision GNSS correction information over the terrestrial UHD broadcast network. The broadcast carries correction data for GNSS receivers; it does not use the broadcast signal itself for positioning.",
      cells=dict(ITU=ITU_NONE,
                 ATSC=C((), "No counterpart document."),
                 TTA=C(["TTAK.KO-07.0165", "TTAK.KO-07.0167", "TTAK.KO-07.0168"], "Broadcast RTK correction data service (June 2025); HP-GNSS correction information message structure and datagram IP tunneling (June 2025)."),
                 SBTVD=C((), "No counterpart identified.")),
      verdict=V("none", "TTA-only provision; no ATSC or SBTVD Forum counterpart."),
      evidence=[dict(org="TTA", doc="TTAK.KO-07.0165", clause="whole document", url=""), dict(org="TTA", doc="TTAK.KO-07.0167", clause="message structure", url=""), dict(org="TTA", doc="TTAK.KO-07.0168", clause="IP tunneling", url="")]),
 dict(id="ATSC BPS (in progress)", category="datacast", type="—", title="Broadcast Positioning System (BPS)", title_ko="",
      summary="Positioning and timing derived from the terrestrial broadcast signal itself (ATSC 3.0 signal as a PNT source, independent of GNSS). A different technology from RTK correction datacasting.",
      cells=dict(ITU=C((), "No published document. A Korean contribution on broadcast positioning is planned for WP 6A (September 2026 meeting, per the Korean ITU-R SG6 study-group agenda; not yet public)."),
                 ATSC=C((), "No published standard; BPS is in industry trials — formal standardization status to be confirmed."),
                 TTA=C((), "No counterpart document."),
                 SBTVD=C((), "No counterpart identified.")),
      verdict=V("review", "No published document in any of the four bodies; ATSC status to be confirmed.")),
 dict(id="(no ATSC document / TPEG)", category="datacast", type="—", title=official("TTAK.KO-07.0139", "TTAK.KO-07.0139"), title_ko="",
      summary="Requirements for traffic and travel information (TPEG-family) data services over the terrestrial UHD network.",
      cells=dict(ITU=ITU_NONE, ATSC=C((), "No counterpart (can be realized with NRT delivery)."), TTA=C(["TTAK.KO-07.0139"], "Requirements for terrestrial UHD traffic and travel information service (Dec 2019)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="A/331 §AEA", category="datacast", type="Standard", title="Emergency information datacasting", title_ko="",
      summary="Emergency information content (maps, evacuation information) delivered by datacasting in addition to AEAT alert messages.",
      cells=dict(ITU=C(["BT.1774", "Report BT.2299"], "Use of broadcast infrastructures for public warning (BT.1774); broadcasting for public warning, disaster mitigation and relief (Report BT.2299)."), ATSC=C(["A/331:2026-04"], "AEA messages and rich-media delivery."),
                 TTA=C(["TTAK.KO-07.0142/R4", "TTAK.KO-07.0156", "TTAK.KO-06.0523"], "Emergency alert implementation guide for dedicated receivers; emergency information service for community broadcasting; guideline for using disaster information."), SBTVD=NONE),
      verdict=V("partial", "AEAT basis is common, but TTA extends it with domestic service provisions (dedicated receivers, community broadcasting).")),
]

# Regulatory technical standards (national law), mapped clause-by-clause to ATSC documents. Quoted text is verbatim (Korean) or an excerpt (US).
REGULATIONS = [
  {"org": "TTA", "country": "Korea", "id": "MSIT Notice No. 2023-34, Article 13",
   "title": "방송표준방식 및 방송업무용 무선설비의 기술기준", "title_lang": "ko", "title_en": "",
   "issuer": "과학기술정보통신부 (Ministry of Science and ICT)", "effective": "2023-11-01",
   "url": "https://www.law.go.kr/admRulLsInfoP.do?admRulId=53476&efYd=0", "local": "docs/refs/KR_MSIT-Notice-2023-34_Art13.md",
   "note": "Article 13 (terrestrial UHD television) defines the broadcasting standard method by reference to the TTA terrestrial UHDTV transmission/reception standards; paragraph ③ defers anything not specified to ITU conditions.",
   "clauses": [
     {"ref": "Art. 13 ① 1", "text": "방송신호는 비디오 서비스 신호, 오디오 서비스 신호 또는 데이터 서비스 신호로 구성될 것", "maps": ["A/300"]},
     {"ref": "Art. 13 ① 2", "text": "방송신호의 표현 형식은 한국정보통신기술협회가 정한 \"지상파 UHDTV방송 송수신 정합 표준\"에서 규정하는 내용을 따를 것", "maps": ["A/300", "A/343"]},
     {"ref": "Art. 13 ① 3", "text": "비디오 신호의 압축 조건은 … ISO/IEC 23008-2의 Main 10 Profile 또는 Scalable Main 10 Profile, Main tier, Level 5.2의 내용을 따를 것", "maps": ["A/341"]},
     {"ref": "Art. 13 ① 4", "text": "오디오 신호의 압축 조건은 … ISO/IEC 23008-3의 LC(low complexity) Profile, Level 1, 2 또는 3의 내용을 따를 것", "maps": ["A/342 Part 1", "A/342 Part 3"]},
     {"ref": "Art. 13 ① 5", "text": "다중화: 컴포넌트들을 하나의 프로그램 채널로 다중화; 전송채널(6㎒ 폭)에 적어도 하나의 4K UHDTV 프로그램 채널 포함; 다중화의 기술적 조건은 TTA 표준의 IP(Internet Protocol) 기반 다중화 방법을 따를 것", "maps": ["A/330", "A/331"]},
     {"ref": "Art. 13 ① 6", "text": "오류정정 방식은 LDPC+BCH, LDPC+CRC32, LDPC 중 한 가지; 변조방식은 QAM(QPSK 포함)으로 하며 변조 규격은 TTA 표준에서 규정한 방식", "maps": ["A/322"]},
     {"ref": "Art. 13 ① 7", "text": "전송방식은 OFDM 방식으로 하며, 전송 프레임, 전송 다중화 방식, 부트스트랩 등의 송신 규격은 TTA 표준에서 규정한 방식으로 할 것", "maps": ["A/321", "A/322"]},
     {"ref": "Art. 13 ② 1–10", "text": "무선설비 기술적 조건: 주파수허용편차(SFN ±2.1 Hz), 전파형식 D7W·점유대역폭 6 ㎒, 대역외 발사강도(별표 20·21), 스퓨리어스(별표 22), PAPR ≤ 13 ㏈, MER ≥ 27 ㏈, 편파면, 실효복사전력, 안테나 지향특성", "maps": ["A/322", "A/324"]},
     {"ref": "Art. 13 ② 11", "text": "지상파 방송사업자가 콘텐츠 보호기술을 도입하고자 하는 경우 … 수상기 제조사와 협의를 거쳐 지상파 UHDTV 방송을 시청할 수 있는 조치가 수반된 경우에 한할 것", "maps": ["A/360", "A/361", "A/362"]},
     {"ref": "Art. 13 ③", "text": "이 기준에 규정되지 않은 지상파 초고화질 텔레비전 방송업무에 대한 기술적 특성은 국제전기통신연합에서 정한 조건에 따를 것", "maps": []},
   ]},
  {"org": "ATSC", "country": "United States", "id": "47 CFR § 73.682(f)",
   "title": "TV transmission standards — Next Gen TV transmission standard", "title_lang": "en", "title_en": "",
   "issuer": "Federal Communications Commission (FCC)", "effective": "",
   "url": "https://www.ecfr.gov/current/title-47/section-73.682", "local": "docs/refs/US_47CFR-73.682f.md",
   "note": "Incorporates ATSC A/321:2016 and A/322:2017 by reference (§ 73.8000); other ATSC 3.0 layers are not mandated by rule.",
   "clauses": [
     {"ref": "§ 73.682(f)", "text": "Transmission of Next Gen TV broadcast television (ATSC 3.0) signals shall comply with ATSC A/321:2016 \"System Discovery and Signaling\" (March 23, 2016) and ATSC A/322:2017 \"Physical Layer Protocol\" (June 6, 2017), incorporated by reference (§ 73.8000). Compliance with A/322:2017 for free over-the-air primary video programming sunsets on July 17, 2027.", "maps": ["A/321", "A/322"]},
   ]},
  {"org": "SBTVD", "country": "Brazil", "id": "Decreto nº 12.595, de 27 de agosto de 2025",
   "title": "Dispõe sobre a escolha do padrão tecnológico da segunda geração do Sistema Brasileiro de Televisão Digital Terrestre, denominada TV 3.0, e sobre a sua implantação no território nacional.", "title_lang": "pt", "title_en": "",
   "issuer": "Presidência da República", "effective": "2025-08-28",
   "url": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/decreto/D12595.htm", "local": "docs/refs/BR_Decreto-12595-2025_and_Anatel-Ato-2705-2026.md",
   "note": "Signed 27 Aug 2025, published in the DOU on 28 Aug 2025. Adopts the ATSC 3.0 physical-layer signal standard for TV 3.0 (Art. 3º) with MIMO, LDM and TxID; technical specifications are drafted by Fórum SBTVD and standardized by ABNT (Art. 3º §1º–§2º). Art. 5º lists the system characteristics; Art. 2º of Decreto 11.484/2023 is revoked.",
   "clauses": [
     {"ref": "Art. 3º, caput", "text": "A TV 3.0 adotará o padrão de sinais da camada física do sistema ATSC 3.0, e incorporará, entre outras, as seguintes inovações tecnológicas recomendadas pelo Fórum SBTVD: I - Múltiplas Entradas e Múltiplas Saídas – MIMO; II - Multiplexação por Divisão de Camadas – LDM; e III - Ferramenta de Identificação de Transmissor – TxID.", "maps": ["A/321", "A/322"]},
     {"ref": "Art. 3º, § 1º–§ 2º", "text": "O Fórum SBTVD elaborará as especificações técnicas a serem adotadas pela TV 3.0 … As especificações técnicas … serão normatizadas pela ABNT.", "maps": ["A/300"]},
     {"ref": "Art. 5º", "text": "O padrão tecnológico da TV 3.0 possibilitará: qualidade audiovisual superior; recepção fixa, móvel e portátil; integração entre radiodifusão e internet com interação entre dispositivos; interface baseada em catálogo de aplicativos; segmentação e personalização de conteúdo; uso otimizado do espectro; multiprogramação aprimorada; transmissão de dados como serviço de valor adicionado.", "maps": ["A/300", "A/344", "A/338"]},
   ]},
  {"org": "SBTVD", "country": "Brazil", "id": "Anatel Ato nº 2.705, de 24 de fevereiro de 2026",
   "title": "Requisitos técnicos provisórios para avaliação da conformidade de transmissores e retransmissores da segunda geração do SBTVD-T – TV 3.0", "title_lang": "pt", "title_en": "",
   "issuer": "Agência Nacional de Telecomunicações (Anatel)", "effective": "2026-02-25",
   "url": "https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2026/2124-ato-2705", "local": "docs/refs/BR_Decreto-12595-2025_and_Anatel-Ato-2705-2026.md",
   "note": "Signed 24 Feb 2026, published in the Boletim de Serviço on 25 Feb 2026 (in force on publication). Provisional conformity-assessment requirements for TV 3.0 transmitters: the physical layer shall implement ATSC 3.0 per ATSC A/321:2025-07, A/322:2025-07a and A/324:2025-07 (item 4.1); emission mask per RCC-SRA (item 5.8.2); MER of at least 30 dB (item 5.9.2). Definitive requirements under Consulta Pública nº 10/2026.",
   "clauses": [
     {"ref": "Anexo, item 4.1", "text": "Os equipamentos básicos de transmissão da camada física (Over-the-Air Physical Layer) da TV 3.0, compreendendo transmissores e retransmissores, devem implementar o padrão ATSC 3.0, em conformidade com as normas ATSC A/321:2025-07, ATSC A/322:2025-07a e ATSC A/324:2025-07 …", "maps": ["A/321", "A/322", "A/324"]},
     {"ref": "Anexo, item 5.8.2", "text": "Requisito: o equipamento deve atender à máscara de emissão estabelecida nos Requisitos Técnicos de Condições de Uso de Radiofrequências aplicáveis aos Serviços de Radiodifusão de Sons e Imagens, de Retransmissão de Televisão e ao Serviço de Acesso Condicionado.", "maps": ["A/322"]},
     {"ref": "Anexo, item 5.9.2", "text": "Taxa de Erro de Modulação (MER) — Requisito: considera-se aceitável um valor de pelo menos 30 dB medido na saída do filtro de RF do transmissor.", "maps": ["A/322"]},
   ]},
  {"org": "SBTVD", "country": "Brazil", "id": "Portaria MCom nº 10.693, de 5 de outubro de 2023 · Anatel Resolução nº 789/2026",
   "title": "Diretrizes complementares para a canalização, cobertura do serviço e harmonização de faixas de frequência para implantação da TV 3.0 · PDFF / RCC-SRA", "title_lang": "pt", "title_en": "",
   "issuer": "Ministério das Comunicações · Anatel", "effective": "2023-10-05 · 2026-07-06",
   "url": "https://www.in.gov.br/web/dou/-/portaria-mcom-n-10.693-de-5-de-outubro-de-2023", "local": "",
   "note": "Spectrum and channelization framework: primary and exclusive allocation of high-VHF (174–216 MHz) and UHF (470–608, 614–698 MHz) to broadcasting for TV 3.0; channel plan updated by Anatel Resolução nº 789/2026 (PDFF and RCC-SRA). No clause mapped to an ATSC document.",
   "clauses": []},
]
REG_BY_DOC = {}
for reg in REGULATIONS:
    for cl in reg["clauses"]:
        for doc in cl["maps"]:
            REG_BY_DOC.setdefault(doc, []).append({"org": reg["org"], "id": reg["id"], "ref": cl["ref"], "text": cl["text"]})

# SBTVD Forum / ABNT counterparts per ATSC document (TV 3.0 series ABNT NBR 25601–25609:2025 and Fórum SBTVD Operational Guidelines).
SBTVD_MAP = {
 "A/300": C((), "TV 3.0 is specified as the ABNT NBR 25601–25609:2025 series (physical layer, transport, video, audio, captions, closed signing, EWS, application coding, receivers); no single umbrella document identified."),
 "A/321": C(["ABNT NBR 25601:2025", "SBTVD OG-01"], "ATSC 3.0 physical layer adopted by decree; transmitters must implement A/321:2025-07 (Anatel Ato 2.705/2026)."),
 "A/322": C(["ABNT NBR 25601:2025", "SBTVD OG-01"], "ATSC 3.0 physical layer with MIMO, LDM and TxID (Decreto 12.595/2025 Art. 3º); A/322:2025-07a required for transmitters."),
 "A/324": C(["ATSC A/324:2025-07 (incorporated by reference)"], "Required for TV 3.0 transmitters and retransmitters by Anatel Ato 2.705/2026, item 4.1; no separate ABNT document."),
 "A/325": C(["TV 3.0 Phase 3 PL lab report"], "Fórum SBTVD Phase 2/3 laboratory test reports (2021, 2023)."),
 "A/326": C(["TV 3.0 Phase 3 PL field report"], "Fórum SBTVD Phase 2/3 field test reports (2021, 2024)."),
 "A/330": C(["ABNT NBR 25602:2025", "SBTVD OG-02"], "Transport layer standard; ALP inclusion to be confirmed."),
 "A/331": C(["ABNT NBR 25602:2025", "SBTVD OG-02"], "Transport layer standard and operational guideline."),
 "A/332": C(["ABNT NBR 25602:2025"], "ESG provisions to be confirmed."),
 "A/333": C(["ABNT NBR 25602:2025"], "Usage reporting provisions to be confirmed."),
 "A/337": C(["ABNT NBR 25608:2025", "SBTVD OG-08"], "Application coding standard; event delivery to be confirmed."),
 "A/338": C(["ABNT NBR 25608:2025"], "Companion-device provisions to be confirmed."),
 "A/341": C(["ABNT NBR 25603:2025", "SBTVD OG-03"], "TV 3.0 video coding adopts VVC (+LCEVC); HEVC not used."),
 "A/342 Part 1": C(["ABNT NBR 25604:2025", "SBTVD OG-04"], "Audio coding standard and operational guideline."),
 "A/342 Part 2": C(["ABNT NBR 25604:2025"], "TV 3.0 adopts MPEG-H; AC-4 not adopted."),
 "A/342 Part 3": C(["ABNT NBR 25604:2025", "SBTVD OG-04"], "TV 3.0 audio: MPEG-H adopted."),
 "A/343": C(["ABNT NBR 25605:2025", "SBTVD OG-05"], "Closed captioning standard and operational guideline."),
 "A/344": C(["ABNT NBR 25608:2025", "SBTVD OG-08"], "Ginga-based application coding (528 pp.)."),
 "A/345": C(["ABNT NBR 25603:2025", "SBTVD OG-03"], "TV 3.0 video coding: VVC (+LCEVC)."),
 "A/360": C((), "Security provisions not identified as a separate document; to be checked in ABNT NBR 25602/25608/25609."),
 "A/381": C(["SBTVD OG-08"], "Application coding operational guideline."),
}
SBTVD_EXTRA = {  # by row title for rows without an ATSC anchor
 "Datacasting — NRT file and data delivery": C(["ABNT NBR 25602:2025", "SBTVD OG-CPC (draft)"], "Transport layer; Common Public Communication / Digital Government platform guideline (draft, Aug 2026)."),
 "Emergency information datacasting": C(["ABNT NBR 25607:2025", "SBTVD OG-07 v1"], "Emergency warning system standard and operational guideline (v1, June 2026)."),
}
VERDICT_OVERRIDE = {
 "A/321": V("partial", "Korea (TTA Part 4) and Brazil (ABNT NBR 25601, Anatel Ato 2.705 referencing A/321:2025-07) both adopt the ATSC 3.0 bootstrap; wake-up bit usage to be confirmed."),
 "A/322": V("partial", "Both Korea and Brazil adopt the ATSC 3.0 physical layer; Korea restricts operating parameters (6 MHz), Brazil mandates MIMO, LDM and TxID by decree."),
 "A/324": V("partial", "Brazil requires A/324:2025-07 for transmitters; Korean STL/SFN provisions in Part 4 to be compared."),
 "A/341": V("partial", "TTA adopts HEVC (profile and HDR options to be compared); SBTVD Forum differs (VVC +LCEVC, ABNT NBR 25603)."),
 "A/344": V("diff", "Application runtimes differ: A/344 Broadcaster Application vs HbbTV 2.0-based IBB (TTA) vs Ginga (ABNT NBR 25608)."),
 "A/345": V("review", "SBTVD VVC specification (ABNT NBR 25603) and A/345 profiles to be compared; no TTA counterpart."),
}

rows = []
for r in US:
    doc, m = r["doc_id"], MAP.get(r["doc_id"])
    if not m or series_of(doc) is None: continue
    is_rp = r["filename"].startswith("RP/")
    sb = SBTVD_MAP.get(doc, m["SBTVD"])
    cells = {"ITU": dict(m["ITU"]), "ATSC": C([f"{doc}:{r['version_date'][:7]}"], "Baseline document" + (" (Recommended Practice)" if is_rp else "")), "TTA": dict(m["TTA"]), "SBTVD": dict(sb)}
    if doc in VERDICT_OVERRIDE: m = dict(m, verdict=VERDICT_OVERRIDE[doc])
    for rg in REG_BY_DOC.get(doc, []):
        cells[rg["org"]].setdefault("reg", []).append(rg)
    rows.append(dict(id=doc, category=series_of(doc), type="RP" if is_rp else "Standard", title=r["title"], title_ko="", summary=m["summary"],
                     cells=cells, verdict=m["verdict"], impact=m.get("impact", ""), recommendation=m.get("recommendation", ""), evidence=[], review=dict(REVIEW)))
for e in EXTRA_ROWS:
    if e["title"] in SBTVD_EXTRA: e["cells"]["SBTVD"] = dict(SBTVD_EXTRA[e["title"]])
    for rg in REG_BY_DOC.get(e["id"], []):
        e["cells"][rg["org"]].setdefault("reg", []).append(rg)
    e.setdefault("impact", ""); e.setdefault("recommendation", ""); e.setdefault("evidence", []); e["review"] = dict(REVIEW); rows.append(e)
# ---- Per-country verdicts (TTA vs ATSC, SBTVD vs ATSC), mapping relations and confidence ----------------------------
# Explicit values for the rows examined so far; everything else is derived from the cell contents below.
PER_ORG = {  # doc id -> {org: (code, text, none-kind)}
 "A/300": {"TTA": ("review", "TTA Part 1 plays the role of system requirements; clause-level comparison pending"), "SBTVD": ("review", "System specified as the ABNT NBR 25601–25609 series; no umbrella document")},
 "A/321": {"TTA": ("profile", "TTA §10 is a translation of A/321:2016 §4–6: bootstrap structure and major-version-0 signaling identical (6 MHz selected nationally). A/321:2026 additions (major version 1, heterogeneous-waveform multiplexing) not yet carried over — no effect on ATSC 3.0 services"), "SBTVD": ("profile", "A/321:2025-07 incorporated by reference (Anatel Ato 2.705/2026 item 4.1); identical for ATSC 3.0 frames; 2026-04 Amd 1 not yet referenced; ABNT NBR 25601 profile unverified")},
 "A/322": {"TTA": ("profile", "TTA §5–9/Annex I-1 translate A/322 (2020 text + 2024 MIMO extension) and select the 6 MHz option by regulation: FEC, constellations, FFT/GI/pilots, frequency interleaver identical. Open item: Table Ⅰ.10-5 still lists MP4_2 at 32K/GI6_1536 (removed by A/322:2025-07a Amd 1)"), "SBTVD": ("profile", "A/322:2025-07a incorporated by reference; national profile selects 6 MHz and mandates MIMO, LDM and TxID (Decreto 12.595/2025 Art. 3º). January/June 2026 amendments not yet referenced; ABNT profile unverified")},
 "A/323": {"TTA": ("none", "", "not-found"), "SBTVD": ("none", "", "not-found")},
 "A/324": {"TTA": ("review", "Gateway/exciter functions in Part 4; STLTP adoption and SFN rules to be compared"), "SBTVD": ("review", "A/324:2025-07 incorporated by reference (Anatel Ato 2.705/2026 item 4.1); changes between A/324:2025-07 and the baseline A/324:2026-04 not yet compared")},
 "A/331": {"TTA": ("partial", "Part 3 restricts the ROUTE/DASH and MMT profile; emergency alerting extended in national standards"), "SBTVD": ("review", "ABNT NBR 25602 transport layer — clause comparison pending (ABNT clause unverified)")},
 "A/341": {"TTA": ("partial", "HEVC mandated (MSIT Notice Art. 13 ①3: Main 10 / Scalable Main 10, Level 5.2); HDR and frame-rate constraints to be compared"), "SBTVD": ("diff", "VVC (+LCEVC) adopted instead of HEVC (ABNT NBR 25603)")},
 "A/342 Part 1": {"TTA": ("review", "Audio clauses of Part 2 to be compared"), "SBTVD": ("review", "ABNT NBR 25604 — clause comparison pending (ABNT clause unverified)")},
 "A/342 Part 2": {"TTA": ("none", "AC-4 not adopted (MSIT Notice Art. 13 ①4 mandates MPEG-H only)", "not-adopted"), "SBTVD": ("none", "AC-4 not adopted (MPEG-H selected for TV 3.0)", "not-adopted")},
 "A/342 Part 3": {"TTA": ("partial", "MPEG-H LC profile, Level 1–3 mandated (MSIT Notice Art. 13 ①4); profile/level table vs A/342-3 to be compared"), "SBTVD": ("partial", "MPEG-H adopted (ABNT NBR 25604); profile constraints unverified")},
 "A/343": {"TTA": ("review", "Caption provisions of Part 2 (Korean fonts, character codes) to be compared"), "SBTVD": ("review", "ABNT NBR 25605 closed captioning — clause comparison pending")},
 "A/344": {"TTA": ("diff", "HbbTV 2.0-based IBB (TTAK.KO-07.0128/R3) instead of the A/344 Broadcaster Application"), "SBTVD": ("diff", "Ginga-based application coding (ABNT NBR 25608) instead of A/344")},
 "A/345": {"TTA": ("none", "VVC not adopted (MSIT Notice Art. 13 ①3 mandates HEVC only)", "not-adopted"), "SBTVD": ("review", "VVC adopted (ABNT NBR 25603); profile alignment with A/345 to be compared")},
 "A/360": {"TTA": ("review", "Part 5 content protection — scope vs A/360 (signaling signatures) to be compared"), "SBTVD": ("review", "Security provisions to be located in ABNT NBR 25602/25608/25609")},
}
RELS = {  # doc id -> {org: (relation, confidence)}
 "A/321": {"TTA": ("profile", "confirmed"), "SBTVD": ("incorporated", "partial")},
 "A/322": {"TTA": ("profile", "confirmed"), "SBTVD": ("incorporated", "partial")},
 "A/324": {"TTA": ("related", "metadata"), "SBTVD": ("incorporated", "confirmed")},
 "A/331": {"TTA": ("profile", "metadata"), "SBTVD": ("related", "metadata")},
 "A/341": {"TTA": ("profile", "partial"), "SBTVD": ("alternative", "confirmed")},
 "A/342 Part 1": {"TTA": ("profile", "metadata"), "SBTVD": ("related", "metadata")},
 "A/342 Part 2": {"TTA": ("alternative", "confirmed"), "SBTVD": ("alternative", "confirmed")},
 "A/342 Part 3": {"TTA": ("profile", "partial"), "SBTVD": ("profile", "metadata")},
 "A/343": {"TTA": ("related", "metadata"), "SBTVD": ("related", "metadata")},
 "A/344": {"TTA": ("alternative", "partial"), "SBTVD": ("alternative", "confirmed")},
 "A/345": {"TTA": ("alternative", "confirmed"), "SBTVD": ("related", "metadata")},
 "A/360": {"TTA": ("related", "metadata"), "SBTVD": ("related", "unverified")},
}
def derive(cell, org, doc_id):
    """Default per-country verdict from the cell contents when no explicit value is given."""
    note = (cell.get("note") or "").lower()
    if cell["docs"]:
        return V("review", "Counterpart document identified; clause-level comparison pending")
    if "not adopted" in note: return V("none", cell.get("note", ""), "not-adopted")
    if "no counterpart" in note or "not identified" in note or "no ats" in note: return V("none", cell.get("note", ""), "not-found")
    if cell.get("reg"): return V("review", "Regulatory reference only; standard document to be identified")
    return V("none", "", "pending")
for r in rows:
    r["verdicts"] = {}
    for org in ("TTA", "SBTVD"):
        cell = r["cells"].get(org) or C()
        spec = PER_ORG.get(r["id"], {}).get(org)
        r["verdicts"][org] = V(*spec) if spec else derive(cell, org, r["id"])
        rel, conf = RELS.get(r["id"], {}).get(org, (None, None))
        if rel: cell["rel"] = rel
        if conf: cell["conf"] = conf
        if "rel" not in cell:
            code = r["verdicts"][org]["code"]
            cell["rel"] = {"same": "incorporated", "partial": "profile", "diff": "alternative", "review": "related"}.get(code, "") if cell["docs"] else ""
        if "conf" not in cell and cell["docs"]:
            cell["conf"] = "metadata"
    if r["cells"].get("ITU", {}).get("docs"):
        r["cells"]["ITU"].setdefault("rel", "reference"); r["cells"]["ITU"].setdefault("conf", "metadata")
    r["cells"]["ATSC"].setdefault("rel", "baseline"); r["cells"]["ATSC"].setdefault("conf", "confirmed")
    # 'ABNT clause unverified' flag: Brazilian mappings that rest on paid ABNT standards we have not read
    sb = r["cells"].get("SBTVD", {})
    if any(d.startswith("ABNT NBR") for d in sb.get("docs", [])) and sb.get("conf") in (None, "metadata", "unverified"):
        sb["flag"] = "ABNT clause unverified"

# ---- Feature-level comparisons (clause/table evidence) from data/comparisons/*.json, attached to rows by ATSC doc id ---
COMPARISONS = []
for cf in sorted((ROOT / "data" / "comparisons").glob("*.json")):
    COMPARISONS.extend(json.load(open(cf, encoding="utf-8")))
by_doc = {}
for cmp in COMPARISONS:
    for doc in cmp.get("atsc_docs", []):
        by_doc.setdefault(doc, []).append(cmp)
for r in rows:
    if r["id"] in by_doc:
        r["comparisons"] = by_doc[r["id"]]

order = {c["id"]: i for i, c in enumerate(CATEGORIES)}
rows.sort(key=lambda x: (order[x["category"]], not x["id"].startswith("A/"), x["type"] == "RP", x["id"]))  # ATSC-anchored rows first

data = {
  "meta": {
    "title": "ATSC 3.0 Common Ground",
    "subtitle": "One Standard. Connected Worldwide.",
    "purpose": "Using the US ATSC 3.0 standards (A/300 series) as the baseline, this page maps each ATSC document to the corresponding ITU-R Recommendations/Reports, Korean TTA terrestrial UHDTV standards and Brazilian SBTVD Forum TV 3.0 specifications, and records the differences.",
    "baseline": "ATSC", "scope": "ATSC 3.0 Standards and Recommended Practices of the A/300 series listed on atsc.org (34 documents) plus datacasting services without a dedicated ATSC document.",
    "updated": TODAY,
  },
  "orgs": [
    {"id": "ITU", "label": "ITU-R", "sub": "International · BT/BS-series Recommendations and Reports", "color": "#1a73b5"},
    {"id": "ATSC", "label": "ATSC", "sub": "United States · ATSC 3.0 (baseline) · FCC 47 CFR § 73.682(f)", "color": "#3b4a63"},
    {"id": "TTA", "label": "TTA", "sub": "Korea · Terrestrial UHDTV standards · MSIT Notice 2023-34 Art. 13", "color": "#0f7c82"},
    {"id": "SBTVD", "label": "SBTVD Forum", "sub": "Brazil · TV 3.0 · MCom/Anatel regulation", "color": "#6b5e3a"}
  ],
  "regulations": REGULATIONS,
  "verdicts": {
    "same":    {"icon": "✓", "label": "Same", "desc": "Clause- and table-level comparison done against the baseline version: no relevant difference (legal incorporation alone does not qualify)"},
    "profile": {"icon": "◐", "label": "Adopted · national profile", "desc": "The ATSC document is adopted as defined; the country selects among the options and parameters the document itself permits (bandwidth, optional tools, mandated features)"},
    "partial": {"icon": "△", "label": "Partial match", "desc": "Core is the same but the content differs: missing or stale clauses, errata not reflected, or constraints beyond the ATSC options"},
    "diff":    {"icon": "≠", "label": "Different", "desc": "A different technology or specification is adopted"},
    "none":    {"icon": "—", "label": "No counterpart", "desc": "No corresponding provision, or not identified"},
    "review":  {"icon": "ⓘ", "label": "Review needed", "desc": "Counterpart documents identified; clause-level comparison pending"}
  },
  "categories": CATEGORIES,
  "relations": RELATIONS, "confidence": CONFIDENCE, "noneKinds": NONE_KINDS,
  "comparisons": COMPARISONS,
  "docTitles": DOC_TITLES,
  "rows": rows,
}
out = ROOT / "data/standards.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "data/standards.js").write_text("window.STANDARDS_DATA = " + json.dumps(data, ensure_ascii=False) + ";" + chr(10), encoding="utf-8")
print(f"wrote {out}: {len(rows)} rows, {len(CATEGORIES)} categories, {len(DOC_TITLES)} document titles")
