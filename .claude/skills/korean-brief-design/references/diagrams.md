# 도식 (인라인 SVG) 규약

기획안에서 그림이 값을 하는 경우는 대개 셋이다. **공간 배치**(회의장·부스),
**시간 구조**(하루 흐름, 단계 전환), **상태 전환**(A 배치 → B 배치). 그 외에는
표가 더 빨리 읽힌다. 장식용 그림은 넣지 않는다.

## 1. 테마 대응이 먼저다

SVG 안에서 색을 리터럴로 박으면 다크 모드에서 그림만 홀로 깨진다.
`fill="#333"` 대신 클래스를 주고 CSS에서 토큰으로 칠한다. `var()`는 SVG 속성에서도
동작하므로 인라인 속성에 쓸 수도 있다(`fill="var(--cobalt)"`).

```css
.dgm{width:100%;height:auto;display:block;border-radius:12px;background:var(--surface-2)}
.dgm .room  {fill:var(--surface-2);stroke:var(--line-strong);stroke-width:2}
.dgm .screen{fill:var(--ink)}
.dgm .onscreen{fill:var(--ground);font-size:11px}   /* 어두운 스크린 위 글자 */
.dgm .stand {fill:var(--surface);stroke:var(--cobalt);stroke-width:1.8}
.dgm .seat  {fill:var(--surface);stroke:var(--line-strong);stroke-width:1}
.dgm .divider{stroke:var(--line-strong);stroke-width:1.6;stroke-dasharray:6 5;fill:none}
.dgm .flowline{fill:none;stroke:var(--cobalt);stroke-width:1.4;stroke-dasharray:5 4;opacity:.75}
.dgm text     {font-family:"IBM Plex Sans KR",sans-serif;font-size:12px;fill:var(--ink-soft)}
.dgm .zone    {font-family:"Gothic A1",sans-serif;font-weight:800;font-size:14px;fill:var(--ink)}
.dgm .num     {font-family:"IBM Plex Mono",monospace;font-size:11px;fill:var(--ink-faint)}
```

색이 곧 범례가 되게 한다. 코발트 = 주 요소, 앰버 = 차별화 축·핵심 전환,
회색 = 부수·휴식. 그림 아래에 `.fig-legend`로 같은 색을 다시 설명한다.

## 2. 반복 요소는 `<defs>` + `<use>`

같은 부스를 여덟 번 손으로 그리면 좌표 하나가 어긋나도 눈에 안 띈다. 한 번 정의하고
옮겨 쓴다. `<use>`의 `x`/`y`는 이동(translate)으로 동작한다.

```svg
<defs>
  <g id="booth">
    <rect class="bfoot" x="0" y="0" width="115" height="52" rx="7"/>
    <rect class="btbl"  x="27" y="11" width="61" height="30" rx="4"/>
    <circle class="bseat" cx="12" cy="26" r="8"/>
    <circle class="bseat" cx="103" cy="26" r="8"/>
  </g>
</defs>
<use href="#booth" x="580" y="162"/>
<use href="#booth" x="715" y="162"/>
```

**id는 문서 전체에서 유일해야 한다.** 한 페이지에 SVG가 여러 개면 마커 id가
충돌하거나, 2번 SVG가 1번 SVG의 마커를 참조하는 사고가 난다. SVG마다 접두어를
붙인다(`ar-plan`, `ar-mode`).

화살표 마커:
```svg
<marker id="ar-plan" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto">
  <path d="M0 0 L8 4 L0 8 z" fill="var(--cobalt)"/>
</marker>
```

## 3. 대략이라도 축척을 맞춘다

개념도라도 비율이 현실과 맞으면 설득력이 다르다. 방 치수를 정하고 `단위/m`를
계산한 뒤 가구를 그 비율로 그린다.

예: 방 18m × 11m를 800 × 490 단위로 → 약 44단위/m.
칵테일 테이블(지름 0.6m) → 반지름 13단위. 회의 테이블(1.8m × 1.0m) → 80 × 44단위.

이렇게 하면 "몇 개가 들어가는가"라는 질문에 그림이 스스로 답한다.

## 4. 캡션이 배치를 정당화한다

평면도의 값은 예쁜 그림이 아니라 **판단의 근거**다. 그림 아래에 반드시
"왜 이 배치인가"를 적는다. 회의에서 나올 반박을 미리 받는 자리다.

```html
<p class="fig-cap"><b>배치 원칙 넷.</b>
  ① 분리선을 앞뒤로 세워 좌석 존에서도 스크린이 보이게 한다.
  ② 스탠딩을 전면에 밀집시켜 발표 때 화면 앞 밀도를 확보한다.
  ③ 소음을 부르는 다과·안내는 좌석 존 반대편에 몰아 상담 구역을 지킨다.
  ④ 중앙을 비워 이동 동선이 짧고 눈에 보이게 한다.</p>
```

개념도임을 밝히는 단서도 함께 단다 — "실제 축척·기둥·출입구 위치와 다르며
현장 확인 후 확정".

## 5. 상태 전환은 같은 가구, 다른 사람

"재배치 없이 두 프로그램을 소화한다"를 말로 하면 안 믿는다. **가구 위치가
동일한 그림 두 장**을 나란히 놓고 사람 분포만 바꾸면 한눈에 증명된다.

사람은 점을 수십 개 찍지 말고 **밀도 블롭**으로 그린다 — 마크업이 훨씬 짧고
읽기도 낫다.

```svg
<ellipse class="blob" cx="160" cy="105" rx="118" ry="62"/>
```
```css
.dgm .blob{fill:var(--cobalt);opacity:.20}
.dgm .blob-a{fill:var(--amber-bright);opacity:.28}
```

## 6. 접근성과 반응형

- 모든 SVG에 `role="img"`와 내용을 설명하는 `aria-label`을 단다. 그림을 못 보는
  사람에게 캡션만으로는 부족하다.
- `viewBox`를 쓰고 `width`/`height`는 CSS로(`width:100%;height:auto`). 고정 픽셀은
  모바일에서 넘친다.
- 가로로 긴 도식은 `overflow-x:auto` 컨테이너 안에 둔다. 페이지 본문이 옆으로
  스크롤되면 안 된다.

## 7. 흔한 사고

| 증상 | 원인 |
|---|---|
| 다크 모드에서 그림만 안 보임 | SVG 안에 색 리터럴을 박음 |
| 화살표가 안 나옴 | 마커 id 오타, 또는 다른 SVG의 id를 참조 |
| 텍스트가 도형에 가림 | `text`를 도형보다 먼저 그림 — SVG는 나중에 그린 것이 위 |
| 라벨끼리 겹침 | 라벨 자리를 먼저 잡고 도형을 배치해야 함 |
| 모바일에서 그림이 잘림 | `viewBox` 없이 고정 width |
