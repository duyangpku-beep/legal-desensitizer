"""
core/detector.py — SmartDetector

100% offline, regex-only entity detection for Chinese + English legal documents.
Detects: contract parties, amounts, person names, company names, phone, email, ID, address.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Detection result types
# ─────────────────────────────────────────────────────────────────────────────

class EntityMatch(NamedTuple):
    text: str           # original matched text
    entity_type: str    # e.g. "PHONE", "AMOUNT", "PARTY"
    replacement: str    # what to replace it with


@dataclass
class DetectionResult:
    """Aggregated detection output for one document text."""
    parties: dict[str, str] = field(default_factory=dict)   # full_name → alias
    entities: list[EntityMatch] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Compiled regex patterns
# ─────────────────────────────────────────────────────────────────────────────

# --- Contract parties ---
PARTY_EN = re.compile(
    # Group 1: company full name — must start uppercase; exclude '(' so it can't
    # span into a later alias clause like '("Company")'
    r'([A-Z][^(\n]+?(?:Co\.?,?\s*Ltd\.?|Limited|Inc\.?|Corp\.?|LLC|LLP|'
    r'Company|Corporation|Enterprise|Fund|Partnership|Trust)[^()\n]*?)'
    # Optional descriptor clause before the alias, e.g. ", a company incorporated in ..."
    r'\s*[,(]\s*(?:[^,()\n]*?[Cc]ompany[^,()\n]*?,\s*)?'
    # Alias in quotes — group 2, uppercase first letter
    r'["\u201c]\s*([A-Z][A-Za-z\s]{1,30})\s*["\u201d]\s*\)',
    # No IGNORECASE: [A-Z] stays strictly uppercase so "a company..." won't match
)

PARTY_CN = re.compile(
    r'([^\s，,。；\n]{2,40}?'
    r'(?:有限公司|股份有限公司|集团有限公司|控股有限公司|合伙企业|'
    r'基金管理公司|投资管理公司|科技有限公司|贸易有限公司|公司))'
    r'[^（(]{0,30}[（("]'
    r'\s*(?:以下简称\s*)?["""]\s*([^\s"""]{1,10})\s*["""]\s*[）)]',
    re.UNICODE,
)

# --- Amounts ---
AMOUNT_EN = re.compile(
    r'(?:USD|US\$|\$|EUR|€|GBP|£|HKD|HK\$|SGD|S\$|JPY|¥|RMB|CNY)\s*'
    r'[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand|mn|bn)?',
    re.IGNORECASE,
)

AMOUNT_CN = re.compile(
    r'(?:人民币|港币|港元|美元|欧元|英镑|日元)?'
    r'[\d,]+(?:\.\d+)?\s*(?:元|万元|百万元|亿元|万|亿)(?:整|正)?',
    re.UNICODE,
)

AMOUNT_CN_WRITTEN = re.compile(
    r'[零一二三四五六七八九十百千万亿]+(?:元|万元|亿元|美元|港元)',
    re.UNICODE,
)

# --- Phone numbers ---
PHONE_CN_MOBILE = re.compile(r'1[3-9]\d{9}')
PHONE_CN_DASH   = re.compile(r'1[3-9]\d-\d{4}-\d{4}')
PHONE_CN_LAND   = re.compile(r'0\d{2,3}[-\s]?\d{7,8}(?:[-\s]?\d{1,4})?')
PHONE_INTL      = re.compile(r'(?:\+\d{1,3}[-\s]?)?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}')

# --- Email ---
EMAIL = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# --- ID numbers ---
ID_CN    = re.compile(
    r'[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]'
)
PASSPORT = re.compile(r'[A-Z]\d{8}|[A-Z]{2}\d{7}')

# --- Addresses ---
ADDR_CN = re.compile(
    r'(?:(?:中国\s*)?(?:[^\s，。]{2,4}省|[^\s，。]{2,3}市|北京|上海|广州|深圳|香港|澳门))'
    r'[^\s，。]{2,50}?(?:路|街|道|大道|大街|里|巷|弄|号|楼|室|单元|区|园|广场)',
    re.UNICODE,
)
ADDR_EN = re.compile(
    r'\d+[,\s]+[A-Z][A-Za-z\s]+(?:Road|Street|Avenue|Ave|Lane|Drive|Dr|Way|'
    r'Place|Pl|Boulevard|Blvd)[,\s]+[A-Za-z\s,]+',
    re.IGNORECASE,
)

# --- Person names from Notices clauses ---
NOTICE_NAME_EN = re.compile(
    r'(?:Attention|Attn|To|For the attention of)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
    re.IGNORECASE,
)
NOTICE_NAME_CN = re.compile(
    r'(?:收件人|联系人|联系|致)\s*[：:]\s*([\u4e00-\u9fff]{2,4})',
    re.UNICODE,
)

# --- Other company names (non-party) ---
OTHER_CO_EN = re.compile(
    r'\b([A-Z][A-Za-z\s&]{2,40}?'
    r'(?:Co\.?,?\s*Ltd\.?|Limited|Inc\.?|Corp\.?|LLC|LLP|Company|Corporation))\b'
)
OTHER_CO_CN = re.compile(
    r'([^\s，,。；\n（(]{2,20}?(?:有限公司|股份公司|集团|基金|合伙企业))',
    re.UNICODE,
)


# ─────────────────────────────────────────────────────────────────────────────
# SmartDetector
# ─────────────────────────────────────────────────────────────────────────────

class SmartDetector:
    """
    Stateless entity detector for legal documents.

    Usage::

        detector = SmartDetector(options)
        result   = detector.analyze(full_document_text)
        # result.parties  → {full_name: alias}
        # result.entities → [EntityMatch(...), ...]
    """

    def __init__(
        self,
        detect_parties: bool = True,
        detect_amounts: bool = True,
        detect_phones: bool = True,
        detect_emails: bool = True,
        detect_ids: bool = True,
        detect_addresses: bool = True,
        detect_names: bool = True,
        detect_other_companies: bool = True,
        language: str = "auto",  # "auto" | "en" | "cn"
    ) -> None:
        self.detect_parties          = detect_parties
        self.detect_amounts          = detect_amounts
        self.detect_phones           = detect_phones
        self.detect_emails           = detect_emails
        self.detect_ids              = detect_ids
        self.detect_addresses        = detect_addresses
        self.detect_names            = detect_names
        self.detect_other_companies  = detect_other_companies
        self.language                = language

    # ── public API ──────────────────────────────────────────────────────────

    def analyze(self, text: str) -> DetectionResult:
        """
        Scan *text* (full document plain text) and return a DetectionResult.

        All matches are de-duplicated; longer matches take priority over
        shorter ones that overlap.
        """
        result = DetectionResult()

        if self.detect_parties:
            result.parties = self._detect_parties(text)

        # Build known-party-alias set so we skip them when detecting "other companies"
        known_aliases: set[str] = set(result.parties.values())
        known_full:   set[str] = set(result.parties.keys())

        entities: list[EntityMatch] = []

        if self.detect_phones:
            entities.extend(self._detect_phones(text))
        if self.detect_emails:
            entities.extend(self._detect_emails(text))
        if self.detect_ids:
            entities.extend(self._detect_ids(text))
        if self.detect_addresses:
            entities.extend(self._detect_addresses(text))
        if self.detect_names:
            entities.extend(self._detect_names(text))
        if self.detect_amounts:
            entities.extend(self._detect_amounts(text))
        if self.detect_other_companies:
            entities.extend(self._detect_other_companies(text, known_full, known_aliases))

        result.entities = self._deduplicate(entities)
        return result

    def build_replacements(self, result: DetectionResult) -> dict[str, str]:
        """
        Merge parties + entities into a single replacement map, priority-ordered:
        parties → PII → amounts → companies.
        """
        replacements: dict[str, str] = {}

        # 1. Parties (full name → alias)
        replacements.update(result.parties)

        # 2. PII first (phones, email, ID, address, names)
        pii_types = {"PHONE", "EMAIL", "ID", "ADDRESS", "NAME"}
        for em in result.entities:
            if em.entity_type in pii_types and em.text not in replacements:
                replacements[em.text] = em.replacement

        # 3. Amounts
        for em in result.entities:
            if em.entity_type == "AMOUNT" and em.text not in replacements:
                replacements[em.text] = em.replacement

        # 4. Other companies
        for em in result.entities:
            if em.entity_type == "COMPANY" and em.text not in replacements:
                replacements[em.text] = em.replacement

        return replacements

    # ── private helpers ─────────────────────────────────────────────────────

    def _detect_parties(self, text: str) -> dict[str, str]:
        parties: dict[str, str] = {}
        for m in PARTY_EN.finditer(text):
            full, alias = m.group(1).strip(), m.group(2).strip()
            parties[full] = alias
        for m in PARTY_CN.finditer(text):
            full, alias = m.group(1).strip(), m.group(2).strip()
            parties[full] = alias
        return parties

    def _detect_amounts(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        for m in AMOUNT_EN.finditer(text):
            matches.append(EntityMatch(m.group(), "AMOUNT", "[AMOUNT]"))
        for m in AMOUNT_CN.finditer(text):
            matches.append(EntityMatch(m.group(), "AMOUNT", "[金额]"))
        for m in AMOUNT_CN_WRITTEN.finditer(text):
            matches.append(EntityMatch(m.group(), "AMOUNT", "[金额]"))
        return matches

    def _detect_phones(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        seen: set[str] = set()
        patterns = [PHONE_CN_MOBILE, PHONE_CN_DASH, PHONE_CN_LAND, PHONE_INTL]
        for pat in patterns:
            for m in pat.finditer(text):
                t = m.group()
                if t not in seen and len(t) >= 7:
                    seen.add(t)
                    replacement = "[电话]" if any('\u4e00' <= c <= '\u9fff' for c in text[max(0, m.start()-10):m.start()]) else "[PHONE]"
                    matches.append(EntityMatch(t, "PHONE", replacement))
        return matches

    def _detect_emails(self, text: str) -> list[EntityMatch]:
        return [EntityMatch(m.group(), "EMAIL", "[EMAIL]") for m in EMAIL.finditer(text)]

    def _detect_ids(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        for m in ID_CN.finditer(text):
            matches.append(EntityMatch(m.group(), "ID", "[证件号码]"))
        for m in PASSPORT.finditer(text):
            matches.append(EntityMatch(m.group(), "ID", "[ID NUMBER]"))
        return matches

    def _detect_addresses(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        for m in ADDR_CN.finditer(text):
            matches.append(EntityMatch(m.group(), "ADDRESS", "[地址]"))
        for m in ADDR_EN.finditer(text):
            matches.append(EntityMatch(m.group(), "ADDRESS", "[ADDRESS]"))
        return matches

    def _detect_names(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        seen: set[str] = set()
        for m in NOTICE_NAME_EN.finditer(text):
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                matches.append(EntityMatch(name, "NAME", "[NAME]"))
        for m in NOTICE_NAME_CN.finditer(text):
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                matches.append(EntityMatch(name, "NAME", "[姓名]"))
        return matches

    def _detect_other_companies(
        self,
        text: str,
        known_full: set[str],
        known_aliases: set[str],
    ) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        seen: set[str] = set()
        for m in OTHER_CO_EN.finditer(text):
            name = m.group(1).strip()
            if name not in seen and name not in known_full and name not in known_aliases:
                seen.add(name)
                matches.append(EntityMatch(name, "COMPANY", "[COMPANY NAME]"))
        for m in OTHER_CO_CN.finditer(text):
            name = m.group(1).strip()
            if name not in seen and name not in known_full and name not in known_aliases:
                seen.add(name)
                matches.append(EntityMatch(name, "COMPANY", "[公司名称]"))
        return matches

    @staticmethod
    def _deduplicate(entities: list[EntityMatch]) -> list[EntityMatch]:
        """Remove exact-text duplicates; keep first occurrence."""
        seen: set[str] = set()
        out: list[EntityMatch] = []
        for em in entities:
            if em.text not in seen:
                seen.add(em.text)
                out.append(em)
        return out
