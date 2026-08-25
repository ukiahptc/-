#!/usr/bin/env python3
"""스타일 설정(JSON)을 받아 HWPX 문서를 생성하는 도구.

HWPX는 OWPML(KS X 6101) 기반의 zip 컨테이너 형식이다. 이 스크립트는
외부 의존성 없이 표준 라이브러리만으로 다음 구조를 만든다.

    mimetype                  (무압축, 첫 엔트리)
    version.xml
    settings.xml
    META-INF/container.xml
    META-INF/manifest.xml
    META-INF/container.rdf
    Contents/content.hpf
    Contents/header.xml       <- 글꼴/글자모양/문단모양/스타일 정의
    Contents/section0.xml     <- 본문 (문단 + 표)
    Preview/PrvText.txt

지원 기능:
    - 문단 스타일(글꼴, 크기, 굵기, 색, 장평, 자간, 정렬, 줄간격, 여백, 글머리표)
    - 문서 상단 제목 표(그라데이션 액센트 띠) + 작성날짜/작성자 줄 템플릿
    - 행정문서형 개방형 표(좌우 테두리 없음, 상하 굵은 선, 제목행)

사용법:
    python3 hwpx_generator.py --styles styles.json --content content.json -o out.hwpx
    python3 hwpx_generator.py --styles styles.json --text plain.txt -o out.hwpx \
        --title "문서 제목" --date-author "[’26.8.25.(월), 작성자]"

단위 변환:
    HWPUNIT = 1/7200 inch
    1 pt = 100 HWPUNIT,  1 mm = 7200/25.4 ≈ 283.465 HWPUNIT
    글자 크기(height)는 1/100 pt 단위 (10pt -> 1000)
"""

import argparse
import json
import zipfile
from xml.sax.saxutils import escape, quoteattr

# ---------------------------------------------------------------- 단위 변환

def pt2unit(pt):
    return int(round(float(pt) * 100))


def mm2unit(mm):
    return int(round(float(mm) * 7200.0 / 25.4))


ALIGN_MAP = {
    "left": "LEFT", "right": "RIGHT", "center": "CENTER",
    "justify": "JUSTIFY", "distribute": "DISTRIBUTE",
    # 한국어 표기도 허용
    "왼쪽": "LEFT", "오른쪽": "RIGHT", "가운데": "CENTER", "양쪽": "JUSTIFY", "배분": "DISTRIBUTE",
}

LANGS = ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user")


# ---------------------------------------------------------------- 스타일 모델

DEFAULT_STYLE = {
    "name": "본문",
    "eng_name": "Normal",
    "font_hangul": None,          # None이면 문서 기본 글꼴 사용
    "font_latin": None,
    "font_size_pt": 10.0,
    "bold": False,
    "italic": False,
    "underline": False,
    "color": "#000000",
    "width_ratio_percent": 100,    # 장평 (%)
    "letter_spacing_percent": 0,   # 자간 (-50 ~ 50)
    "bullet_char": None,           # 글머리표 문자 (예: "□"), None이면 없음
    "align": "justify",
    "line_spacing_percent": 160,   # 줄간격 (%)
    "space_before_pt": 0.0,        # 문단 위 간격
    "space_after_pt": 0.0,         # 문단 아래 간격
    "indent_first_line_pt": 0.0,   # 들여쓰기(+) / 내어쓰기(-)
    "left_margin_pt": 0.0,         # 문단 왼쪽 여백
    "right_margin_pt": 0.0,        # 문단 오른쪽 여백
}

DEFAULT_PAGE = {
    "width_mm": 210.0,
    "height_mm": 297.0,
    "landscape": False,
    "margins_mm": {
        "top": 20.0, "bottom": 15.0, "left": 30.0, "right": 30.0,
        "header": 15.0, "footer": 15.0, "gutter": 0.0,
    },
}

DEFAULT_FONTS = {"hangul": "함초롬바탕", "latin": "함초롬바탕"}

# 제목 표/표 서식 기본값 (참조 문서에서 추출한 수치, HWPUNIT)
DEFAULT_TEMPLATE = {
    "title": None,                  # 제목 텍스트 (None이면 제목 표 생략)
    "title_style": "문서 제목",
    "date_author": None,            # 작성날짜/작성자 줄 (None이면 생략)
    "date_author_style": "날짜/작성자",
    "accent_start": "#3057B9",      # 액센트 띠 그라데이션 시작색
    "accent_end": "#DFE6F7",        # 액센트 띠 그라데이션 끝색
    "accent_height_unit": 380,      # 액센트 띠 행 높이
    "title_row_height_unit": 2563,  # 제목 행 높이
}

DEFAULT_TABLE = {
    "header_style": "(표) 제목행",
    "body_style": "(표) 내용 가운데",
    "outer_border_mm": 0.3,         # 표 위/아래 바깥선 두께
    "inner_border_mm": 0.12,        # 내부선 두께
    "row_height_unit": 1949,        # 행 최소 높이
    "cell_margin_lr_unit": 510,     # 셀 안 좌우 여백
    "cell_margin_tb_unit": 141,     # 셀 안 상하 여백
}


def normalize_config(cfg):
    """사용자 설정에 기본값을 채워 완전한 설정으로 만든다."""
    page = dict(DEFAULT_PAGE)
    page.update(cfg.get("page", {}))
    margins = dict(DEFAULT_PAGE["margins_mm"])
    margins.update(cfg.get("page", {}).get("margins_mm", {}))
    page["margins_mm"] = margins

    fonts = dict(DEFAULT_FONTS)
    fonts.update(cfg.get("fonts", {}))

    styles = []
    for raw in cfg.get("styles", [dict(DEFAULT_STYLE)]):
        st = dict(DEFAULT_STYLE)
        st.update(raw)
        if st["font_hangul"] is None:
            st["font_hangul"] = fonts["hangul"]
        if st["font_latin"] is None:
            st["font_latin"] = fonts["latin"]
        styles.append(st)
    if not styles:
        raise ValueError("styles가 비어 있습니다")

    # 표를 담는 문단, 액센트 띠의 빈 셀 등에 쓸 글머리표 없는 기본 스타일 보장
    if not any(st["name"] == "바탕글" for st in styles):
        base = dict(DEFAULT_STYLE)
        base["name"] = "바탕글"
        base["font_hangul"] = fonts["hangul"]
        base["font_latin"] = fonts["latin"]
        styles.append(base)

    template = dict(DEFAULT_TEMPLATE)
    template.update(cfg.get("template", {}))
    table = dict(DEFAULT_TABLE)
    table.update(cfg.get("table", {}))

    return {"page": page, "fonts": fonts, "styles": styles,
            "template": template, "table": table,
            "title": cfg.get("title", "")}


# ---------------------------------------------------------------- 테두리/배경 레지스트리

NONE_EDGE = ("NONE", "0.1 mm")


class FillRegistry:
    """borderFill 정의를 모아 id를 배정한다. id는 1부터."""

    def __init__(self):
        self._keys = {}
        self._xmls = []
        # id 1: 테두리 없음(일반), id 2: charPr/paraPr 참조용
        self.plain(); self.plain2 = self.get("plain2", edges={})

    def _register(self, key, body_factory):
        if key not in self._keys:
            fid = len(self._xmls) + 1
            self._keys[key] = fid
            self._xmls.append(body_factory(fid))
        return self._keys[key]

    def get(self, key, edges=None, gradient=None):
        """edges: {"left"/"right"/"top"/"bottom": (type, width)}; 빠진 변은 NONE.
        gradient: (색1, 색2) 90도 선형 그라데이션 배경."""
        edges = edges or {}

        def factory(fid):
            e = {side: edges.get(side, NONE_EDGE)
                 for side in ("left", "right", "top", "bottom")}
            parts = [
                '<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" '
                'breakCellSeparateLine="0">' % fid,
                '<hh:slash type="NONE" Crooked="0" isCounter="0"/>',
                '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>',
            ]
            for side in ("left", "right", "top", "bottom"):
                t, w = e[side]
                parts.append('<hh:%sBorder type="%s" width="%s" color="#000000"/>' % (side, t, w))
            parts.append('<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>')
            if gradient:
                parts.append(
                    '<hc:fillBrush><hc:gradation type="LINEAR" angle="90" centerX="0" '
                    'centerY="0" step="255" colorNum="2" stepCenter="50" alpha="0">'
                    '<hc:color value="%s"/><hc:color value="%s"/>'
                    '</hc:gradation></hc:fillBrush>' % gradient
                )
            parts.append('</hh:borderFill>')
            return "".join(parts)

        return self._register(key, factory)

    def plain(self):
        return self.get("plain", edges={})

    def solid_box(self, width_mm):
        edge = ("SOLID", "%g mm" % width_mm)
        return self.get("box-%g" % width_mm,
                        edges={s: edge for s in ("left", "right", "top", "bottom")})

    def cell(self, first_col, last_col, top_mm, bottom_mm, inner_mm):
        """개방형 표 셀: 좌우 바깥 테두리 없음."""
        inner = ("SOLID", "%g mm" % inner_mm)
        edges = {
            "top": ("SOLID", "%g mm" % top_mm),
            "bottom": ("SOLID", "%g mm" % bottom_mm),
            "left": NONE_EDGE if first_col else inner,
            "right": NONE_EDGE if last_col else inner,
        }
        key = "cell-%d%d-%g-%g-%g" % (first_col, last_col, top_mm, bottom_mm, inner_mm)
        return self.get(key, edges=edges)

    def xml(self):
        return ('<hh:borderFills itemCnt="%d">%s</hh:borderFills>'
                % (len(self._xmls), "".join(self._xmls)))


# ---------------------------------------------------------------- header.xml

def build_fontfaces(styles, fonts):
    """언어 슬롯별 글꼴 목록과 스타일별 글꼴 인덱스를 만든다."""
    per_lang = {lang: [] for lang in LANGS}

    def font_id(lang, face):
        lst = per_lang[lang]
        if face not in lst:
            lst.append(face)
        return lst.index(face)

    refs = []
    for st in styles:
        ref = {}
        for lang in LANGS:
            face = st["font_latin"] if lang == "latin" else st["font_hangul"]
            ref[lang] = font_id(lang, face)
        refs.append(ref)

    parts = ['<hh:fontfaces itemCnt="7">']
    for lang in LANGS:
        faces = per_lang[lang] or [fonts["hangul"]]
        parts.append('<hh:fontface lang="%s" fontCnt="%d">' % (lang.upper(), len(faces)))
        for i, face in enumerate(faces):
            parts.append('<hh:font id="%d" face=%s type="TTF" isEmbedded="0"/>' % (i, quoteattr(face)))
        parts.append('</hh:fontface>')
    parts.append('</hh:fontfaces>')
    return "".join(parts), refs


def build_char_pr(idx, st, ref, ref_fill_id):
    spacing = int(st["letter_spacing_percent"])
    ratio = int(st["width_ratio_percent"])
    parts = [
        '<hh:charPr id="%d" height="%d" textColor="%s" shadeColor="none" '
        'useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="%d">'
        % (idx, pt2unit(st["font_size_pt"]), st["color"], ref_fill_id)
    ]
    parts.append(
        '<hh:fontRef hangul="%(hangul)d" latin="%(latin)d" hanja="%(hanja)d" '
        'japanese="%(japanese)d" other="%(other)d" symbol="%(symbol)d" user="%(user)d"/>' % ref
    )
    for tag, val in (("ratio", ratio), ("spacing", spacing), ("relSz", 100), ("offset", 0)):
        parts.append(
            '<hh:%s hangul="%d" latin="%d" hanja="%d" japanese="%d" other="%d" symbol="%d" user="%d"/>'
            % (tag, val, val, val, val, val, val, val)
        )
    underline = "BOTTOM" if st["underline"] else "NONE"
    parts.append('<hh:underline type="%s" shape="SOLID" color="%s"/>' % (underline, st["color"]))
    parts.append('<hh:strikeout shape="NONE" color="#000000"/>')
    parts.append('<hh:outline type="NONE"/>')
    parts.append('<hh:shadow type="NONE" color="#B2B2B2" offsetX="10" offsetY="10"/>')
    if st["bold"]:
        parts.append('<hh:bold/>')
    if st["italic"]:
        parts.append('<hh:italic/>')
    parts.append('</hh:charPr>')
    return "".join(parts)


def build_para_pr(idx, st, ref_fill_id, bullet_id=0):
    align = ALIGN_MAP.get(str(st["align"]).lower(), str(st["align"]).upper())
    if bullet_id:
        heading = '<hh:heading type="BULLET" idRef="%d" level="0"/>' % bullet_id
    else:
        heading = '<hh:heading type="NONE" idRef="0" level="0"/>'
    parts = [
        '<hh:paraPr id="%d" tabPrIDRef="0" condense="0" fontLineHeight="0" '
        'snapToGrid="1" suppressLineNumbers="0" checked="0">' % idx,
        '<hh:align horizontal="%s" vertical="BASELINE"/>' % align,
        heading,
        '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD" '
        'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>',
        '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>',
        '<hh:margin>',
        '<hc:intent value="%d" unit="HWPUNIT"/>' % pt2unit(st["indent_first_line_pt"]),
        '<hc:left value="%d" unit="HWPUNIT"/>' % pt2unit(st["left_margin_pt"]),
        '<hc:right value="%d" unit="HWPUNIT"/>' % pt2unit(st["right_margin_pt"]),
        '<hc:prev value="%d" unit="HWPUNIT"/>' % pt2unit(st["space_before_pt"]),
        '<hc:next value="%d" unit="HWPUNIT"/>' % pt2unit(st["space_after_pt"]),
        '</hh:margin>',
        '<hh:lineSpacing type="PERCENT" value="%d" unit="HWPUNIT"/>' % int(st["line_spacing_percent"]),
        '<hh:border borderFillIDRef="%d" offsetLeft="0" offsetRight="0" offsetTop="0" '
        'offsetBottom="0" connect="0" ignoreMargin="0"/>' % ref_fill_id,
        '</hh:paraPr>',
    ]
    return "".join(parts)


def build_numbering():
    heads = []
    for level in range(1, 8):
        heads.append(
            '<hh:paraHead start="1" level="%d" align="LEFT" useInstWidth="1" autoIndent="1" '
            'widthAdjust="0" textOffsetType="PERCENT" textOffset="50" numFormat="DIGIT" '
            'charPrIDRef="4294967295" checkable="0">^%d.</hh:paraHead>' % (level, level)
        )
    return '<hh:numberings itemCnt="1"><hh:numbering id="1" start="0">%s</hh:numbering></hh:numberings>' % "".join(heads)


def build_bullets(styles):
    """스타일에서 쓰인 글머리표 문자를 모아 hh:bullets XML과
    스타일별 bullet id 목록(글머리표 없으면 0)을 돌려준다."""
    chars = []
    ids = []
    for st in styles:
        ch = st.get("bullet_char")
        if not ch:
            ids.append(0)
            continue
        if ch not in chars:
            chars.append(ch)
        ids.append(chars.index(ch) + 1)
    if not chars:
        return "", ids
    parts = ['<hh:bullets itemCnt="%d">' % len(chars)]
    for i, ch in enumerate(chars):
        parts.append(
            '<hh:bullet id="%d" char=%s checkedChar="" useImage="0">'
            '<hh:img binaryItemIDRef="" bright="0" contrast="0" effect="REAL_PIC"/>'
            '<hh:paraHead start="1" level="1" align="LEFT" useInstWidth="0" autoIndent="0" '
            'widthAdjust="0" textOffsetType="PERCENT" textOffset="50" numFormat="DIGIT" '
            'charPrIDRef="4294967295" checkable="0">^1.</hh:paraHead>'
            '</hh:bullet>' % (i + 1, quoteattr(ch))
        )
    parts.append('</hh:bullets>')
    return "".join(parts)


def build_header_xml(cfg, fills):
    styles = cfg["styles"]
    fontfaces_xml, refs = build_fontfaces(styles, cfg["fonts"])

    bullets_xml = build_bullets(styles)
    bullet_ids = []
    chars = []
    for st in styles:
        ch = st.get("bullet_char")
        if not ch:
            bullet_ids.append(0)
        else:
            if ch not in chars:
                chars.append(ch)
            bullet_ids.append(chars.index(ch) + 1)

    ref_fill = fills.plain2
    char_prs = "".join(build_char_pr(i, st, refs[i], ref_fill) for i, st in enumerate(styles))
    para_prs = "".join(build_para_pr(i, st, ref_fill, bullet_ids[i]) for i, st in enumerate(styles))

    style_entries = []
    for i, st in enumerate(styles):
        style_entries.append(
            '<hh:style id="%d" type="PARA" name=%s engName=%s paraPrIDRef="%d" '
            'charPrIDRef="%d" nextStyleIDRef="%d" langID="1042" lockForm="0"/>'
            % (i, quoteattr(st["name"]), quoteattr(st["eng_name"] or st["name"]), i, i, i)
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" version="1.4" secCnt="1">'
        '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        '<hh:refList>'
        + fontfaces_xml
        + fills.xml()
        + '<hh:charProperties itemCnt="%d">%s</hh:charProperties>' % (len(styles), char_prs)
        + '<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>'
        + build_numbering()
        + bullets_xml
        + '<hh:paraProperties itemCnt="%d">%s</hh:paraProperties>' % (len(styles), para_prs)
        + '<hh:styles itemCnt="%d">%s</hh:styles>' % (len(styles), "".join(style_entries))
        + '</hh:refList>'
        '<hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument>'
        '<hh:docOption><hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/></hh:docOption>'
        '</hh:head>'
    )


# ---------------------------------------------------------------- section0.xml

def text_width_unit(page):
    m = page["margins_mm"]
    return mm2unit(page["width_mm"]) - mm2unit(m["left"]) - mm2unit(m["right"]) - mm2unit(m["gutter"])


def build_sec_pr(page):
    m = page["margins_mm"]
    landscape = "NARROWLY" if page.get("landscape") else "WIDELY"
    w = mm2unit(page["width_mm"])
    h = mm2unit(page["height_mm"])
    if page.get("landscape"):
        w, h = max(w, h), min(w, h)
    return (
        '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" '
        'tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" '
        'textVerticalWidthHead="0" masterPageCnt="0">'
        '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" strtnum="0"/>'
        '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
        '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" '
        'border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
        '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
        '<hp:pagePr landscape="%s" width="%d" height="%d" gutterType="LEFT_ONLY">'
        '<hp:margin header="%d" footer="%d" gutter="%d" left="%d" right="%d" top="%d" bottom="%d"/>'
        '</hp:pagePr>'
        '<hp:footNotePr>'
        '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
        '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
        '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
        '<hp:numbering type="CONTINUOUS" newNum="1"/>'
        '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
        '</hp:footNotePr>'
        '<hp:endNotePr>'
        '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
        '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
        '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
        '<hp:numbering type="CONTINUOUS" newNum="1"/>'
        '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
        '</hp:endNotePr>'
        '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" '
        'headerInside="0" footerInside="0" fillArea="PAPER">'
        '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
        '</hp:pageBorderFill>'
        '</hp:secPr>'
        % (landscape, w, h,
           mm2unit(m["header"]), mm2unit(m["footer"]), mm2unit(m["gutter"]),
           mm2unit(m["left"]), mm2unit(m["right"]), mm2unit(m["top"]), mm2unit(m["bottom"]))
    )


def build_cell(col, row, fill_id, style_idx, text, width, height, margin_lr=0, margin_tb=0):
    return (
        '<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" '
        'borderFillIDRef="%d">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" '
        'hasTextRef="0" hasNumRef="0">'
        '<hp:p id="0" paraPrIDRef="%d" styleIDRef="%d" pageBreak="0" columnBreak="0" merged="0">'
        '<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>'
        '</hp:p>'
        '</hp:subList>'
        '<hp:cellAddr colAddr="%d" rowAddr="%d"/>'
        '<hp:cellSpan colSpan="1" rowSpan="1"/>'
        '<hp:cellSz width="%d" height="%d"/>'
        '<hp:cellMargin left="%d" right="%d" top="%d" bottom="%d"/>'
        '</hp:tc>'
        % (fill_id, style_idx, style_idx, style_idx, escape(text),
           col, row, width, height, margin_lr, margin_lr, margin_tb, margin_tb)
    )


def build_title_table(cfg, fills, tbl_id, title_text, title_style_idx, plain_idx):
    """문서 상단 제목 표: 액센트 띠 / 제목 / 액센트 띠 3행."""
    tpl = cfg["template"]
    width = text_width_unit(cfg["page"])
    accent_h = int(tpl["accent_height_unit"])
    title_h = int(tpl["title_row_height_unit"])
    total_h = accent_h * 2 + title_h

    outer = fills.solid_box(0.12)
    top_fill = fills.get("accent-top", edges={},
                         gradient=(tpl["accent_start"], tpl["accent_end"]))
    bot_fill = fills.get("accent-bottom", edges={},
                         gradient=(tpl["accent_end"], tpl["accent_start"]))
    plain = fills.plain()

    rows = [
        '<hp:tr>%s</hp:tr>' % build_cell(0, 0, top_fill, plain_idx, "", width, accent_h, 141, 141),
        '<hp:tr>%s</hp:tr>' % build_cell(0, 1, plain, title_style_idx, title_text, width, title_h, 141, 141),
        '<hp:tr>%s</hp:tr>' % build_cell(0, 2, bot_fill, plain_idx, "", width, accent_h, 141, 141),
    ]
    return (
        '<hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="1" '
        'rowCnt="3" colCnt="1" cellSpacing="0" borderFillIDRef="%d" noAdjust="0">'
        '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        'vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="140" right="140" top="140" bottom="140"/>'
        '<hp:inMargin left="140" right="140" top="140" bottom="140"/>'
        '%s</hp:tbl>' % (tbl_id, outer, width, total_h, "".join(rows))
    )


def build_body_table(cfg, fills, tbl_id, tbl_spec, style_index):
    """행정문서형 개방형 표. tbl_spec:
    {"columns": [...], "rows": [[...], ...], "col_widths_percent": [...],
     "header_style": ..., "body_style": ... (문자열 또는 열별 리스트)}"""
    tset = dict(cfg["table"])
    tset.update({k: v for k, v in tbl_spec.items()
                 if k in ("header_style", "body_style", "outer_border_mm",
                          "inner_border_mm", "row_height_unit",
                          "cell_margin_lr_unit", "cell_margin_tb_unit")})

    columns = tbl_spec.get("columns") or []
    rows = tbl_spec.get("rows") or []
    ncol = len(columns) if columns else (len(rows[0]) if rows else 1)
    nrow = len(rows) + (1 if columns else 0)
    if ncol == 0 or nrow == 0:
        raise ValueError("표에 columns 또는 rows가 필요합니다")

    width = text_width_unit(cfg["page"])
    pcts = tbl_spec.get("col_widths_percent")
    if pcts:
        if len(pcts) != ncol:
            raise ValueError("col_widths_percent 개수가 열 수와 다릅니다")
        total = float(sum(pcts))
        col_w = [int(width * p / total) for p in pcts]
    else:
        col_w = [width // ncol] * ncol
    col_w[-1] = width - sum(col_w[:-1])

    header_idx = style_index(tset["header_style"])
    body = tset["body_style"]
    if isinstance(body, str):
        body_idx = [style_index(body)] * ncol
    else:
        if len(body) != ncol:
            raise ValueError("body_style 리스트 개수가 열 수와 다릅니다")
        body_idx = [style_index(b) for b in body]

    outer_mm = float(tset["outer_border_mm"])
    inner_mm = float(tset["inner_border_mm"])
    row_h = int(tset["row_height_unit"])
    m_lr = int(tset["cell_margin_lr_unit"])
    m_tb = int(tset["cell_margin_tb_unit"])

    tr_parts = []
    r = 0
    if columns:
        tcs = []
        for c, text in enumerate(columns):
            fill = fills.cell(c == 0, c == ncol - 1,
                              outer_mm, outer_mm if nrow == 1 else inner_mm, inner_mm)
            tcs.append(build_cell(c, r, fill, header_idx, str(text), col_w[c], row_h, m_lr, m_tb))
        tr_parts.append('<hp:tr>%s</hp:tr>' % "".join(tcs))
        r += 1
    for i, row in enumerate(rows):
        if len(row) != ncol:
            raise ValueError("행 %d의 칸 수(%d)가 열 수(%d)와 다릅니다" % (i + 1, len(row), ncol))
        first_row = (r == 0)
        last_row = (r == nrow - 1)
        tcs = []
        for c, text in enumerate(row):
            fill = fills.cell(c == 0, c == ncol - 1,
                              outer_mm if first_row else inner_mm,
                              outer_mm if last_row else inner_mm, inner_mm)
            tcs.append(build_cell(c, r, fill, body_idx[c], str(text), col_w[c], row_h, m_lr, m_tb))
        tr_parts.append('<hp:tr>%s</hp:tr>' % "".join(tcs))
        r += 1

    outer = fills.solid_box(0.12)
    return (
        '<hp:tbl id="%d" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        'rowCnt="%d" colCnt="%d" cellSpacing="0" borderFillIDRef="%d" noAdjust="1">'
        '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        'vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="%d" right="%d" top="%d" bottom="%d"/>'
        '%s</hp:tbl>'
        % (tbl_id, nrow, ncol, outer, width, row_h * nrow,
           m_lr, m_lr, m_tb, m_tb, "".join(tr_parts))
    )


def build_section_xml(cfg, fills, items):
    """items: [{"kind": "para", "style": idx, "text": str} |
               {"kind": "table", "spec": {...}} |
               {"kind": "title_table", "text": str, "style": idx}]"""
    styles = cfg["styles"]
    name_to_idx = {st["name"]: i for i, st in enumerate(styles)}

    def style_index(ref):
        if isinstance(ref, int):
            idx = ref
        elif ref in name_to_idx:
            idx = name_to_idx[ref]
        else:
            raise KeyError("정의되지 않은 스타일: %r (styles의 name과 일치해야 함)" % ref)
        if not 0 <= idx < len(styles):
            raise IndexError("스타일 인덱스 범위 초과: %r" % ref)
        return idx

    if not items:
        items = [{"kind": "para", "style": 0, "text": ""}]

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
    ]
    plain_idx = style_index("바탕글")
    tbl_id = 1000000000
    for i, item in enumerate(items):
        pid = 2147483648 + i
        prefix = ""
        if i == 0:
            prefix = (build_sec_pr(cfg["page"])
                      + '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" '
                        'sameSz="1" sameGap="0"/></hp:ctrl>')
        if item["kind"] == "para":
            sidx = style_index(item["style"])
            parts.append(
                '<hp:p id="%d" paraPrIDRef="%d" styleIDRef="%d" pageBreak="0" columnBreak="0" merged="0">'
                '<hp:run charPrIDRef="%d">%s<hp:t>%s</hp:t></hp:run></hp:p>'
                % (pid, sidx, sidx, sidx, prefix, escape(item["text"]))
            )
        else:
            if item["kind"] == "title_table":
                tbl_xml = build_title_table(cfg, fills, tbl_id, item["text"],
                                            style_index(item["style"]), plain_idx)
            else:
                tbl_xml = build_body_table(cfg, fills, tbl_id, item["spec"], style_index)
            tbl_id += 1
            # 표는 문단 안에 글자처럼(treatAsChar) 배치
            parts.append(
                '<hp:p id="%d" paraPrIDRef="%d" styleIDRef="%d" pageBreak="0" columnBreak="0" merged="0">'
                '<hp:run charPrIDRef="%d">%s%s</hp:run></hp:p>'
                % (pid, plain_idx, plain_idx, plain_idx, prefix, tbl_xml)
            )
    parts.append('</hs:sec>')
    return "".join(parts)


# ---------------------------------------------------------------- 기타 파트

VERSION_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" '
    'tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="1" buildNumber="0" '
    'os="1" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="11, 0, 0, 5150"/>'
)

SETTINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
    '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>'
    '</ha:HWPApplicationSetting>'
)

CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
    '<ocf:rootfiles>'
    '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
    '</ocf:rootfiles>'
    '</ocf:container>'
)

MANIFEST_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
    '<odf:file-entry odf:full-path="/" odf:media-type="application/hwp+zip"/>'
    '<odf:file-entry odf:full-path="Contents/header.xml" odf:media-type="application/xml"/>'
    '<odf:file-entry odf:full-path="Contents/section0.xml" odf:media-type="application/xml"/>'
    '<odf:file-entry odf:full-path="settings.xml" odf:media-type="application/xml"/>'
    '</odf:manifest>'
)

CONTAINER_RDF = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about=""/>'
    '</rdf:RDF>'
)


def build_content_hpf(title):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" version="" unique-identifier="" id="">'
        '<opf:metadata>'
        '<opf:title>%s</opf:title>'
        '<opf:language>ko</opf:language>'
        '<opf:meta name="CreatedDate" content=""/>'
        '</opf:metadata>'
        '<opf:manifest>'
        '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
        '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
        '<opf:item id="settings" href="settings.xml" media-type="application/xml"/>'
        '</opf:manifest>'
        '<opf:spine>'
        '<opf:itemref idref="header" linear="yes"/>'
        '<opf:itemref idref="section0" linear="yes"/>'
        '</opf:spine>'
        '</opf:package>' % escape(title)
    )


# ---------------------------------------------------------------- 조립

def build_hwpx(cfg, items, out_path):
    """cfg: normalize_config() 결과, items: build_section_xml 형식."""
    fills = FillRegistry()
    # section을 먼저 만들어 사용된 borderFill을 레지스트리에 채운 뒤 header를 만든다
    section_xml = build_section_xml(cfg, fills, items)
    header_xml = build_header_xml(cfg, fills)

    preview_lines = []
    for it in items:
        if it["kind"] == "para":
            preview_lines.append(it["text"])
        elif it["kind"] == "title_table":
            preview_lines.append(it["text"])
        else:
            for row in it["spec"].get("rows", []):
                preview_lines.append(" | ".join(str(c) for c in row))
    preview = "\r\n".join(preview_lines)

    with zipfile.ZipFile(out_path, "w") as zf:
        # mimetype은 반드시 무압축·첫 엔트리
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip",
                    compress_type=zipfile.ZIP_STORED)
        for name, data in (
            ("version.xml", VERSION_XML),
            ("META-INF/container.xml", CONTAINER_XML),
            ("META-INF/manifest.xml", MANIFEST_XML),
            ("META-INF/container.rdf", CONTAINER_RDF),
            ("Contents/content.hpf", build_content_hpf(cfg.get("title", ""))),
            ("Contents/header.xml", header_xml),
            ("Contents/section0.xml", section_xml),
            ("settings.xml", SETTINGS_XML),
            ("Preview/PrvText.txt", preview),
        ):
            zf.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    return out_path


def resolve_items(cfg, content_items, title=None, date_author=None):
    """content JSON 항목을 내부 item 목록으로 바꾼다. 템플릿(제목 표,
    날짜/작성자)은 설정 또는 인자로 주어지면 문서 맨 앞에 자동 배치."""
    tpl = cfg["template"]
    title = title if title is not None else tpl.get("title")
    date_author = date_author if date_author is not None else tpl.get("date_author")

    items = []
    if title:
        items.append({"kind": "title_table", "text": title, "style": tpl["title_style"]})
    if date_author:
        items.append({"kind": "para", "style": tpl["date_author_style"], "text": date_author})

    for item in content_items:
        if "table" in item:
            items.append({"kind": "table", "spec": item["table"]})
            continue
        if "title_table" in item:
            items.append({"kind": "title_table", "text": item["title_table"],
                          "style": item.get("style", tpl["title_style"])})
            continue
        text = item.get("text", "")
        for line in text.split("\n"):
            items.append({"kind": "para", "style": item.get("style", 0), "text": line})
    return items


def main():
    ap = argparse.ArgumentParser(description="스타일이 적용된 HWPX 파일 생성")
    ap.add_argument("--styles", required=True, help="스타일 설정 JSON 파일")
    ap.add_argument("--content", help='내용 JSON 파일: [{"style": "본문", "text": "..."}, {"table": {...}}]')
    ap.add_argument("--text", help="일반 텍스트 파일 (모든 문단에 첫 번째 스타일 적용)")
    ap.add_argument("--title", help="제목 표 텍스트 (설정 파일 template.title보다 우선)")
    ap.add_argument("--date-author", help="작성날짜/작성자 줄 (template.date_author보다 우선)")
    ap.add_argument("-o", "--output", required=True, help="출력 .hwpx 경로")
    args = ap.parse_args()

    with open(args.styles, encoding="utf-8") as f:
        cfg = normalize_config(json.load(f))

    if args.content:
        with open(args.content, encoding="utf-8") as f:
            content_items = json.load(f)
    elif args.text:
        with open(args.text, encoding="utf-8") as f:
            content_items = [{"style": 0, "text": f.read()}]
    else:
        content_items = []

    items = resolve_items(cfg, content_items, args.title, args.date_author)
    if not items:
        ap.error("--content, --text, --title 중 하나는 필요합니다")
    build_hwpx(cfg, items, args.output)
    n_tbl = sum(1 for it in items if it["kind"] != "para")
    print("생성 완료: %s (항목 %d개, 표 %d개, 스타일 %d개)"
          % (args.output, len(items), n_tbl, len(cfg["styles"])))


if __name__ == "__main__":
    main()
