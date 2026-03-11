"""
tests/test_detector.py — Unit tests for SmartDetector.

Run with:  python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.detector import SmartDetector


@pytest.fixture()
def detector() -> SmartDetector:
    return SmartDetector()


# ── Contract Party Detection ─────────────────────────────────────────────────

class TestPartyDetection:

    def test_en_party_with_quotes(self, detector: SmartDetector) -> None:
        text = (
            'XYZ Trading Co., Ltd., a company incorporated under the laws of '
            'Hong Kong ("Company") and ABC Capital Limited ("Fund").'
        )
        result = detector.analyze(text)
        assert "XYZ Trading Co., Ltd." in result.parties or any("XYZ" in k for k in result.parties)
        assert any(v == "Company" for v in result.parties.values())

    def test_cn_party_with_brackets(self, detector: SmartDetector) -> None:
        text = '某某投资管理有限公司（以下简称"甲方"）与乙方签署本协议。'
        result = detector.analyze(text)
        assert any(v == "甲方" for v in result.parties.values())

    def test_party_replacement_in_replacements(self, detector: SmartDetector) -> None:
        text = 'Alpha Holdings Limited ("Alpha") agrees to purchase...'
        result = detector.analyze(text)
        repl   = detector.build_replacements(result)
        # Some form of Alpha Holdings should map to alias
        assert any("Alpha" in k for k in repl)


# ── Amount Detection ─────────────────────────────────────────────────────────

class TestAmountDetection:

    def test_usd_amount(self, detector: SmartDetector) -> None:
        text   = "The purchase price is USD 1,000,000."
        result = detector.analyze(text)
        types  = {e.entity_type for e in result.entities}
        assert "AMOUNT" in types

    def test_hkd_amount(self, detector: SmartDetector) -> None:
        text   = "HK$500,000 shall be paid within 30 days."
        result = detector.analyze(text)
        assert any(e.entity_type == "AMOUNT" for e in result.entities)

    def test_cn_amount_numeric(self, detector: SmartDetector) -> None:
        text   = "总价款为人民币500万元整。"
        result = detector.analyze(text)
        assert any(e.entity_type == "AMOUNT" for e in result.entities)

    def test_cn_amount_written(self, detector: SmartDetector) -> None:
        text   = "支付一百万元。"
        result = detector.analyze(text)
        assert any(e.entity_type == "AMOUNT" for e in result.entities)

    def test_amount_replacement_label(self, detector: SmartDetector) -> None:
        text   = "USD 250,000 million was agreed."
        result = detector.analyze(text)
        for e in result.entities:
            if e.entity_type == "AMOUNT":
                assert e.replacement in ("[AMOUNT]", "[金额]")


# ── Phone Detection ──────────────────────────────────────────────────────────

class TestPhoneDetection:

    def test_cn_mobile(self, detector: SmartDetector) -> None:
        text   = "请联系张先生：13812345678"
        result = detector.analyze(text)
        assert any(e.entity_type == "PHONE" and "13812345678" in e.text
                   for e in result.entities)

    def test_cn_landline(self, detector: SmartDetector) -> None:
        text   = "办公电话: 0755-12345678"
        result = detector.analyze(text)
        assert any(e.entity_type == "PHONE" for e in result.entities)

    def test_intl_hk(self, detector: SmartDetector) -> None:
        text   = "Contact: +852 2345 6789"
        result = detector.analyze(text)
        assert any(e.entity_type == "PHONE" for e in result.entities)


# ── Email Detection ──────────────────────────────────────────────────────────

class TestEmailDetection:

    def test_standard_email(self, detector: SmartDetector) -> None:
        text   = "Please send to john.doe@example.com for review."
        result = detector.analyze(text)
        assert any(e.entity_type == "EMAIL" and "john.doe@example.com" in e.text
                   for e in result.entities)

    def test_email_replacement(self, detector: SmartDetector) -> None:
        text   = "Reply to legal@firm.hk"
        result = detector.analyze(text)
        for e in result.entities:
            if e.entity_type == "EMAIL":
                assert e.replacement == "[EMAIL]"


# ── ID Detection ─────────────────────────────────────────────────────────────

class TestIDDetection:

    def test_cn_national_id(self, detector: SmartDetector) -> None:
        text   = "身份证号码：110101199001011234"
        result = detector.analyze(text)
        assert any(e.entity_type == "ID" and "110101199001011234" in e.text
                   for e in result.entities)

    def test_passport(self, detector: SmartDetector) -> None:
        text   = "Passport No. A12345678"
        result = detector.analyze(text)
        assert any(e.entity_type == "ID" for e in result.entities)


# ── Notice Name Detection ────────────────────────────────────────────────────

class TestNoticeNameDetection:

    def test_en_attn(self, detector: SmartDetector) -> None:
        text   = "Attention: John Smith\nFor all legal notices..."
        result = detector.analyze(text)
        assert any(e.entity_type == "NAME" and "John Smith" in e.text
                   for e in result.entities)

    def test_cn_contact(self, detector: SmartDetector) -> None:
        text   = "联系人：张伟\n地址：..."
        result = detector.analyze(text)
        assert any(e.entity_type == "NAME" and "张伟" in e.text
                   for e in result.entities)


# ── Build Replacements ───────────────────────────────────────────────────────

class TestBuildReplacements:

    def test_party_priority_over_company(self, detector: SmartDetector) -> None:
        """Party aliases must not be overridden by the 'other company' detector."""
        text   = 'Alpha Capital Limited ("Alpha") is the manager.'
        result = detector.analyze(text)
        repl   = detector.build_replacements(result)
        # The alias "Alpha" should appear in values, not be replaced by [COMPANY NAME]
        assert "Alpha" in repl.values() or any("Alpha" in k for k in repl)

    def test_no_empty_replacements(self, detector: SmartDetector) -> None:
        text   = "No entities here - just plain text."
        result = detector.analyze(text)
        repl   = detector.build_replacements(result)
        for k, v in repl.items():
            assert k and v, f"Empty key or value: {k!r} → {v!r}"
