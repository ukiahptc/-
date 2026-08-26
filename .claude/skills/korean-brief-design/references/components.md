# 컴포넌트 마크업

`assets/tokens.css`의 클래스에 대응하는 HTML이다. 필요한 것만 골라 쓴다.

## 문서 머리 (필수)

`<title>`은 카테고리 라벨이 아니라 **이름**이다. "AAIA 2026 연말 행사 기획안 소개자료"
같은 설명형 대신 "에이전트, 일을 시작했다"처럼 그 문서만의 이름을 붙인다.

```html
<title>여섯 무대의 설계</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@400;500;700;800;900&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style> /* ← assets/tokens.css 내용 */ </style>
```

Google Fonts는 아티팩트 CSP가 허용하는 유일한 외부 폰트 호스트다. 다른 곳에서
불러오면 조용히 대체 글꼴로 떨어진다.

## 스티키 내브 (섹션이 5개 넘을 때만)

```html
<nav>
  <div class="wrap nav-in">
    <div class="brand"><span class="dot"></span>여섯 무대</div>
    <div class="nav-links">
      <a href="#s1">기조</a><a href="#s2">세션 1</a>
    </div>
  </div>
</nav>
```
```css
nav{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--ground) 85%,transparent);
    backdrop-filter:saturate(1.4) blur(12px);border-bottom:1px solid var(--line)}
.nav-in{display:flex;align-items:center;gap:16px;height:58px}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:14.5px;white-space:nowrap}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--cobalt);box-shadow:0 0 0 4px var(--cobalt-tint)}
.nav-links{margin-left:auto;display:flex;gap:6px;overflow-x:auto}
.nav-links a{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-faint);
  text-decoration:none;padding:5px 9px;border-radius:7px;white-space:nowrap}
.nav-links a:hover{color:var(--ink);background:var(--surface-2)}
.nav-links a:focus-visible{outline:2px solid var(--cobalt);outline-offset:2px}
```

## 히어로

원문의 주제 문장이 그대로 헤드라인이 된다. 핵심 어절 하나에만 앰버 밑줄.

```html
<header class="hero">
  <div class="wrap hero-in">
    <div class="kick">2026 대한민국 에이전틱 AI 현황</div>
    <h1>에이전트,<br>이제 <span class="em">일을 시작</span>했다</h1>
    <p class="hero-sub">성과공유회가 아니라 컨퍼런스입니다. …</p>
    <div class="hero-meta">
      <span class="chip"><span class="mono">12.09 WED</span> <b>2026. 12. 9.(수)</b></span>
      <span class="chip">참석 <b>200명+</b></span>
    </div>
  </div>
</header>
```
```css
h1 .em{color:var(--cobalt);position:relative;white-space:nowrap}
h1 .em::after{content:"";position:absolute;left:0;right:0;bottom:.06em;height:.13em;
  background:var(--amber-bright);opacity:.9;z-index:-1;border-radius:2px}
.hero-meta{display:flex;flex-wrap:wrap;gap:10px 12px;margin-top:38px}
```

## 섹션 머리

번호(`01`, `02`)는 **실제 순서가 의미를 가질 때만** 붙인다. 병렬 항목에 번호를
매기면 없는 순서를 지어내는 셈이다.

```html
<section id="why">
  <div class="wrap">
    <p class="eyebrow"><span class="no">01</span>기획 방향</p>
    <h2 class="sec">다른 AI 행사가 비워둔 두 자리</h2>
    <p class="lead">대형 AI 행사는 초청·후원 기반이라 …</p>
    …
  </div>
</section>
```

## 카드 격자

```html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
  <div class="card reveal">
    <div class="t">GAP 01</div>
    <h3>실패와 병목의 공개</h3>
    <p>도입 과정에서 실제로 막힌 지점을 …</p>
  </div>
  <div class="card flag reveal">…</div>
</div>
```
좁은 화면에서 1열로 떨어뜨리는 미디어쿼리를 잊지 않는다.

## 비교표 — 권장안 한 행만 강조

```html
<div class="tbl-wrap">
  <table class="cmp">
    <thead><tr><th>배치안</th><th>스테이션</th><th>처리량</th><th>한계</th></tr></thead>
    <tbody>
      <tr><td class="plan">A. 연회 원탁 1:1</td><td class="num">14</td><td class="num">42건</td><td>면적 절반 사장</td></tr>
      <tr class="pick"><td class="plan">D. 혼합</td><td class="num">30</td><td class="num">90건</td>
          <td>구역 분리 안내 필요 <span class="pickmark">권장</span></td></tr>
    </tbody>
  </table>
</div>
```
```css
.pickmark{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  font-weight:600;color:#fff;background:var(--cobalt);border-radius:4px;padding:1px 6px;margin-left:6px}
```

## 타임라인

```html
<div class="tl">
  <div class="slot"><div class="time">12:30</div><div class="node"></div>
    <div class="what">등록 및 사전 교류<span class="tag">30′</span></div></div>
  <div class="slot key"><div class="time">13:20</div><div class="node"></div>
    <div class="what">기조강연<span class="tag">40′</span></div></div>
  <div class="slot hinge">…</div>   <!-- 차별화 축 -->
  <div class="slot rest">…</div>    <!-- 휴식·전환 -->
</div>
```
시각은 반드시 mono + `tabular-nums`. 숫자가 세로로 안 맞으면 표가 아니라 목록으로 읽힌다.

## 수치 타일

```html
<div class="stats">
  <div class="stat reveal"><div class="n">300<small>건</small></div>
    <div class="k">등록 목표<br>노쇼 30~40% 감안</div></div>
  <div class="stat amber reveal">…</div>
</div>
```

## 진행표 (분 단위)

```html
<table class="ros">
  <tr><td class="t">00:00</td><td class="d">사회자 연사 소개 <em>2′</em></td></tr>
  <tr class="amber"><td class="t">15:00</td><td class="d"><b>2부 · 기업 증언</b> <em>15′</em></td></tr>
</table>
```
```css
.ros{width:100%;border-collapse:collapse;font-size:14px}
.ros td{padding:9px 0;border-bottom:1px solid var(--line);vertical-align:top}
.ros tr:last-child td{border-bottom:0}
.ros .t{font-family:"IBM Plex Mono",monospace;color:var(--cobalt-deep);white-space:nowrap;
  width:64px;font-size:12.5px;font-weight:500;padding-right:14px}
.ros .d em{color:var(--ink-faint);font-style:normal;font-size:12.5px;
  font-family:"IBM Plex Mono",monospace;margin-left:6px}
.ros .amber .t{color:var(--amber)}
```

## 푸터 + 초안 표기

가정값이 섞인 문서라면 여기서 반드시 밝힌다.

```html
<footer>
  <div class="wrap">
    <div class="foot-in">
      <span class="fb">AAIA 2026 연말 행사 기획(안)</span>
      <span>운영사무국(KMAC) · 2026. 8. 25.</span>
      <span class="prov">DRAFT · 구조·컨텐츠 논의안</span>
    </div>
    <p class="foot-note">수치와 편성은 확정 전 가정값(안)이며 …</p>
  </div>
</footer>
```

## 스크롤 등장 (선택)

`.reveal`을 붙인 요소에만 적용된다. 모션 최소화 설정과 옵저버 미지원을 모두 처리한다.

```html
<script>
(function(){
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var els = document.querySelectorAll(".reveal");
  if(reduce || !("IntersectionObserver" in window)){
    els.forEach(function(e){e.classList.add("in")}); return;
  }
  var io = new IntersectionObserver(function(en){
    en.forEach(function(x){ if(x.isIntersecting){ x.target.classList.add("in"); io.unobserve(x.target); } });
  },{threshold:.12,rootMargin:"0px 0px -6% 0px"});
  els.forEach(function(e){io.observe(e)});
})();
</script>
```

모든 카드에 다 붙이지는 않는다. 화면에 한꺼번에 들어오는 격자 전체가 하나씩
떠오르면 산만하다. 섹션당 한 무리 정도면 충분하다.
