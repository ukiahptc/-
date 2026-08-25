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
    Contents/section0.xml     <- 본문
    Preview/PrvText.txt

사용법:
    python3 hwpx_generator.py --styles styles.json --content content.json -o out.hwpx
    python3 hwpx_generator.py --styles styles.json --text plain.txt -o out.hwpx

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
    return {"page": page, "fonts": fonts, "styles": styles,
            "title": cfg.get("title", "")}


# ---------------------------------------------------------------- header.xml

def build_fontfaces(styles, fonts):
    """언어 슬롯별 글꼴 목록과 스타일별 글꼴 인덱스를 만든다."""
    per_lang = {}
    for lang in LANGS:
        per_lang[lang] = []

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


def build_border_fill(fid):
    return (
        '<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
        '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
        '</hh:borderFill>' % fid
    )


def build_char_pr(idx, st, ref):
    spacing = int(st["letter_spacing_percent"])
    parts = [
        '<hh:charPr id="%d" height="%d" textColor="%s" shadeColor="none" '
        'useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">'
        % (idx, pt2unit(st["font_size_pt"]), st["color"])
    ]
    parts.append(
        '<hh:fontRef hangul="%(hangul)d" latin="%(latin)d" hanja="%(hanja)d" '
        'japanese="%(japanese)d" other="%(other)d" symbol="%(symbol)d" user="%(user)d"/>' % ref
    )
    ratio = int(st["width_ratio_percent"])
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


def build_para_pr(idx, st, bullet_id=0):
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
        '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" '
        'offsetBottom="0" connect="0" ignoreMargin="0"/>',
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
    return "".join(parts), ids


def build_header_xml(cfg):
    styles = cfg["styles"]
    fontfaces_xml, refs = build_fontfaces(styles, cfg["fonts"])

    bullets_xml, bullet_ids = build_bullets(styles)
    char_prs = "".join(build_char_pr(i, st, refs[i]) for i, st in enumerate(styles))
    para_prs = "".join(build_para_pr(i, st, bullet_ids[i]) for i, st in enumerate(styles))

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
        + '<hh:borderFills itemCnt="2">' + build_border_fill(1) + build_border_fill(2) + '</hh:borderFills>'
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


def build_section_xml(cfg, paragraphs):
    """paragraphs: [(style_index, text), ...]"""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
    ]
    if not paragraphs:
        paragraphs = [(0, "")]
    for i, (style_idx, text) in enumerate(paragraphs):
        pid = 2147483648 + i
        parts.append(
            '<hp:p id="%d" paraPrIDRef="%d" styleIDRef="%d" pageBreak="0" columnBreak="0" merged="0">'
            % (pid, style_idx, style_idx)
        )
        parts.append('<hp:run charPrIDRef="%d">' % style_idx)
        if i == 0:
            parts.append(build_sec_pr(cfg["page"]))
            parts.append(
                '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" '
                'sameSz="1" sameGap="0"/></hp:ctrl>'
            )
        parts.append('<hp:t>%s</hp:t>' % escape(text))
        parts.append('</hp:run>')
        parts.append('</hp:p>')
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

def build_hwpx(cfg, paragraphs, out_path):
    """cfg: normalize_config() 결과, paragraphs: [(style_index, text)]"""
    header_xml = build_header_xml(cfg)
    section_xml = build_section_xml(cfg, paragraphs)
    preview = "\r\n".join(t for _, t in paragraphs)

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


def resolve_paragraphs(cfg, content_items):
    """content_items: [{"style": 이름 또는 인덱스, "text": "..."}] -> [(idx, line)]"""
    name_to_idx = {st["name"]: i for i, st in enumerate(cfg["styles"])}
    paragraphs = []
    for item in content_items:
        ref = item.get("style", 0)
        if isinstance(ref, int):
            idx = ref
        else:
            if ref not in name_to_idx:
                raise KeyError("정의되지 않은 스타일: %r (styles의 name과 일치해야 함)" % ref)
            idx = name_to_idx[ref]
        if not 0 <= idx < len(cfg["styles"]):
            raise IndexError("스타일 인덱스 범위 초과: %d" % idx)
        text = item.get("text", "")
        # 여러 줄 텍스트는 줄 단위로 문단 분리
        for line in text.split("\n"):
            paragraphs.append((idx, line))
    return paragraphs


def main():
    ap = argparse.ArgumentParser(description="스타일이 적용된 HWPX 파일 생성")
    ap.add_argument("--styles", required=True, help="스타일 설정 JSON 파일")
    ap.add_argument("--content", help='내용 JSON 파일: [{"style": "본문", "text": "..."}]')
    ap.add_argument("--text", help="일반 텍스트 파일 (모든 문단에 첫 번째 스타일 적용)")
    ap.add_argument("-o", "--output", required=True, help="출력 .hwpx 경로")
    args = ap.parse_args()

    with open(args.styles, encoding="utf-8") as f:
        cfg = normalize_config(json.load(f))

    if args.content:
        with open(args.content, encoding="utf-8") as f:
            items = json.load(f)
    elif args.text:
        with open(args.text, encoding="utf-8") as f:
            items = [{"style": 0, "text": f.read()}]
    else:
        ap.error("--content 또는 --text 중 하나는 필요합니다")

    paragraphs = resolve_paragraphs(cfg, items)
    build_hwpx(cfg, paragraphs, args.output)
    print("생성 완료: %s (문단 %d개, 스타일 %d개)"
          % (args.output, len(paragraphs), len(cfg["styles"])))


if __name__ == "__main__":
    main()
