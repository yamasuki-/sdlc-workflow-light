"""Word: 出典 = 見出し階層＋段落番号。表は行単位、変更履歴（挿入・削除）と画像は確信度を下げて記録する。"""
from __future__ import annotations

import re
from pathlib import Path

from .base import HIGH, LOW, MID, Fragment

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
HEADING = re.compile(r"^(?:Heading|見出し)\s*(\d)$", re.IGNORECASE)


def _text(el) -> tuple[str, str, bool]:
    """(現在のテキスト（挿入含む・削除除く）, 削除されたテキスト, 挿入を含むか)"""
    cur, deleted, ins = [], [], False
    for node in el.iter():
        if node.tag == f"{W}t":
            cur.append(node.text or "")
        elif node.tag == f"{W}delText":
            deleted.append(node.text or "")
        elif node.tag == f"{W}tab":
            cur.append("\t")
        elif node.tag in (f"{W}br", f"{W}cr"):
            cur.append("\n")
        elif node.tag == f"{W}ins":
            ins = True
    return "".join(cur).strip(), "".join(deleted).strip(), ins


def _style(p, doc) -> str:
    ppr = p.find(f"{W}pPr")
    if ppr is None:
        return ""
    ps = ppr.find(f"{W}pStyle")
    if ps is None:
        return ""
    sid = ps.get(f"{W}val")
    try:
        return doc.styles.get_by_id(sid, 1).name or sid  # 1 = WD_STYLE_TYPE.PARAGRAPH
    except Exception:  # noqa: BLE001
        return sid or ""


def _is_list(p) -> bool:
    ppr = p.find(f"{W}pPr")
    return ppr is not None and ppr.find(f"{W}numPr") is not None


def convert(path: Path, assets_dir: Path, rel_assets: str) -> list[Fragment]:
    import docx

    doc = docx.Document(str(path))
    body = doc.element.body
    heads: list[str] = []
    out: list[Fragment] = []
    para_no = 0
    table_no = 0
    img_no = 0

    def where(extra):
        return (" > ".join(heads) or "（見出しなし）") + f" / {extra}"

    def images(el, src):
        nonlocal img_no
        for blip in el.iter(f"{A}blip"):
            rid = blip.get(f"{R}embed")
            part = doc.part.related_parts.get(rid) if rid else None
            if part is None:
                continue
            img_no += 1
            ext = Path(part.partname).suffix or ".png"
            name = f"{path.stem}-img{img_no}{ext}"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / name).write_bytes(part.blob)
            out.append(Fragment(f"{src}（画像{img_no}）", "図", "要画像読取", LOW,
                                ["画像の内容を読み取り、本文と確信度を記入すること"], [f"{rel_assets}/{name}"]))

    for el in body.iterchildren():
        if el.tag == f"{W}p":
            para_no += 1
            text, deleted, ins = _text(el)
            style = _style(el, doc)
            m = HEADING.match(style)
            level = int(m.group(1)) if m else (1 if style in ("Title", "表題") else 0)
            if level and text:
                heads[:] = heads[: level - 1] + [text]
                continue
            src = where(f"段落{para_no}")
            images(el, src)
            if not text and not deleted:
                continue
            conf, notes = HIGH, []
            if ins:
                conf = MID
                notes.append("変更履歴（挿入）を含む。承認済みの変更か確認")
            if deleted:
                conf = LOW if not text else MID
                notes.append(f"変更履歴（削除）あり: 「{deleted}」")
            out.append(Fragment(src, "箇条書き" if _is_list(el) else "段落", text or "（削除のみ）", conf, notes))
        elif el.tag == f"{W}tbl":
            table_no += 1
            rows = el.findall(f"{W}tr")
            header = None
            for rn, tr in enumerate(rows, 1):
                cells = []
                flags = set()
                for tc in tr.findall(f"{W}tc"):
                    t, d, ins = _text(tc)
                    cells.append(t)
                    if ins:
                        flags.add("ins")
                    if d:
                        flags.add("del")
                    tcpr = tc.find(f"{W}tcPr")
                    if tcpr is not None and (tcpr.find(f"{W}vMerge") is not None or tcpr.find(f"{W}gridSpan") is not None):
                        flags.add("merge")
                if header is None:
                    header = cells
                    continue
                if not any(cells):
                    continue
                text = "\n".join(f"{h or f'列{i + 1}'}: {v}" for i, (h, v) in enumerate(zip(header, cells)) if v)
                conf, notes = HIGH, []
                if flags & {"merge", "ins"}:
                    conf = MID
                    notes.append("結合セルまたは変更履歴（挿入）を含む")
                if "del" in flags:
                    conf = MID
                    notes.append("変更履歴（削除）を含む")
                src = where(f"表{table_no} 行{rn}")
                out.append(Fragment(src, "表行", text, conf, notes))
                images(tr, src)
    return out
