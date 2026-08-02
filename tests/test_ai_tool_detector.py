import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from boothitemmanager2.ai_tool_detector import build_ai_tool_report, detect_ai_tool_candidate


@dataclass
class FakeItem:
    item_id: str
    title: str
    description: str
    category: str = "GIMMICK_TOOL"
    creator_name: str = "Test Shop"
    creator_id: str = "test-shop"
    source_url: str = ""
    tags_raw: list[str] = field(default_factory=list)


def test_explicit_ai_assistant_is_detected():
    item = FakeItem(
        item_id="1",
        title="VRChat AI Assistant",
        description="Unity内で質問に回答するAIチャットツールです。",
        source_url="https://booth.pm/ja/items/1",
    )
    result = detect_ai_tool_candidate(item)
    assert result is not None
    assert result["classification"] == "AI_TOOL"
    assert result["confidence"] == "HIGH"


def test_ai_generated_components_disclosure_is_detected():
    item = FakeItem(
        item_id="2",
        title="サムネ作成補助ツール",
        description="AI生成物を一部に含みます。対象はEditor拡張のコードです。",
        source_url="https://booth.pm/ja/items/2",
    )
    result = detect_ai_tool_candidate(item)
    assert result is not None
    assert result["classification"] == "AI_GENERATED_COMPONENTS"


def test_ai_training_prohibition_is_not_positive_evidence():
    item = FakeItem(
        item_id="3",
        title="テクスチャ圧縮ツール",
        description="本製品をAI学習、機械学習、生成AIへの入力に使用することは禁止します。",
        source_url="https://booth.pm/ja/items/3",
    )
    assert detect_ai_tool_candidate(item) is None


def test_automation_only_is_not_ai():
    item = FakeItem(
        item_id="4",
        title="メニュー自動生成ツール",
        description="Expression Menuを自動生成します。",
        source_url="https://booth.pm/ja/items/4",
    )
    assert detect_ai_tool_candidate(item) is None


def test_shop_signal_does_not_propagate_to_other_items():
    ai_item = FakeItem(
        item_id="5",
        title="ChatGPT翻訳ツール",
        description="ChatGPT APIを使ったリアルタイム翻訳ツールです。",
        source_url="https://booth.pm/ja/items/5",
    )
    outfit = FakeItem(
        item_id="6",
        title="サマードレス",
        description="手描きテクスチャの衣装です。",
        category="OUTFIT",
        source_url="https://booth.pm/ja/items/6",
    )
    report = build_ai_tool_report([ai_item, outfit], generated_at="2026-08-02T00:00:00+00:00")
    assert report["metrics"]["candidate_items"] == 1
    assert report["metrics"]["candidate_shops"] == 1
    assert report["items"][0]["item_id"] == "5"
    assert report["shops"][0]["item_ids"] == ["5"]
    assert report["policy"]["shop_signal_does_not_propagate"] is True
