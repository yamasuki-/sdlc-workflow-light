from __future__ import annotations

from dataclasses import dataclass, field

# 確信度: 高 = 機械的にそのまま抽出 / 中 = 解釈を含む（結合セル展開・変更履歴等） / 低 = 人または画像読取で要確認
HIGH, MID, LOW = "高", "中", "低"


@dataclass
class Fragment:
    source: str                 # 出典（形式別の単位: シート!セル / 見出し＋段落 / スライド＋図形 / 見出し＋行）
    kind: str                   # 段落・箇条書き・表行・図・ノート 等
    text: str
    confidence: str = HIGH
    notes: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)   # 画像化した図など（リポジトリ相対パス）
