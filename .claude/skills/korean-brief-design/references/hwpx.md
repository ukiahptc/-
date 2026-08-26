# 한글 문서(HWPX) 경로

공문서·정식 보고서는 결국 한글 파일로 나간다. `scripts/hwpx_generator.py`는 스타일
설정 JSON과 내용 JSON을 받아 HWPX를 만든다. 외부 의존성 없이 파이썬 표준
라이브러리만 쓴다.

## 실행

```bash
python3 scripts/hwpx_generator.py \
  --styles assets/styles.report.json \
  --content 내용.json \
  -o 산출물.hwpx \
  --title "AAIA 2026 연말 행사 기획(안)" \
  --date-author "[’26.8.25.(화), 운영사무국(KMAC)]"
```

`--title`과 `--date-author`는 설정 파일의 `template` 값을 덮어쓴다. 문서마다 바뀌는
값이라 명령줄로 주는 편이 편하다. 내용 없이 제목만으로도 만들 수 있다.

## 스타일 수치 (assets/styles.report.json)

실제 문서에서 측정해 확정한 값이다. **사용자가 새 수치를 주지 않는 한 그대로 쓴다.**
눈대중으로 바꾸면 기존 문서와 서식이 어긋난다.

| 스타일 | 글꼴 | 크기 | 자간 | 좌/우 여백 | 줄간격 | 문단 간격 | 글머리표 |
|---|---|---|---|---|---|---|---|
| 문서 제목 | HY헤드라인M | 18pt | 0 | 0 / 0 | 190% | — | — |
| 날짜/작성자 | 휴먼명조 (영문 HCI Poppy) | 12pt | 0 | 0 / 0 | 110% | 아래 12pt | — |
| □ | HY헤드라인M | 15pt | -5% | 2 / 7pt | 160% | 위 14 · 아래 10pt | □ |
| ○ | 휴먼명조 | 15pt | -3% | 19 / 7pt | 160% | 아래 10pt | ○ |
| - | 휴먼명조 | 12pt | -3% | 34 / 7pt | 160% | 아래 10pt | - |
| · | 휴먼명조 | 12pt | -3% | 49 / 7pt | 160% | 아래 10pt | · |
| (표) 제목행 | 맑은 고딕 | 11pt | 0 | 0 / 0 | 130% | — | — |
| (표) 내용 기본서술 | 맑은 고딕 | 10pt | -5% | 0 / 0 | 130% | — | — |
| (표) 내용 가운데 | 맑은 고딕 | 10pt | -5% | 0 / 0 | 130% | — | — |

편집 용지는 A4에 좌우 20mm, 상하 10mm, 머리말·꼬리말 15mm.

여백이 스타일 전환을 만든다. □ 앞 14pt와 각 항목 아래 10pt가 없으면 개조식이
빽빽하게 붙어 읽히지 않는다. 이 간격은 나중에 사용자가 지적해서 넣은 값이다.

## 기본 템플릿

`template` 블록이 있으면 문서 맨 앞에 두 요소가 자동으로 들어간다.

- **제목 표** — 3행. 위아래에 파란 그라데이션 액센트 띠(#3057B9 → #DFE6F7, 아래
  띠는 역방향), 가운데 행에 제목. 표 폭은 본문 폭 전체.
- **작성날짜/작성자** — 제목 표 바로 아래 오른쪽 정렬. `[’26.8.25.(화), 운영사무국(KMAC)]`
  형식. 아래 12pt 간격.

## 표 서식

행정문서형 개방형 표다. 좌우 바깥 테두리가 없고, 위아래만 0.3mm 굵은 선,
내부선은 0.12mm. 셀은 세로 가운데 정렬.

```json
{ "table": {
    "columns": ["구분", "내용"],
    "col_widths_percent": [20, 80],
    "body_style": ["(표) 내용 가운데", "(표) 내용 기본서술"],
    "rows": [["일시", "2026. 12. 9.(수) 12:30~19:40"]]
} }
```

`body_style`에 열 개수만큼 배열을 주면 열마다 다른 스타일이 적용된다. 왼쪽 구분
열은 가운데, 서술이 긴 오른쪽 열은 기본서술(양쪽 정렬)이 잘 읽힌다. `columns`를
빼면 제목행 없는 표가 된다.

## 내용 JSON

```json
[
  { "style": "□", "text": "추진 배경" },
  { "style": "○", "text": "첫 문단.\n줄바꿈은 문단 분리" },
  { "table": { "columns": ["시간","내용"], "rows": [["12:30~13:00","등록"]] } },
  { "style": "□", "text": "붙임 1. 모객 계획", "page_break": true }
]
```

`page_break: true`면 그 문단부터 새 쪽에서 시작한다. 본문과 붙임을 나눌 때 쓴다.

## 만들 때 지킬 것

- **개조식 뎁스는 2단까지.** 화면과 마찬가지로 종이에서도 □ 아래 ○ 아래 - 아래 ·
  까지 내려가면 안 읽힌다. 하위 항목이 한 논지면 합치고, 나열이면 표로 올린다.
- **나열형은 표로.** 일시·장소·규모, 시기별 마일스톤, 대안 비교, 리스크와 대응은
  전부 표가 낫다. 목록으로 늘어놓으면 쪽만 잡아먹는다.
- **회의용이면 본문과 붙임을 나눈다.** 본문은 구조와 컨텐츠만, 운영 세부(모객·
  일정·예산·리스크)는 `page_break`로 쪽을 나눠 붙임으로 내린다.
- 확정 전 수치에는 **(안)** 을 붙이고, 문서 끝에 "끝."을 오른쪽 정렬로 둔다.

## 참조 문서에서 서식을 새로 뽑아야 할 때

사용자가 다른 한글 파일을 주며 "이 서식으로"라고 하면 HWPX를 풀어서 직접 읽는다.
HWPX는 zip이고 안의 XML이 서식을 다 담고 있다.

```bash
python3 -c "import zipfile; zipfile.ZipFile('참조.hwpx').extractall('x')"
```

- `Contents/header.xml` — 글꼴(`hh:fontface`), 글자 모양(`hh:charPr`: height는
  1/100pt, `hh:spacing`이 자간 %), 문단 모양(`hh:paraPr`: 여백은 HWPUNIT,
  `hc:prev`/`hc:next`가 문단 위아래 간격), 테두리·배경(`hh:borderFill`)
- `Contents/section0.xml` — 본문과 표 구조
- `Preview/PrvImage.png` — 미리보기 이미지. 눈으로 확인할 때 이걸 먼저 본다.

단위는 HWPUNIT = 1/7200인치. 1pt = 100 HWPUNIT, 1mm ≈ 283.465 HWPUNIT.
생성기가 pt·mm를 받아 알아서 변환하므로 설정 파일에는 pt와 mm만 쓴다.

## 검증

만든 뒤에는 열어보기 전에 기계적으로 확인한다. XML이 깨지거나 참조가 어긋나면
한글이 파일을 못 연다.

```python
import zipfile, re, xml.dom.minidom
z = zipfile.ZipFile('산출물.hwpx')
for n in z.namelist():
    if n.endswith(('.xml', '.hpf')):
        xml.dom.minidom.parseString(z.read(n))   # XML 정합성
h = z.read('Contents/header.xml').decode('utf-8')
s = z.read('Contents/section0.xml').decode('utf-8')
defined = set(re.findall(r'<hh:borderFill id="(\d+)"', h))
used = set(re.findall(r'borderFillIDRef="(\d+)"', s + h))
assert not (used - defined), '정의되지 않은 borderFill'
```

시간표가 들어간 문서라면 구간이 연속하는지도 검산한다. 사람이 눈으로 훑으면
14행 중 한 칸 어긋난 걸 놓친다.
