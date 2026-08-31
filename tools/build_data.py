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
            DOC_TITLES[sid] = {"title": it["korStandard"].strip(), "lang": "ko", "title_en": (it.get("engStandard") or "").strip()}
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
for folder, lang in (("ITU", "en"), ("BR", "pt")):  # agent-produced indexes: ITU (English), SBTVD (Portuguese)
    p = ROOT / "standards" / folder / "index.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            if r.get("doc_id") and r.get("title"):
                DOC_TITLES[r["doc_id"].strip()] = {"title": r["title"].strip(), "lang": lang, "title_en": r["title"].strip() if lang == "en" else ""}

TODAY = "2026-08-31"
REVIEW = {"status": "draft", "by": "", "updated": TODAY}

def series_of(doc_id):
    m = re.match(r"A/(\d)(\d)(\d)", doc_id)
    if not m: return "other"
    h, t = m.group(1), m.group(2)
    if h == "2" or (h == "3" and t == "0"): return "s300"
    return {"2": "s320", "3": "s330", "4": "s340", "5": "s350", "6": "s360", "7": "s370", "8": "s380"}.get(t, "other")

CATEGORIES = [
    {"id": "s300", "name": "A/200–A/300 · System", "desc": "System architecture and umbrella documents"},
    {"id": "s320", "name": "A/320 series · Physical Layer", "desc": "Bootstrap, physical layer protocol, return channel, STL, PHY test plans"},
    {"id": "s330", "name": "A/330 series · Management and Protocols", "desc": "Link layer, signaling/delivery, ESG, usage reporting, watermarks, app events, companion devices"},
    {"id": "s340", "name": "A/340 series · Presentation", "desc": "Video, audio, captions, interactive content"},
    {"id": "s350", "name": "A/350 series · Recommended Practices (Protocols)", "desc": "Guides to link layer and signaling/delivery"},
    {"id": "s360", "name": "A/360 series · Security", "desc": "Security, service protection, DRM"},
    {"id": "s370", "name": "A/370 series · Redistribution", "desc": "Conversion and delivery of ATSC 3.0 services for redistribution"},
    {"id": "s380", "name": "A/380 series · Haptics and Interactive Use", "desc": ""},
    {"id": "datacast", "name": "Datacasting services", "desc": "Data services carried over the broadcast; anchored to A/331 NRT delivery where applicable (no dedicated ATSC standard for RTK — ATSC BPS in progress)"},
]

V = lambda code, text="": {"code": code, "text": text}
C = lambda docs=(), note="": {"docs": list(docs), "note": note}
ITU_NONE, NONE = C(), C()

# Per-document mapping. Keys: ATSC doc id as in index.csv.
MAP = {
 "A/200": dict(summary="Regional service availability information.", ITU=ITU_NONE, TTA=C((), "No counterpart identified."), SBTVD=NONE, verdict=V("none")),
 "A/300": dict(summary="Top-level document defining the ATSC 3.0 system architecture and the relationship between the individual standards.",
   ITU=C(["Report BT.2295"], "Collection of DTTB system specifications (includes an ATSC 3.0 system description)."),
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
   ITU=C(["BT.1877", "BT.1306", "Report BT.2295"], "Listed as a second-generation system in Rec. BT.1877."),
   TTA=C(["TTAK.KO-07.0151/R1"], "Part 4: Physical Layer (revised Dec 2025). 6 MHz; defines broadcast gateway and exciter functions."),
   SBTVD=C((), "TV 3.0 physical layer (ATSC 3.0 PHY-based) specification to be confirmed."),
   verdict=V("partial", "TTA adopts the ATSC 3.0 PHY but restricts it to Korean operating parameters (6 MHz etc.)."),
   impact="Transmission equipment (gateway, exciter) is largely compatible; operating profiles (PLP configuration, LDM use) need checking.",
   recommendation="Compare the mandatory/optional parameter tables of Part 4 with the A/322 annexes."),
 "A/323": dict(summary="Dedicated return channel over broadcast spectrum.", ITU=ITU_NONE, TTA=C((), "No counterpart (within the reviewed set)."), SBTVD=NONE,
   verdict=V("none", "Neither Korea nor Brazil specifies a dedicated return channel.")),
 "A/324": dict(summary="STLTP interface between the broadcast gateway (scheduler) and transmitters; timing and SFN synchronization.",
   ITU=ITU_NONE,
   TTA=C(["TTAK.KO-07.0151/R1", "TTAR-07.0026/R1"], "Part 4 defines gateway/exciter functions; technical report gives TxID/BSID assignment guidelines."),
   SBTVD=NONE, verdict=V("review", "Adoption of STLTP and Korean SFN operating rules to be compared.")),
 "A/325": dict(summary="Laboratory performance test plan for the ATSC 3.0 physical layer.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0157"], "Guideline for test methods of terrestrial UHD radio equipment (2022)."), SBTVD=NONE, verdict=V("review")),
 "A/326": dict(summary="Field test plan for ATSC 3.0.",
   ITU=C(["Report BT.2343"], "Collection of field trials of UHDTV over DTTB networks."), TTA=C(["TTAK.KO-07.0157"], ""), SBTVD=NONE, verdict=V("review")),
 "A/327": dict(summary="Guidelines for using the physical layer protocol.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0154/R1"], "Terrestrial UHD system monitoring guideline (related, not equivalent)."), SBTVD=NONE, verdict=V("review")),
 "A/330": dict(summary="ATSC Link-layer Protocol (ALP): encapsulation of IP packets into PLPs, header compression, signaling.",
   ITU=C(["Report BT.2295"], ""), TTA=C(["TTAK.KO-07.0150/R3"], "Inclusion in Part 3: Systems to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/331": dict(summary="LLS/SLS signaling, ROUTE/DASH and MMTP delivery, advanced emergency alerting (AEA), time synchronization.",
   ITU=C(["Report BT.2295", "BT.2090"], "BT.2090: emergency warning via DTTB."),
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
   ITU=C(["BT.2020", "BT.2100", "BT.709"], "UHDTV colorimetry, HDR-TV."),
   TTA=C(["TTAK.KO-07.0149/R1"], "Part 2: Components — HEVC adopted."),
   SBTVD=C((), "TV 3.0 adopts VVC (+LCEVC); HEVC not used."),
   verdict=V("partial", "TTA adopts HEVC (profile and HDR options to be compared); SBTVD differs (VVC)."),
   impact="Brazilian receivers are not compatible with the HEVC profile; HDR method and frame-rate constraints may also differ between Korea and the US.",
   recommendation="Compare the video constraint tables of Part 2 with A/341 Table 6.x."),
 "A/342 Part 1": dict(summary="Common audio system requirements (presentations, accessibility, dialogue enhancement).",
   ITU=C(["BS.2051", "BS.1770"], "Advanced sound systems; loudness."), TTA=C(["TTAK.KO-07.0149/R1"], "Audio clauses of Part 2: Components."), SBTVD=NONE, verdict=V("review")),
 "A/342 Part 2": dict(summary="Dolby AC-4 audio system.",
   ITU=ITU_NONE, TTA=C((), "AC-4 not adopted in the Korean standard."), SBTVD=C((), "TV 3.0 adopts MPEG-H; AC-4 not adopted."),
   verdict=V("diff", "Korea and Brazil both adopt MPEG-H only, not AC-4."),
   impact="AC-4 decoders in US-oriented receiver chipsets are unnecessary in Korea/Brazil, while MPEG-H is mandatory."),
 "A/342 Part 3": dict(summary="MPEG-H 3D Audio system.",
   ITU=C(["BS.2051", "BS.2088"], "Advanced sound systems; ADM/BW64."), TTA=C(["TTAK.KO-07.0149/R1"], "Part 2: Components — MPEG-H 3D Audio as the sole audio codec."),
   SBTVD=C((), "TV 3.0 audio: MPEG-H adopted."),
   verdict=V("partial", "All three regions adopt MPEG-H; profile/level and channel-configuration constraints to be compared.")),
 "A/343": dict(summary="IMSC1 (TTML) caption and subtitle format and delivery.",
   ITU=ITU_NONE, TTA=C(["TTAK.KO-07.0149/R1"], "Caption provisions of Part 2 (Korean fonts, character codes) to be confirmed."), SBTVD=NONE, verdict=V("review")),
 "A/344": dict(summary="HTML5-based Broadcaster Application runtime with WebSocket/REST APIs.",
   ITU=C(["BT.2053", "BT.2075", "Report BT.2267"], "IBB requirements, systems and report."),
   TTA=C(["TTAK.KO-07.0128/R3"], "Terrestrial UHD IBB service — HbbTV 2.0-based browser environment."),
   SBTVD=C((), "Ginga-based application environment."),
   verdict=V("diff", "Application runtimes differ: A/344 vs HbbTV 2.0 vs Ginga."),
   impact="Broadcaster applications are hard to reuse across countries and receiver browser requirements differ."),
 "A/345": dict(summary="VVC (H.266) video format.",
   ITU=C(["BT.[VVC] (draft)"], "Draft new Recommendation on the use of VVC in progress in WP 6B."),
   TTA=C((), "VVC not adopted in the Korean standard."), SBTVD=C((), "TV 3.0 video: VVC (+LCEVC) adopted."),
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
 dict(id="(no ATSC document)", category="s320", type="—", title=official("TTAK.KO-07.0154/R1", "TTAK.KO-07.0154/R1"), title_ko="",
      summary="Operational guideline for monitoring terrestrial UHD (ATSC 3.0) transmission systems.",
      cells=dict(ITU=ITU_NONE, ATSC=C((), "No ATSC standard; related material in A/327 guidelines."), TTA=C(["TTAK.KO-07.0154/R1"], "Terrestrial UHD system monitoring guideline (Dec 2023)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="(no ATSC document)", category="s340", type="—", title=official("TTAK.KO-07.0153", "TTAK.KO-07.0153"), title_ko="",
      summary="3DTV service over terrestrial UHDTV broadcasting.",
      cells=dict(ITU=C(["BT.2160"], "3DTV broadcasting features (reference)."), ATSC=C((), "No ATSC 3.0 standard."), TTA=C(["TTAK.KO-07.0153"], "Part 6: 3DTV (June 2021)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="A/331 §NRT", category="datacast", type="Standard", title="Datacasting — NRT file and data delivery", title_ko="",
      summary="Non-real-time file delivery over ROUTE sessions and data service signaling. There is no dedicated ATSC datacasting standard; the NRT provisions of A/331 apply.",
      cells=dict(ITU=C(["Report BT.2295"], ""), ATSC=C(["A/331:2026-04"], "Baseline (NRT/ROUTE clauses)."), TTA=C(["TTAK.KO-07.0150/R3"], "NRT provisions in Part 3: Systems to be confirmed."), SBTVD=NONE),
      verdict=V("review")),
 dict(id="ATSC BPS (in progress)", category="datacast", type="—", title=official("TTAK.KO-07.0165", "Broadcast RTK correction data service"), title_ko="",
      summary="Datacasting of RTK (real-time kinematic) correction signals and high-precision GNSS correction information over the terrestrial UHD broadcast network. Different approach from ATSC BPS, which uses the broadcast signal itself for positioning.",
      cells=dict(ITU=C(["WP 6A contribution: Broadcast Positioning System (Sept 2026, planned)"], "Contributions on broadcast positioning in progress."),
                 ATSC=C((), "No published standard — Broadcast Positioning System (BPS) standardization in progress."),
                 TTA=C(["TTAK.KO-07.0165", "TTAK.KO-07.0167", "TTAK.KO-07.0168"], "Broadcast RTK correction data service (June 2025); HP-GNSS correction information message structure and datagram IP tunneling (June 2025)."),
                 SBTVD=C((), "No counterpart identified.")),
      verdict=V("diff", "TTA leads standardization of RTK/HP-GNSS correction datacasting; ATSC is pursuing BPS."),
      impact="Korean RTK datacasting can operate independently of ATSC standards; alignment may be needed once BPS is published.",
      recommendation="Present TTAK.KO-07.0165–0168 as reference documents in the ITU-R WP 6A BPS discussion.",
      evidence=[dict(org="TTA", doc="TTAK.KO-07.0165", clause="whole document", url=""), dict(org="TTA", doc="TTAK.KO-07.0167", clause="message structure", url=""), dict(org="TTA", doc="TTAK.KO-07.0168", clause="IP tunneling", url="")]),
 dict(id="(no ATSC document)", category="datacast", type="—", title=official("TTAK.KO-07.0139", "TTAK.KO-07.0139"), title_ko="",
      summary="Requirements for traffic and travel information (TPEG-family) data services over the terrestrial UHD network.",
      cells=dict(ITU=ITU_NONE, ATSC=C((), "No counterpart (can be realized with NRT delivery)."), TTA=C(["TTAK.KO-07.0139"], "Requirements for terrestrial UHD traffic and travel information service (Dec 2019)."), SBTVD=NONE),
      verdict=V("none", "TTA-only provision.")),
 dict(id="A/331 §AEA", category="datacast", type="Standard", title="Emergency information datacasting", title_ko="",
      summary="Emergency information content (maps, evacuation information) delivered by datacasting in addition to AEAT alert messages.",
      cells=dict(ITU=C(["BT.2090", "Report BT.2382"], "Emergency warning via DTTB."), ATSC=C(["A/331:2026-04"], "AEA messages and rich-media delivery."),
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
     {"ref": "Art. 13 ① 3", "text": "비디오 신호의 압축 조건은 … ISO/IEC 23008-2의 Main 10 Profile 또는 Scalable Main 10 Profile, Main tier, Level 5.2의 내용을 따를 것", "maps": ["A/341", "A/345"]},
     {"ref": "Art. 13 ① 4", "text": "오디오 신호의 압축 조건은 … ISO/IEC 23008-3의 LC(low complexity) Profile, Level 1, 2 또는 3의 내용을 따를 것", "maps": ["A/342 Part 1", "A/342 Part 2", "A/342 Part 3"]},
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
  {"org": "SBTVD", "country": "Brazil", "id": "TV 3.0 regulation (MCom / Anatel)",
   "title": "", "title_lang": "pt", "title_en": "", "issuer": "Ministério das Comunicações / Anatel", "effective": "",
   "url": "", "local": "", "note": "Regulatory instrument defining the TV 3.0 system to be added once the documents are collected (standards/BR/regulatory).",
   "clauses": []},
]
REG_BY_DOC = {}
for reg in REGULATIONS:
    for cl in reg["clauses"]:
        for doc in cl["maps"]:
            REG_BY_DOC.setdefault(doc, []).append({"org": reg["org"], "id": reg["id"], "ref": cl["ref"], "text": cl["text"]})

rows = []
for r in US:
    doc, m = r["doc_id"], MAP.get(r["doc_id"])
    if not m: continue
    is_rp = r["filename"].startswith("RP/")
    cells = {"ITU": dict(m["ITU"]), "ATSC": C([f"{doc}:{r['version_date'][:7]}"], "Baseline document" + (" (Recommended Practice)" if is_rp else "")), "TTA": dict(m["TTA"]), "SBTVD": dict(m["SBTVD"])}
    for rg in REG_BY_DOC.get(doc, []):
        cells[rg["org"]].setdefault("reg", []).append(rg)
    rows.append(dict(id=doc, category=series_of(doc), type="RP" if is_rp else "Standard", title=r["title"], title_ko="", summary=m["summary"],
                     cells=cells, verdict=m["verdict"], impact=m.get("impact", ""), recommendation=m.get("recommendation", ""), evidence=[], review=dict(REVIEW)))
for e in EXTRA_ROWS:
    e.setdefault("impact", ""); e.setdefault("recommendation", ""); e.setdefault("evidence", []); e["review"] = dict(REVIEW); rows.append(e)
order = {c["id"]: i for i, c in enumerate(CATEGORIES)}
rows.sort(key=lambda x: (order[x["category"]], x["type"] == "RP", x["id"]))

data = {
  "meta": {
    "title": "ATSC 3.0 Standards Comparison",
    "subtitle": "ITU-R · ATSC · TTA · SBTVD Forum",
    "purpose": "Using the US ATSC 3.0 standards (A/300 series) as the baseline, this page maps each ATSC document to the corresponding ITU-R Recommendations/Reports, Korean TTA terrestrial UHDTV standards and Brazilian SBTVD Forum TV 3.0 specifications, and records the differences.",
    "baseline": "ATSC", "scope": "ATSC 3.0 Standards and Recommended Practices listed on atsc.org (35 documents) plus datacasting services without a dedicated ATSC document.",
    "updated": TODAY,
    "highlights": [
      {"title": "Audio codec", "text": "ATSC specifies both AC-4 and MPEG-H (A/342 Parts 2 and 3); TTA adopted MPEG-H 3D Audio only, and SBTVD Forum also selected MPEG-H."},
      {"title": "Video codec", "text": "ATSC and TTA use HEVC (A/341) as the baseline and ATSC added VVC (A/345); SBTVD Forum adopted VVC (+LCEVC) from the start."},
      {"title": "Application platform", "text": "ATSC uses the A/344 Broadcaster Application, TTA an HbbTV 2.0-based IBB (TTAK.KO-07.0128/R3), and SBTVD Forum Ginga — three different runtimes."},
      {"title": "Datacasting · RTK", "text": "TTA standardized broadcast RTK correction data (TTAK.KO-07.0165) and HP-GNSS correction delivery (0167, 0168). ATSC's Broadcast Positioning System is still in progress; no SBTVD counterpart identified."}
    ]
  },
  "orgs": [
    {"id": "ITU", "label": "ITU-R", "sub": "International · BT/BS-series Recommendations and Reports", "color": "#1a73b5"},
    {"id": "ATSC", "label": "ATSC", "sub": "United States · ATSC 3.0 (baseline) · FCC 47 CFR § 73.682(f)", "color": "#3b4a63"},
    {"id": "TTA", "label": "TTA", "sub": "Korea · Terrestrial UHDTV standards · MSIT Notice 2023-34 Art. 13", "color": "#0f7c82"},
    {"id": "SBTVD", "label": "SBTVD Forum", "sub": "Brazil · TV 3.0 · MCom/Anatel regulation", "color": "#6b5e3a"}
  ],
  "regulations": REGULATIONS,
  "verdicts": {
    "same":    {"icon": "✓", "label": "Same", "desc": "Baseline (ATSC) provisions adopted as is"},
    "partial": {"icon": "△", "label": "Partial match", "desc": "Core is the same; profiles, options or constraints differ"},
    "diff":    {"icon": "≠", "label": "Different", "desc": "A different technology or specification is adopted"},
    "none":    {"icon": "—", "label": "No counterpart", "desc": "No corresponding provision, or not identified"},
    "review":  {"icon": "ⓘ", "label": "Review needed", "desc": "Counterpart documents identified; clause-level comparison pending"}
  },
  "categories": CATEGORIES,
  "docTitles": DOC_TITLES,
  "rows": rows,
}
out = ROOT / "data/standards.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "data/standards.js").write_text("window.STANDARDS_DATA = " + json.dumps(data, ensure_ascii=False) + ";" + chr(10), encoding="utf-8")
print(f"wrote {out}: {len(rows)} rows, {len(CATEGORIES)} categories, {len(DOC_TITLES)} document titles")
