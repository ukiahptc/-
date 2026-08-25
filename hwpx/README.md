# HWPX 스타일 생성기

스타일 수치(JSON)를 받아 스타일이 적용된 HWPX 문서를 생성하는 도구입니다.
외부 라이브러리 없이 Python 3 표준 라이브러리만 사용합니다.

## 사용법

```bash
# 스타일별 내용 지정 (권장)
python3 hwpx_generator.py --styles styles.example.json --content content.example.json -o out.hwpx

# 일반 텍스트 전체에 첫 번째 스타일 적용
python3 hwpx_generator.py --styles styles.example.json --text 내용.txt -o out.hwpx
```

## 스타일 설정 항목 (styles.json)

### page — 용지 설정

| 항목 | 단위 | 설명 |
|---|---|---|
| `width_mm`, `height_mm` | mm | 용지 크기 (기본 A4: 210×297) |
| `landscape` | true/false | 가로 방향 여부 |
| `margins_mm.top/bottom/left/right` | mm | 용지 여백 |
| `margins_mm.header/footer` | mm | 머리말/꼬리말 영역 |
| `margins_mm.gutter` | mm | 제본 여백 |

### fonts — 문서 기본 글꼴

| 항목 | 설명 |
|---|---|
| `hangul` | 한글 글꼴 이름 (예: 함초롬바탕, 맑은 고딕, 바탕) |
| `latin` | 영문 글꼴 이름 |

### styles — 문단 스타일 목록 (여러 개 정의 가능)

| 항목 | 단위 | 설명 |
|---|---|---|
| `name` | | 스타일 이름 (content에서 이 이름으로 참조) |
| `font_hangul`, `font_latin` | | 이 스타일 전용 글꼴 (생략하면 문서 기본 글꼴) |
| `font_size_pt` | pt | 글자 크기 |
| `bold`, `italic`, `underline` | true/false | 굵게 / 기울임 / 밑줄 |
| `color` | #RRGGBB | 글자 색 |
| `letter_spacing_percent` | % | 자간 (-50 ~ 50) |
| `align` | | 정렬: `left` `center` `right` `justify` `distribute` (한글 표기 `왼쪽` `가운데` 등도 가능) |
| `line_spacing_percent` | % | 줄간격 (한글 기본 160) |
| `space_before_pt`, `space_after_pt` | pt | 문단 위/아래 간격 |
| `indent_first_line_pt` | pt | 첫 줄 들여쓰기(양수) / 내어쓰기(음수) |
| `left_margin_pt`, `right_margin_pt` | pt | 문단 좌/우 여백 |

## 내용 파일 형식 (content.json)

```json
[
  { "style": "제목", "text": "문서 제목" },
  { "style": "본문", "text": "첫 문단.\n둘째 문단(줄바꿈은 문단 분리)." }
]
```

`style`은 styles.json의 `name`(또는 0부터 시작하는 인덱스)입니다.

## 단위 참고

HWPX 내부 단위는 HWPUNIT(1/7200 인치)입니다. 1pt = 100 HWPUNIT,
1mm ≈ 283.465 HWPUNIT이며 변환은 스크립트가 자동으로 처리하므로
설정 파일에는 pt와 mm만 쓰면 됩니다.
