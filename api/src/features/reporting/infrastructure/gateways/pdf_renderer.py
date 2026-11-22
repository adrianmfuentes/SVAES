import asyncio
import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image,
)
from reportlab.lib import colors
from reportlab.platypus.flowables import Flowable

from features.projects_releases.domain.release import Release
from features.verification.domain.verification_result import VerificationResult
from .pdf_labels import _rule_name, _t, _translate_evidence, _verdict_label

_INK         = (13/255,  15/255,  18/255)
_PAPER       = (246/255, 244/255, 240/255)
_PAPER2      = (237/255, 234/255, 228/255)
_ACCENT      = (232/255, 213/255, 163/255)
_BORDER      = (212/255, 207/255, 199/255)
_BORDER_STR  = (158/255, 152/255, 144/255)
_MUTED       = (122/255, 118/255, 112/255)

_VALID       = (42/255,  107/255, 60/255)
_VALID_BG    = (232/255, 245/255, 236/255)
_VALID_BDR   = (168/255, 213/255, 181/255)

_INVALID     = (139/255, 26/255,  26/255)
_INVALID_BG  = (250/255, 234/255, 234/255)
_INVALID_BDR = (216/255, 128/255, 128/255)

_WARN        = (139/255, 94/255,  0/255)
_WARN_BG     = (253/255, 243/255, 220/255)
_WARN_BDR    = (223/255, 192/255, 112/255)

_UNEVAL      = (90/255,  94/255,  101/255)
_UNEVAL_BG   = (235/255, 235/255, 235/255)
_UNEVAL_BDR  = (192/255, 192/255, 192/255)


def _verdict_colors(verdict_str: str) -> tuple:
    v = verdict_str.upper()
    if v == "VALID":
        return _VALID, _VALID_BG, _VALID_BDR
    if v == "INVALID":
        return _INVALID, _INVALID_BG, _INVALID_BDR
    if "WARNING" in v:
        return _WARN, _WARN_BG, _WARN_BDR
    return _UNEVAL, _UNEVAL_BG, _UNEVAL_BDR


def _status_colors(status: str) -> tuple:
    s = (status or "").upper()
    if s == "OK":
        return _VALID, _VALID_BG, _VALID_BDR
    if s in ("ERROR", "FAILED"):
        return _INVALID, _INVALID_BG, _INVALID_BDR
    if s in ("WARNING", "WARN"):
        return _WARN, _WARN_BG, _WARN_BDR
    return _UNEVAL, _UNEVAL_BG, _UNEVAL_BDR


_LOGO_PATH = "/app/static/images/icon-192.png"


class _HeaderFlowable(Flowable):
    def __init__(self, content_w: float, logo_sz: float, logo_off: float,
                 use_logo: bool, gen_date: str, lang: str):
        self._content_w = content_w
        self._logo_sz = logo_sz
        self._logo_off = logo_off
        self._use_logo = use_logo
        self._gen_date = gen_date
        self._lang = lang

    def wrap(self, aW: float, aH: float) -> tuple[float, float]:  # NOSONAR
        return self._content_w, self._logo_sz

    def draw(self):
        c = self.canv
        if self._use_logo:
            logo = Image(_LOGO_PATH, width=self._logo_sz, height=self._logo_sz)
            logo.drawOn(c, 0, 0)
        else:
            c.setFillColorRGB(*_ACCENT)
            c.rect(0, 4 * mm, 6, 6, fill=1, stroke=0)
        c.setFillColorRGB(*_INK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self._logo_off, 5 * mm, "SVAES")
        c.setFillColorRGB(*_MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(self._logo_off, 1.5 * mm, _t(self._lang, "generated_by"))
        c.setFillColorRGB(*_MUTED)
        c.setFont("Helvetica", 7)
        c.drawRightString(self._content_w, 1.5 * mm, self._gen_date)
        c.setFillColorRGB(*_INK)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(self._content_w, 5 * mm, _t(self._lang, "report_title").upper())


class _VerdictBlock(Flowable):
    """Clean typographic verdict — thin left stripe, no colored fill."""

    _STRIPE = 3       # stripe width in points
    _PAD    = 4 * mm  # text left-offset from stripe
    _H      = 18 * mm # total height

    def __init__(self, content_w: float, verdict_text: str, result_id: str,
                 exec_at: str, fg):
        self._content_w  = content_w
        self._verdict_text = verdict_text
        self._result_id  = result_id
        self._exec_at    = exec_at
        self._fg         = fg

    def wrap(self, aW: float, aH: float) -> tuple[float, float]:  # NOSONAR
        return self._content_w, self._H

    def draw(self):
        c  = self.canv
        tx = self._STRIPE + self._PAD

        # thin left accent stripe
        c.setFillColorRGB(*self._fg)
        c.rect(0, 0, self._STRIPE, self._H, fill=1, stroke=0)

        # verdict text
        c.setFont("Helvetica-Bold", 15)
        c.drawString(tx, self._H * 0.50, self._verdict_text)

        # meta: truncated ID on left, execution date on right
        c.setFillColorRGB(*_MUTED)
        c.setFont("Courier", 7.5)
        c.drawString(tx, 2.5 * mm, self._result_id[:8] + "…")
        c.setFont("Helvetica", 8)
        c.drawRightString(self._content_w, 2.5 * mm, self._exec_at)


def _section_label(text: str, content_w: float, muted_c, border_c) -> list:
    return [
        Spacer(1, 5 * mm),
        Paragraph(
            text.upper(),
            ParagraphStyle("SL", fontName="Helvetica-Bold", fontSize=7,
                          textColor=muted_c, leading=9, spaceAfter=2 * mm),
        ),
        HRFlowable(width=content_w, thickness=0.5, color=border_c, spaceAfter=3 * mm),
    ]


def _build_rules_table(rules: list, ok_count: int, err_count: int, warn_count: int,
                        lang: str, content_w: float, muted_c, ink_c) -> tuple:
    n = len(rules)
    summary_line = (
        f"{n} {_t(lang, 'summary_rules')}  ·  "
        f"{ok_count} {_t(lang, 'summary_ok')}  ·  "
        f"{err_count} {_t(lang, 'summary_errors')}"
    )
    if warn_count:
        summary_line += f"  ·  {warn_count} {_t(lang, 'summary_warnings')}"

    th_s = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7,
                          textColor=muted_c, leading=9)
    tid_s = ParagraphStyle("TID", fontName="Courier", fontSize=7.5,
                          textColor=ink_c, leading=10)
    tnm_s = ParagraphStyle("TNM", fontName="Helvetica", fontSize=8,
                          textColor=ink_c, leading=11)
    tmg_s = ParagraphStyle("TMG", fontName="Helvetica", fontSize=7.5,
                          textColor=muted_c, leading=10)

    COL_ID  = 1.6 * cm
    COL_NM  = 7.0 * cm
    COL_ST  = 2.0 * cm
    COL_MSG = content_w - COL_ID - COL_NM - COL_ST

    data_rows = [[
        Paragraph(_t(lang, "col_rule_id").upper(), th_s),
        Paragraph(_t(lang, "col_rule_name").upper(), th_s),
        Paragraph(_t(lang, "col_status").upper(), th_s),
        Paragraph(_t(lang, "col_message").upper(), th_s),
    ]]

    for rule in rules:
        rule_id = rule.get("rule_id") or "–"
        status = (rule.get("status") or "").upper()
        evidence_key = rule.get("evidence") or rule.get("message")
        evidence_params = rule.get("evidence_params")
        if evidence_key is None or str(evidence_key).strip().lower() == "none":
            detail = _t(lang, "no_detail")
        else:
            detail = _translate_evidence(lang, evidence_key, evidence_params)
            if detail == evidence_key and status == "OK":
                detail = _t(lang, "no_detail")
        st_label = _t(lang, f"status_{status.lower()}") or status
        st_s = ParagraphStyle("ST", fontName="Helvetica", fontSize=8,
                             textColor=ink_c, leading=10)
        data_rows.append([
            Paragraph(rule_id, tid_s),
            Paragraph(_rule_name(lang, rule_id), tnm_s),
            Paragraph(st_label, st_s),
            Paragraph(detail, tmg_s),
        ])

    rules_table = Table(data_rows, colWidths=[COL_ID, COL_NM, COL_ST, COL_MSG], repeatRows=1)
    rules_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*_PAPER2)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.Color(*_BORDER_STR)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.Color(*_BORDER)),
    ]))

    summary_para = Paragraph(
        summary_line,
        ParagraphStyle("Sum", fontName="Helvetica", fontSize=8,
                      textColor=muted_c, leading=11, spaceAfter=4 * mm),
    )
    return summary_para, rules_table


def _build_pdf(pdf_path: str, result, release, lang: str) -> None:
    PAGE_W, _ = A4
    MARGIN    = 2.0 * cm
    CONTENT_W = PAGE_W - 2 * MARGIN

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=1.5 * cm, bottomMargin=2.0 * cm,
        title=_t(lang, "report_title"), author="SVAES",
    )

    # ── computed values ───────────────────────────────────────────────────────
    verdict_str  = result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict)
    verdict_text = _verdict_label(lang, result.verdict)
    fg_v, _, _ = _verdict_colors(verdict_str)

    rules      = result.rule_results or []
    ok_count   = sum(1 for r in rules if (r.get("status") or "").upper() == "OK")
    err_count  = sum(1 for r in rules if (r.get("status") or "").upper() in ("ERROR", "FAILED"))
    warn_count = sum(1 for r in rules if (r.get("status") or "").upper() in ("WARNING", "WARN"))

    r_name    = getattr(release, "name",    None) or _t(lang, "na")
    r_version = getattr(release, "version", None) or _t(lang, "na")
    exec_at   = (
        result.executed_at.strftime("%d/%m/%Y %H:%M UTC")
        if result.executed_at else _t(lang, "na")
    )
    duration  = f"{result.duration_ms} {_t(lang, 'duration_ms')}"
    gen_date  = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    muted_c = colors.Color(*_MUTED)
    ink_c   = colors.Color(*_INK)
    border_c = colors.Color(*_BORDER)

    _use_logo = os.path.isfile(_LOGO_PATH)
    LOGO_SZ   = 14 * mm
    LOGO_OFF  = (LOGO_SZ + 3 * mm) if _use_logo else 0

    # ── story ─────────────────────────────────────────────────────────────────
    story = [
        _HeaderFlowable(CONTENT_W, LOGO_SZ, LOGO_OFF, _use_logo, gen_date, lang),
        HRFlowable(
            width=CONTENT_W, thickness=0.5, color=border_c,
            spaceBefore=3 * mm, spaceAfter=5 * mm,
        ),
        Paragraph(
            _t(lang, "report_title"),
            ParagraphStyle("Title", fontName="Times-Roman", fontSize=22,
                           textColor=ink_c, leading=26, spaceAfter=2 * mm),
        ),
        Paragraph(
            f"{r_name}  ·  {r_version}  ·  {_t(lang, 'field_executed_at')}: {exec_at}",
            ParagraphStyle("Meta", fontName="Helvetica", fontSize=8,
                           textColor=muted_c, leading=11, spaceAfter=4 * mm),
        ),
        HRFlowable(width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=0),
        _VerdictBlock(CONTENT_W, verdict_text, str(result.id), exec_at, fg_v),
        HRFlowable(width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=5 * mm),
    ]

    # ── Delivery info ─────────────────────────────────────────────────────────
    story.extend(_section_label(_t(lang, "section_release"), CONTENT_W, muted_c, border_c))

    lbl_s = ParagraphStyle("Lbl", fontName="Helvetica-Bold", fontSize=7, textColor=muted_c, leading=9)
    val_s = ParagraphStyle("Val", fontName="Helvetica", fontSize=8.5, textColor=ink_c, leading=11)
    mon_s = ParagraphStyle("Mon", fontName="Courier", fontSize=8, textColor=ink_c, leading=11)

    C1, C2 = CONTENT_W * 0.28, CONTENT_W * 0.72

    def _info(label, value, mono=False):
        return [
            Paragraph(label, lbl_s),
            Paragraph(str(value) if value else _t(lang, "na"), mon_s if mono else val_s),
        ]

    info_data = [
        _info(_t(lang, "field_release_name"),    r_name),
        _info(_t(lang, "field_release_version"), r_version),
        _info(_t(lang, "field_release_id"),      str(result.release_id), mono=True),
        _info(_t(lang, "field_verification_id"), str(result.id),         mono=True),
        _info(_t(lang, "field_executed_at"),     exec_at),
        _info(_t(lang, "field_duration"),        duration),
    ]
    info_table = Table(info_data, colWidths=[C1, C2])
    info_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, border_c),
    ]))
    story.append(info_table)

    # ── Rules ─────────────────────────────────────────────────────────────────
    story.extend(_section_label(_t(lang, "section_rules"), CONTENT_W, muted_c, border_c))
    summary_para, rules_table = _build_rules_table(
        rules, ok_count, err_count, warn_count, lang, CONTENT_W, muted_c, ink_c,
    )
    story.extend([summary_para, rules_table])

    # ── Footer ────────────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 8 * mm),
        HRFlowable(width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=3 * mm),
        Paragraph(
            f"SVAES  ·  {_t(lang, 'footer_note')}  ·  {gen_date}",
            ParagraphStyle("Foot", fontName="Helvetica", fontSize=7.5,
                           textColor=muted_c, leading=10, alignment=1),
        ),
    ])

    doc.build(story)


class PdfRenderer:
    async def render(
        self, path: str, result: VerificationResult, release: Release | None, lang: str,
    ) -> None:
        await asyncio.to_thread(_build_pdf, path, result, release, lang)
