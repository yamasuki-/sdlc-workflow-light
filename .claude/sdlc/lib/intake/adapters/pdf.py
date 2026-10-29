"""PDF: 出典 = 見出し＋ページ番号＋段落番号（表は表番号＋行）。テキスト層から抽出し、表は行単位の断片にする。

PDF は段落・見出しの構造を持たないため、段落は行間と行頭の記号から、見出しは文字の大きさから推定する。
画像や線・図形で描いた図（構成図・フロー等）を含むページと、テキスト層の無いページ（スキャン）は
ページ全体を画像化して「要画像読取」（確信度 低）にする。
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path

from .base import HIGH, LOW, MID, Fragment

# 行頭の箇条書き記号（全角の記号・丸数字は直後の空白なしでもよい。半角の記号・番号は空白が続くものだけ）
BULLET = re.compile(r"^\s*(?:[・•●○■□◆◇▪‣①-⑳]|[*\-–]\s|\(?\d{1,3}[.)）]\s|[（(]\d{1,3}[)）])")
HEADING_RATIO = 1.2     # 本文の文字サイズのこの倍率以上で、短い行を見出しとみなす
HEADING_MAX_LEN = 60
DRAWING_MIN = 4         # 表の外にある線・矩形・曲線がこの数以上あるページは図を含むとみなす
IMAGE_MIN_AREA = 2500   # pt²（約 50pt 四方）未満の画像はアイコン・ロゴとみなして無視
RESOLUTION = 100


def _size(line) -> float:
    sizes = [c.get("size", 0) for c in line.get("chars", []) if str(c.get("text", "")).strip()]
    return statistics.median(sizes) if sizes else 0


def _inside(obj, boxes) -> bool:
    return any(b[0] - 1 <= obj["x0"] and obj["x1"] <= b[2] + 1 and b[1] - 1 <= obj["top"] and obj["bottom"] <= b[3] + 1
               for b in boxes)


def _render(page, name: str, assets_dir: Path, rel_assets: str) -> str | None:
    try:
        assets_dir.mkdir(parents=True, exist_ok=True)
        page.to_image(resolution=RESOLUTION).save(assets_dir / name)
        return f"{rel_assets}/{name}"
    except Exception:  # noqa: BLE001 — 画像化できなくても取り込みは続ける（要画像読取として残す）
        return None


def convert(path: Path, assets_dir: Path, rel_assets: str) -> list[Fragment]:
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit("エラー: PDF の取り込みには pdfplumber が必要です（pip install -r requirements.txt）。")

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as e:  # noqa: BLE001 — パスワード付き・破損
        raise SystemExit(f"エラー: PDF を開けません（パスワード付き・破損の可能性）: {path.name}: {e}")

    out: list[Fragment] = []
    heads: list[tuple[float, str]] = []   # (文字サイズ, 見出し)
    table_no = 0
    with pdf:
        pages = []
        for page in pdf.pages:
            tables = page.find_tables()
            boxes = [t.bbox for t in tables]
            body = page.filter(lambda o: o.get("object_type") != "char" or not _inside(o, boxes)) if boxes else page
            lines = [ln for ln in body.extract_text_lines() if ln["text"].strip()]
            pages.append((page, tables, boxes, lines))
        sizes = [_size(ln) for _, _, _, lines in pages for ln in lines]
        body_size = statistics.median(sizes) if sizes else 0

        for pn, (page, tables, boxes, lines) in enumerate(pages, 1):
            def where(extra):
                return (" > ".join(h for _, h in heads) or "（見出しなし）") + f" / p.{pn} {extra}"

            # 段落: 行間が空いた所・行頭が記号の所で区切る。表は位置順に差し込む
            items = [("line", ln["top"], ln) for ln in lines] + [("table", t.bbox[1], t) for t in tables]
            items.sort(key=lambda x: x[1])
            para_no = 0
            para: list[dict] = []

            def flush():
                nonlocal para_no, para
                if not para:
                    return
                para_no += 1
                text = "\n".join(ln["text"].strip() for ln in para)
                out.append(Fragment(where(f"段落{para_no}"), "箇条書き" if BULLET.match(para[0]["text"]) else "段落", text, HIGH))
                para = []

            for kind, _, it in items:
                if kind == "table":
                    flush()
                    table_no += 1
                    rows = it.extract()
                    header = [str(c or "").strip() for c in rows[0]] if rows else []
                    for rn, row in enumerate(rows[1:], 2):
                        cells = [str(c or "").strip() for c in row]
                        if not any(cells):
                            continue
                        text = "\n".join(f"{h or f'列{i + 1}'}: {v}" for i, (h, v) in enumerate(zip(header, cells)) if v)
                        notes = ["PDF の表は罫線から推定して抽出している。列のずれ・結合セルを原本と照合"]
                        if any(c is None for c in row):
                            notes.append("結合セルを含む可能性")
                        out.append(Fragment(where(f"表{table_no} 行{rn}"), "表行", text, MID, notes))
                    continue
                ln = it
                size = _size(ln)
                if body_size and size >= body_size * HEADING_RATIO and len(ln["text"].strip()) <= HEADING_MAX_LEN:
                    flush()
                    heads[:] = [h for h in heads if h[0] > size] + [(size, ln["text"].strip())]
                    continue
                if para:
                    prev = para[-1]
                    gap = ln["top"] - prev["bottom"]
                    if gap > max((prev["bottom"] - prev["top"]) * 0.6, 2) or BULLET.match(ln["text"]):
                        flush()
                para.append(ln)
            flush()

            # 図・スキャン: ページ全体を画像化して読み取り対象にする
            images = [im for im in page.images
                      if (im["x1"] - im["x0"]) * (im["bottom"] - im["top"]) >= IMAGE_MIN_AREA]
            drawings = [o for o in page.lines + page.rects + page.curves if not _inside(o, boxes)]
            scanned = not page.chars and (images or drawings)
            if scanned or images or len(drawings) >= DRAWING_MIN:
                asset = _render(page, f"{path.stem}-page{pn}.png", assets_dir, rel_assets)
                note = ("テキスト層が無い（スキャン等）。ページ画像から本文を読み取り、確信度を記入すること" if scanned else
                        "画像または線・図形で描いた図（構成図・フロー等）を含む。ページ画像から図の要素と関係を読み取り、"
                        "本文と確信度を記入すること（ページ内のテキストは別の断片として抽出済み）")
                if asset:
                    out.append(Fragment(f"p.{pn} / ページ全体（画像化）", "図", "要画像読取", LOW, [note], [asset]))
                else:
                    out.append(Fragment(f"p.{pn} / ページ全体", "図", "要画像読取（画像化できず）", LOW,
                                        [note + "。人に画像を提供してもらうか質問リストに回す"]))

            for an in page.annots or []:
                text = str(an.get("contents") or "").strip()
                if text:
                    out.append(Fragment(f"p.{pn} / 注釈", "注釈", text, MID, ["PDF の注釈（コメント）。要求か補足かを確認"]))
    return out
