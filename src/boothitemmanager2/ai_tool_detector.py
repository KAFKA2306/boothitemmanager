"""Evidence-based detection of AI-related BOOTH tools.

The detector only classifies an item when the seller's own title, description,
tags, or category contains explicit positive evidence. A shop-level signal never
propagates to the shop's other products.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
import re
import unicodedata
from typing import Any, Iterable


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    weight: int
    label: str
    family: str


NEGATIVE_CONTEXT_PATTERNS = (
    re.compile(r"AI生成物を含みません", re.IGNORECASE),
    re.compile(r"NO\s+AI(?:\s+TRAINING)?", re.IGNORECASE),
    re.compile(
        r"(?:AI|生成AI|機械学習).{0,40}?"
        r"(?:禁止|不可|利用しない|使用しない|学習させない|入力しない)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:禁止|不可).{0,40}?(?:AI|生成AI|機械学習)",
        re.IGNORECASE,
    ),
)

CORE_RULES = (
    Rule(
        "explicit_ai_assistant",
        re.compile(
            r"(?:AI\s*(?:assistant|アシスタント|chat|チャット|tool|ツール)"
            r"|(?:assistant|アシスタント).{0,8}(?<![A-Za-z0-9])AI(?![A-Za-z0-9]))",
            re.IGNORECASE,
        ),
        8,
        "AIアシスタント／AIツールを明示",
        "core",
    ),
    Rule(
        "named_ai_service",
        re.compile(
            r"(?<![A-Za-z0-9])(?:ChatGPT|GPT(?:-[34])?|OpenAI|Claude|Gemini|"
            r"Whisper|Stable\s*Diffusion|ComfyUI|Midjourney|ElevenLabs|LLM|LoRA)"
            r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
        5,
        "AIモデル・サービス名を明示",
        "core",
    ),
    Rule(
        "generative_ai",
        re.compile(
            r"(?:生成AI|AI生成|AIによる生成|AIで生成|AIを使って生成|"
            r"AIを使ったツール|AIを使ってツール)",
            re.IGNORECASE,
        ),
        6,
        "生成AIまたはAI利用を明示",
        "core",
    ),
    Rule(
        "standalone_ai",
        re.compile(r"(?<![A-Za-z0-9])AI(?![A-Za-z0-9])", re.IGNORECASE),
        3,
        "AIという語を明示",
        "core",
    ),
)

DISCLOSURE_RULES = (
    Rule(
        "ai_generated_components_disclosure",
        re.compile(
            r"AI生成物を(?:一部に)?含みます|AI生成物が(?:一部)?含まれます",
            re.IGNORECASE,
        ),
        10,
        "AI生成物の含有を販売者が開示",
        "disclosure",
    ),
    Rule(
        "ai_assisted_creation_disclosure",
        re.compile(
            r"(?:ChatGPT|生成AI|AI)を(?:活用|使用|利用)して(?:作成|制作|開発|実装)"
            r"|(?:ChatGPT|生成AI|AI)で(?:作成|制作|開発|実装)",
            re.IGNORECASE,
        ),
        8,
        "AI支援での作成・開発を販売者が開示",
        "disclosure",
    ),
)

TOOL_CONTEXT_RULES = (
    Rule(
        "tool_context",
        re.compile(
            r"(?:ツール|tool|editor|エディタ|assistant|アシスタント|"
            r"翻訳|translat|チャット|chat|生成|generator|補助|自動化|API)",
            re.IGNORECASE,
        ),
        2,
        "ツール／機能提供の文脈",
        "tool",
    ),
    Rule(
        "ai_behavior",
        re.compile(
            r"(?:プロンプト|文脈を理解|質問に回答|テキストを生成|音声を生成|"
            r"リアルタイム翻訳|音声認識|voice[- ]?to[- ]?text)",
            re.IGNORECASE,
        ),
        2,
        "AIらしい入出力機能を説明",
        "tool",
    ),
)


def _normalise(value: Any) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value))


def _mask_negative_context(text: str) -> str:
    masked = text
    for pattern in NEGATIVE_CONTEXT_PATTERNS:
        masked = pattern.sub(lambda match: " " * len(match.group(0)), masked)
    return masked


def _item_value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _category_value(item: Any) -> str:
    category = _item_value(item, "category", "")
    if isinstance(category, Enum):
        return str(category.value)
    return str(category or "")


def _tags_text(item: Any) -> str:
    values: list[str] = []
    for key in ("tags_raw", "tags", "tags_generated"):
        value = _item_value(item, key, [])
        if callable(value):
            value = value()
        if isinstance(value, (list, tuple, set)):
            values.extend(_normalise(v) for v in value)
    tag_set = _item_value(item, "tag_set")
    if tag_set is not None:
        if isinstance(tag_set, dict):
            tag_values = tag_set.values()
        else:
            tag_values = getattr(tag_set, "__dict__", {}).values()
        for value in tag_values:
            if isinstance(value, (list, tuple, set)):
                values.extend(_normalise(v) for v in value)
    return " ".join(v for v in values if v)


def _snippet(text: str, start: int, end: int, radius: int = 54) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    prefix = "…" if left else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{text[left:right].strip()}{suffix}"


def _collect_evidence(field: str, text: str) -> list[dict[str, Any]]:
    clean_text = _normalise(text)
    positive_text = _mask_negative_context(clean_text)
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in (*DISCLOSURE_RULES, *CORE_RULES, *TOOL_CONTEXT_RULES):
        for match in rule.pattern.finditer(positive_text):
            key = (rule.rule_id, match.group(0).casefold())
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "rule_id": rule.rule_id,
                    "family": rule.family,
                    "field": field,
                    "label": rule.label,
                    "matched_text": clean_text[match.start() : match.end()],
                    "snippet": _snippet(clean_text, match.start(), match.end()),
                    "weight": rule.weight,
                }
            )
    return evidence


def detect_ai_tool_candidate(item: Any) -> dict[str, Any] | None:
    """Return an evidence record or ``None`` when positive evidence is insufficient."""

    fields = {
        "title": _normalise(_item_value(item, "title", "")),
        "description": _normalise(_item_value(item, "description", "")),
        "tags": _tags_text(item),
    }
    evidence: list[dict[str, Any]] = []
    for field, text in fields.items():
        if text:
            evidence.extend(_collect_evidence(field, text))

    max_weight_by_rule: dict[str, int] = {}
    for ev in evidence:
        max_weight_by_rule[ev["rule_id"]] = max(
            ev["weight"], max_weight_by_rule.get(ev["rule_id"], 0)
        )

    families = {ev["family"] for ev in evidence}
    category = _category_value(item).upper()
    has_disclosure = "disclosure" in families
    has_core = "core" in families
    has_tool_context = "tool" in families or category == "GIMMICK_TOOL"

    if not has_disclosure and not (has_core and has_tool_context):
        return None

    score = sum(max_weight_by_rule.values())
    if has_disclosure:
        if "ai_generated_components_disclosure" in max_weight_by_rule:
            classification = "AI_GENERATED_COMPONENTS"
        else:
            classification = "AI_ASSISTED_CREATION"
    elif "explicit_ai_assistant" in max_weight_by_rule:
        classification = "AI_TOOL"
    elif "named_ai_service" in max_weight_by_rule:
        classification = "AI_SERVICE_INTEGRATION"
    else:
        classification = "AI_RELATED_TOOL"

    if score >= 12:
        confidence = "HIGH"
    elif score >= 8:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    item_id = str(_item_value(item, "item_id", _item_value(item, "id", "")) or "")
    source_url = _normalise(
        _item_value(
            item,
            "source_url",
            _item_value(item, "booth_url", f"https://booth.pm/ja/items/{item_id}"),
        )
    )
    creator_name = _normalise(
        _item_value(item, "creator_name", _item_value(item, "author", "Unknown Shop"))
    )
    creator_id = _normalise(_item_value(item, "creator_id", ""))

    return {
        "item_id": item_id,
        "title": fields["title"],
        "creator_name": creator_name,
        "creator_id": creator_id,
        "source_url": source_url,
        "category": category,
        "classification": classification,
        "confidence": confidence,
        "score": score,
        "evidence": evidence,
    }


def build_ai_tool_report(
    items: Iterable[Any],
    *,
    generated_at: str | None = None,
    source: str = "catalog",
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    shop_candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for item in items:
        candidate = detect_ai_tool_candidate(item)
        if candidate is None:
            continue
        candidates.append(candidate)
        shop_key = (candidate["creator_id"], candidate["creator_name"])
        shop_candidates[shop_key].append(candidate)

    candidates.sort(key=lambda row: (-row["score"], row["title"], row["item_id"]))

    shops = []
    for (creator_id, creator_name), rows in shop_candidates.items():
        rows.sort(key=lambda row: (-row["score"], row["title"]))
        shops.append(
            {
                "creator_id": creator_id,
                "creator_name": creator_name,
                "signal": "SHOP_SELLS_EXPLICIT_AI_RELATED_ITEM",
                "candidate_count": len(rows),
                "max_score": max(row["score"] for row in rows),
                "item_ids": [row["item_id"] for row in rows],
                "item_urls": [row["source_url"] for row in rows],
                "note": (
                    "このシグナルは当該ショップがAI関連商品を販売している事実だけを表し、"
                    "同ショップの他商品がAI制作であることを意味しません。"
                ),
            }
        )
    shops.sort(key=lambda row: (-row["candidate_count"], -row["max_score"], row["creator_name"]))

    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "1.0",
        "generated_at": timestamp,
        "source": source,
        "policy": {
            "positive_evidence_only": True,
            "shop_signal_does_not_propagate": True,
            "negative_ai_policy_mentions_are_excluded": True,
            "automation_without_ai_evidence_is_excluded": True,
            "disclaimer": (
                "販売ページ上の明示情報を抽出した候補リストです。"
                "衣装・モデルその他の制作方法を断定するものではありません。"
            ),
        },
        "metrics": {
            "candidate_items": len(candidates),
            "candidate_shops": len(shops),
        },
        "shops": shops,
        "items": candidates,
    }


def write_ai_tool_report(
    items: Iterable[Any],
    output_paths: Iterable[str] = ("api/ai_tool_candidates.json",),
) -> dict[str, Any]:
    report = build_ai_tool_report(items)
    for path in output_paths:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return report
