# ATSC 3.0 표준 비교 대시보드 (ITU · ATSC · TTA · SBTVD Forum)

ITU-R 권고/보고서와 미국(ATSC), 한국(TTA), 브라질(SBTVD Forum)의 차세대 지상파 방송 표준을 기술 항목별로 비교하는 인터랙티브 대시보드입니다.

- **X축: 기술 항목** (물리계층, 전송, 코덱, 앱 프레임워크, 재난경보, …)
- **Y축: 표준화 기구** — ITU → ATSC → TTA → SBTVD Forum 순

| 기구 | 표준 | 비고 |
|------|------|------|
| 🌐 ITU | ITU-R BT 시리즈 권고/보고서 (BT.1306, BT.1877, BT.2295 등) | DTTB 시스템 규격의 국제 기준 문서 |
| 🇺🇸 ATSC | ATSC 3.0 (A/300 계열, "NextGen TV") | ROUTE/DASH 위주, 2020년 상용 시작 |
| 🇰🇷 TTA | 지상파 UHDTV 방송 송수신 정합 (TTAK.KO-07.0148~0153 Part 1~6 등) | 2017년 UHD 본방송 시작, MMT 기반 |
| 🇧🇷 SBTVD Forum | TV 3.0 (ATSC 3.0 물리계층 + 자체 상위계층) | 2025년 이후 단계적 도입 |

## 비교 축 (초안)
- 물리계층 (PHY): 채널 대역폭, 파일럿, LDM, 부트스트랩
- 전송계층: ROUTE/DASH vs MMT
- 비디오/오디오 코덱: HEVC / VVC, AC-4 / MPEG-H
- 방송-통신 융합(하이브리드), 앱 프레임워크(A/344, Ginga 등)
- 재난경보 (AEA / KEAS), 접근성, 저작권 보호
- 규제·정책 및 도입 일정

## 구조
```
data/       비교 데이터 (JSON)
src/        대시보드 소스
docs/       참고 문서·표준 출처 정리 (docs/refs: ITU English Style Guide 등)
tools/      표준 문서 수집 스크립트 (TTA 로그인/다운로드 자동화)
standards/  표준 원문 PDF — 저작권 문제로 git에 포함하지 않음 (.gitignore)
```

## 실행
```bash
# 정적 대시보드: 로컬 서버로 index.html 서빙
python -m http.server 8080
```

## 라이선스
TBD
