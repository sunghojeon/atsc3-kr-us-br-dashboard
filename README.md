# ATSC 3.0 Standards Comparison

최신 확정 ATSC 문서를 기준으로 한국 TTA와 브라질 TV 3.0의 대응 조항·국가 프로파일·차이를 비교하는 정적 HTML 자료다. ITU-R 문서는 국제적 맥락으로 연결한다. 검증 기준일은 **2026-10-22**이다(2026-10-18판의 갱신판; 바뀐 점은 `docs/REVIEW_2026-10-22_ko.md`).

**35개 ATSC 문서(표준23, Recommended Practice12), 비교44행, 세부 기능44개, 18문서의 장절 대응80행**을 포함한다. 공식 current 목록의 판본·PDF·SHA-256을 확인하고 화면 주장의 관련 조항을 대조했다. 전체 표준의 모든 문장에 대한 동등성 인증은 아니다.

## 열기와 재생성

`index.html`을 직접 열거나 다음 명령으로 로컬 서버를 시작한다. 직접 열 때도 `app.js`와 `data/standards.js`를 같은 폴더 구조로 유지한다.

```sh
python -m http.server 8080
python tools/build_data.py
python tools/build_data.py --check
python tools/test_dashboard.py
python tools/export_standalone.py
```

마지막 명령은 **`dist/atsc3-kr-us-br-reviewed.html`** 단일 파일을 만든다. 데이터·스크립트·스타일을 포함하고 외부 글꼴을 요청하지 않아 인터넷 없이 볼 수 있다. 공식 출처 링크를 여는 데에는 인터넷이 필요하다.

빌드는 Python 표준 라이브러리만 사용하며 원문 PDF·로그인·`standards/*/index.csv`에 의존하지 않는다. 브라우저 검증은 선택 사항이다.

```sh
python -m pip install playwright
python -m playwright install chromium
python tools/test_dashboard.py --browser --artifacts dist/qa
```

사용자 프로필을 쓰지 않는 격리 Chromium에서44행·44개 기능의 표시, 판정 이유·권고, 검색·필터·키보드, 1440/1024/390px 및 어두운 화면, 단일 파일을 검사한다.

## 정본과 생성 파일

| 경로 | 역할 |
|---|---|
| `data/mappings.json` | 행·국가별 대응·판정·법령·출처의 정본 |
| `data/baseline.json` | 확인한 ATSC 현행35문서와 별도 후보표준 목록 |
| `data/comparisons/*.json` | 물리계층·STL·시그널링·코덱·앱 세부 비교 |
| `data/chapters/*.json` | 명시한 국가판의 장절 대응과 차이 |
| `data/standards.json`, `data/standards.js` | 위 정본에서 함께 생성하는 화면 데이터 |
| `index.html`, `app.js` | 화면·검색·필터·세부 근거 표시 |
| `notes.js` | 검토 메모(선택한 글자에 메모, 이 브라우저에만 저장) |
| `docs/sources.md` | 공식 출처와 자료의 지위 |
| `docs/REVIEW_2026-10-18_ko.md` | 수정·검증·남는 한계 |
| `docs/REVIEW_2026-10-22_ko.md` | 2026-10-22 갱신: SBTVD 현행판·ABNT 원제·검색 보조어·브라질 법령 일자 |
| `docs/refs/` | 법령 요약과 참조 |
| `standards/` | 로컬 원문; 저작권 때문에 Git 및 전달 ZIP에서 제외 |

정본 JSON을 수정한 뒤 생성기를 실행한다. 생성 파일만 고치면 `--check`가 실패한다. 기존 수집 도구 `tools/tta_*.py`는 화면 실행이나 재빌드에 필요하지 않다.

## 검토 메모

1. 화면 오른쪽 아래 `✎ Memo off` 단추를 눌러 메모 모드를 켠다.
2. 고칠 부분의 글자를 선택하고 `✎ Add note`를 눌러 메모를 적는다.
   - 선택한 글자에 주황색 표시가 남는다.
   - 표시를 누르면 수정·완료(Done)·삭제를 할 수 있다.
3. `Notes` 목록에서 문서별로 모아 보고, `Show`로 그 위치를 연다.
4. 끝나면 `Export .md`(읽는 용도)나 `Export .json`(다시 가져오기용)으로 내보낸다. `Import .json`은 다른 기기에서 만든 메모를 합친다.

메모의 저장과 표시는 다음과 같다.

- 메모는 **그 브라우저에만** 저장된다(localStorage). 서버로 보내지 않으므로 다른 방문자에게 보이지 않는다.
- 공개 주소와 내려받은 단일 HTML은 저장소가 서로 다르다. 기기나 브라우저를 바꾸면 json으로 옮긴다.
- 표의 필터·탭·행 펼침이 바뀌거나 페이지를 다시 열어도, 메모는 인용한 글자와 앞뒤 문맥으로 다시 찾아 표시된다.
- 나중에 내용이 바뀌어 인용 글자를 찾지 못하면 표시 없이 목록에만 남는다.

## 판정의 의미

- **Same in stated scope**: 명시한 세부 범위에서 기술 차이를 찾지 못했다. 문서 전체·모든 선택 기능·수신기 호환을 뜻하지 않는다.
- **Partial match / Different**: 인용 조항에 실제 차이가 있거나 기술 방식이 다르다. 국가 문서의 인용판과 실제 기술 차이를 구분한다.
- **No equivalent identified**: 명시한 검토 집합에서 직접 대응을 찾지 못했거나 별도 국가 문서로 식별했다. 미검토를 부재로 분류하지 않는다.
- **Review needed**: 대응·의무·동등성을 확정할 근거가 충분하지 않다. 관계·신뢰도·미확인 범위를 함께 읽는다.

최신 ATSC 기술 기준과 법령의 고정 편입판은 다르다. 과거 ATSC 인용판, 브라질 법령·ABNT 규범·비규범 OG, 확정판·후보판을 구분한다. ABNT 전문을 읽지 못한 셀에는 이를 표시한다. 등록된 code point도 실제 수신기의 구현·상호운용 증거는 아니다.

기존 공개 주소는 <https://sunghojeon.github.io/atsc3-kr-us-br-dashboard/>다. **이번 검증은 로컬 수정본에 대한 것이며 공개 사이트 갱신을 의미하지 않는다.**
