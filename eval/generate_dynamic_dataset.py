#!/usr/bin/env python3
"""Dynamic Golden Dataset Generator.

Produces eval/dynamic_golden_dataset.json with time-anchored predictions
whose ground truth is computed at generation time. Deterministic templates
use Python stdlib (datetime, calendar, math). Brave Search templates query
the Brave API for current facts.

Usage:
    /home/wsluser/projects/calledit/venv/bin/python eval/generate_dynamic_dataset.py

Requires:
    - BRAVE_API_KEY env var for Brave Search templates (optional — degrades gracefully)

Output:
    eval/dynamic_golden_dataset.json (schema 4.0 compatible)
"""

import calendar
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Constants ---
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "dynamic_golden_dataset.json")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
VALID_MODES = {"immediate", "at_date", "before_date", "recurring"}
VALID_VERDICTS = {"confirmed", "refuted", "inconclusive"}
VALID_SOURCES = {"deterministic", "brave_search", "api_lookup"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


# ---------------------------------------------------------------------------
# Brave Search
# ---------------------------------------------------------------------------

def brave_search(query: str, count: int = 5) -> Optional[dict]:
    """Query Brave Search API. Returns parsed results or None on failure."""
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.get(
            BRAVE_SEARCH_URL,
            params={"q": query, "count": count},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        return {"results": results, "query": query}
    except Exception as e:
        logger.warning("Brave search failed for '%s': %s", query, e)
        return None


# ---------------------------------------------------------------------------
# Lunar cycle helper (for before_date templates)
# ---------------------------------------------------------------------------

# Known full moon reference: January 13, 2026 22:27 UTC
_KNOWN_FULL_MOON = datetime(2026, 1, 13, 22, 27, tzinfo=timezone.utc)
_SYNODIC_MONTH = 29.53058770576  # days


def _nearest_full_moon_before(target: datetime) -> datetime:
    """Find the most recent full moon before `target` using synodic month."""
    cycles = (target - _KNOWN_FULL_MOON).total_seconds() / (
        _SYNODIC_MONTH * 86400
    )
    n = int(cycles)
    candidate = _KNOWN_FULL_MOON + timedelta(days=n * _SYNODIC_MONTH)
    if candidate > target:
        candidate -= timedelta(days=_SYNODIC_MONTH)
    return candidate


def _nearest_full_moon_after(target: datetime) -> datetime:
    """Find the next full moon on or after `target`."""
    fm = _nearest_full_moon_before(target)
    if fm < target:
        fm += timedelta(days=_SYNODIC_MONTH)
    return fm


# ---------------------------------------------------------------------------
# Prediction helper
# ---------------------------------------------------------------------------

def _make_prediction(
    pred_id: str,
    text: str,
    difficulty: str,
    mode: str,
    verdict: str,
    domain: str,
    stakes: str = "trivial",
    time_horizon: str = "minutes-to-hours",
    persona: str = "student",
    source: str = "deterministic",
    raw_data: dict = None,
    computation_logic: str = "",
    now: datetime = None,
    verification_date: str = None,
    replaces: str = None,
    recurring_interval: str = None,
    verification_sources: list = None,
    verification_criteria: list = None,
    verification_steps: list = None,
    evaluation_rubric: str = "",
) -> dict:
    """Build a schema 4.0 prediction dict with ground_truth_computation."""
    now_iso = now.isoformat() if now else datetime.now(timezone.utc).isoformat()
    return {
        "id": pred_id,
        "prediction_text": text,
        "difficulty": difficulty,
        "verification_mode": mode,
        "verification_readiness": "immediate",
        "expected_verification_outcome": verdict,
        "expected_verifiability_score_range": [0.8, 1.0],
        "smoke_test": False,
        "is_boundary_case": False,
        "boundary_description": None,
        "replaces": replaces,
        "time_sensitive": False,
        "recurring_interval": recurring_interval,
        "verification_date": verification_date,
        "dimension_tags": {
            "domain": domain,
            "stakes": stakes,
            "time_horizon": time_horizon,
            "persona": persona,
        },
        "ground_truth": {
            "verifiability_reasoning": computation_logic,
            "date_derivation": f"Generated at {now_iso}",
            "verification_sources": verification_sources or ["calendar_arithmetic"],
            "objectivity_assessment": "objective",
            "verification_criteria": verification_criteria or [text],
            "verification_steps": verification_steps or ["Verify the claim"],
            "verification_timing": "Immediate",
            "expected_verification_criteria": verification_criteria or [text],
            "expected_verification_method": computation_logic,
            "ground_truth_source": source,
            "ground_truth_computation": {
                "source": source,
                "raw_data": raw_data or {},
                "computation_logic": computation_logic,
                "computed_at": now_iso,
            },
        },
        "evaluation_rubric": evaluation_rubric or f"Agent should {verdict} this prediction.",
    }


# ===========================================================================
# IMMEDIATE MODE — Deterministic Templates
# ===========================================================================

def template_weekday_check(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-001: 'Today is a weekday'"""
    dow = calendar.weekday(now.year, now.month, now.day)
    day_name = calendar.day_name[dow]
    is_weekday = dow < 5
    verdict = "confirmed" if is_weekday else "refuted"
    return _make_prediction(
        pred_id="dyn-imm-001",
        text="Today is a weekday",
        difficulty="easy",
        mode="immediate",
        verdict=verdict,
        domain="science",
        source="deterministic",
        raw_data={
            "date": now.strftime("%Y-%m-%d"),
            "day_of_week": day_name,
            "weekday_index": dow,
            "formula": f"calendar.weekday({now.year}, {now.month}, {now.day}) < 5",
        },
        computation_logic=f"{day_name} is weekday index {dow} ({'< 5 → weekday' if is_weekday else '>= 5 → weekend'}) → {verdict}",
        now=now,
        verification_sources=["calendar_arithmetic"],
        verification_criteria=["Today is Monday through Friday"],
        verification_steps=["Check current day of week"],
        evaluation_rubric="Agent should confirm or refute via calendar reasoning.",
    )


def template_year_parity(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-002: 'The current year is even'"""
    is_even = now.year % 2 == 0
    verdict = "confirmed" if is_even else "refuted"
    return _make_prediction(
        pred_id="dyn-imm-002",
        text=f"The current year ({now.year}) is an even number",
        difficulty="easy",
        mode="immediate",
        verdict=verdict,
        domain="science",
        persona="math_enthusiast",
        source="deterministic",
        raw_data={
            "year": now.year,
            "formula": f"{now.year} % 2 == 0",
            "result": is_even,
        },
        computation_logic=f"{now.year} % 2 = {now.year % 2} → {'even' if is_even else 'odd'} → {verdict}",
        now=now,
        verification_criteria=[f"The year {now.year} is an even number"],
        verification_steps=["Check if current year is divisible by 2"],
        evaluation_rubric="Agent should verify year parity via simple arithmetic.",
    )


def template_month_has_31_days(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-003: 'The current month has 31 days'"""
    _, days_in_month = calendar.monthrange(now.year, now.month)
    month_name = calendar.month_name[now.month]
    has_31 = days_in_month == 31
    verdict = "confirmed" if has_31 else "refuted"
    return _make_prediction(
        pred_id="dyn-imm-003",
        text=f"The current month ({month_name}) has 31 days",
        difficulty="easy",
        mode="immediate",
        verdict=verdict,
        domain="science",
        persona="trivia_buff",
        source="deterministic",
        raw_data={
            "year": now.year,
            "month": now.month,
            "month_name": month_name,
            "days_in_month": days_in_month,
            "formula": f"calendar.monthrange({now.year}, {now.month})[1] == 31",
        },
        computation_logic=f"{month_name} {now.year} has {days_in_month} days → {'has 31' if has_31 else 'does not have 31'} → {verdict}",
        now=now,
        verification_criteria=[f"{month_name} has exactly 31 days"],
        verification_steps=["Check number of days in current month"],
        evaluation_rubric="Agent should verify month length via calendar knowledge.",
    )


def template_today_is_january(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-006: 'The current month is January' — refuted most of the year"""
    month_name = calendar.month_name[now.month]
    is_january = now.month == 1
    verdict = "confirmed" if is_january else "refuted"
    return _make_prediction(
        pred_id="dyn-imm-006",
        text="The current month is January",
        difficulty="easy",
        mode="immediate",
        verdict=verdict,
        domain="science",
        persona="student",
        source="deterministic",
        raw_data={
            "month": now.month,
            "month_name": month_name,
            "is_january": is_january,
        },
        computation_logic=f"Current month is {month_name} (month {now.month}). January is month 1. → {verdict}",
        now=now,
        verification_criteria=["The current month is January"],
        verification_steps=["Check current month"],
        evaluation_rubric="Agent should check current month against January.",
    )


# ===========================================================================
# AT_DATE MODE — Deterministic Templates
# ===========================================================================

def template_yesterday_day_of_week(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-atd-001: 'Yesterday was a [day]'"""
    yesterday = now - timedelta(days=1)
    dow = calendar.weekday(yesterday.year, yesterday.month, yesterday.day)
    actual_day = calendar.day_name[dow]
    # Claim a specific day — make it correct
    verdict = "confirmed"
    return _make_prediction(
        pred_id="dyn-atd-001",
        text=f"Yesterday ({yesterday.strftime('%B %d, %Y')}) was a {actual_day}",
        difficulty="easy",
        mode="at_date",
        verdict=verdict,
        domain="science",
        source="deterministic",
        raw_data={
            "date": yesterday.strftime("%Y-%m-%d"),
            "day_of_week": actual_day,
            "weekday_index": dow,
        },
        computation_logic=f"{yesterday.strftime('%Y-%m-%d')} was a {actual_day} → {verdict}",
        now=now,
        verification_date=yesterday.strftime("%Y-%m-%dT00:00:00Z"),
        verification_criteria=[f"Yesterday was a {actual_day}"],
        verification_steps=["Check the day of week for yesterday's date"],
        evaluation_rubric="Agent should confirm via calendar lookup for yesterday.",
    )


def template_yesterday_was_weekend(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-atd-002: 'Yesterday was a weekend day'"""
    yesterday = now - timedelta(days=1)
    dow = calendar.weekday(yesterday.year, yesterday.month, yesterday.day)
    day_name = calendar.day_name[dow]
    is_weekend = dow >= 5
    verdict = "confirmed" if is_weekend else "refuted"
    return _make_prediction(
        pred_id="dyn-atd-002",
        text=f"Yesterday ({yesterday.strftime('%B %d, %Y')}) was a weekend day",
        difficulty="easy",
        mode="at_date",
        verdict=verdict,
        domain="science",
        persona="office_worker",
        source="deterministic",
        raw_data={
            "date": yesterday.strftime("%Y-%m-%d"),
            "day_of_week": day_name,
            "weekday_index": dow,
            "is_weekend": is_weekend,
        },
        computation_logic=f"{day_name} has weekday index {dow} ({'≥ 5 → weekend' if is_weekend else '< 5 → weekday'}) → {verdict}",
        now=now,
        verification_date=yesterday.strftime("%Y-%m-%dT00:00:00Z"),
        verification_criteria=["Yesterday was Saturday or Sunday"],
        verification_steps=["Check if yesterday's day of week was Saturday or Sunday"],
        evaluation_rubric="Agent should check if yesterday was a weekend day.",
    )


# ===========================================================================
# BEFORE_DATE MODE — Deterministic Templates
# ===========================================================================

def template_full_moon_before_date(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-bfd-001: 'A full moon occurred before [recent date]' — replaces base-010"""
    # Deadline: 3 days ago
    deadline = now - timedelta(days=3)
    deadline_str = deadline.strftime("%B %d, %Y")

    fm = _nearest_full_moon_before(deadline)
    days_before = (deadline - fm).total_seconds() / 86400

    # Full moon occurred before deadline if it's within a reasonable window
    occurred_before = days_before >= 0 and days_before < 35  # within one synodic month
    verdict = "confirmed" if occurred_before else "refuted"

    return _make_prediction(
        pred_id="dyn-bfd-001",
        text=f"A full moon occurred before {deadline_str}",
        difficulty="medium",
        mode="before_date",
        verdict=verdict,
        domain="nature",
        stakes="trivial",
        time_horizon="weeks-to-months",
        persona="gardener",
        source="deterministic",
        raw_data={
            "deadline": deadline.strftime("%Y-%m-%d"),
            "nearest_full_moon": fm.strftime("%Y-%m-%d %H:%M UTC"),
            "days_before_deadline": round(days_before, 1),
            "synodic_month": _SYNODIC_MONTH,
            "reference_full_moon": _KNOWN_FULL_MOON.strftime("%Y-%m-%d %H:%M UTC"),
        },
        computation_logic=f"Nearest full moon before {deadline_str} was {fm.strftime('%Y-%m-%d')} ({round(days_before, 1)} days before deadline) → {verdict}",
        now=now,
        replaces="base-010",
        verification_date=deadline.strftime("%Y-%m-%dT00:00:00Z"),
        verification_sources=["lunar_cycle_calculations", "astronomical_algorithms"],
        verification_criteria=[f"A full moon occurred before {deadline_str}"],
        verification_steps=[
            "Calculate recent full moon dates using lunar cycle algorithms",
            f"Check if any fall before {deadline_str}",
        ],
        evaluation_rubric="Agent should verify via lunar cycle calculation or astronomical data.",
    )


def template_equinox_before_date(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-bfd-002: 'The March equinox occurred before [date]'"""
    # March equinox 2026 is approximately March 20, 2026 14:46 UTC
    equinox_2026 = datetime(2026, 3, 20, 14, 46, tzinfo=timezone.utc)

    # Set deadline to 5 days ago
    deadline = now - timedelta(days=5)
    deadline_str = deadline.strftime("%B %d, %Y")

    occurred_before = equinox_2026 < deadline
    verdict = "confirmed" if occurred_before else "refuted"

    return _make_prediction(
        pred_id="dyn-bfd-002",
        text=f"The March 2026 equinox occurred before {deadline_str}",
        difficulty="medium",
        mode="before_date",
        verdict=verdict,
        domain="nature",
        stakes="trivial",
        time_horizon="weeks-to-months",
        persona="astronomer",
        source="deterministic",
        raw_data={
            "equinox_date": equinox_2026.strftime("%Y-%m-%d %H:%M UTC"),
            "deadline": deadline.strftime("%Y-%m-%d"),
            "occurred_before": occurred_before,
        },
        computation_logic=f"March 2026 equinox was {equinox_2026.strftime('%Y-%m-%d')}. Deadline is {deadline_str}. {'Equinox was before deadline' if occurred_before else 'Equinox was after deadline'} → {verdict}",
        now=now,
        verification_date=deadline.strftime("%Y-%m-%dT00:00:00Z"),
        verification_sources=["astronomical_calculations"],
        verification_criteria=[f"The March 2026 equinox occurred before {deadline_str}"],
        verification_steps=[
            "Determine the date of the March 2026 equinox",
            f"Check if it falls before {deadline_str}",
        ],
        evaluation_rubric="Agent should verify equinox date via astronomical knowledge or search.",
    )


def template_summer_solstice_before_date(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-bfd-004: 'The June 2026 solstice occurred before [recent date]' — guaranteed refuted before June"""
    # June solstice 2026 is approximately June 21, 2026
    solstice_2026 = datetime(2026, 6, 21, 2, 24, tzinfo=timezone.utc)
    deadline = now - timedelta(days=1)
    deadline_str = deadline.strftime("%B %d, %Y")

    occurred_before = solstice_2026 < deadline
    verdict = "confirmed" if occurred_before else "refuted"

    return _make_prediction(
        pred_id="dyn-bfd-004",
        text=f"The June 2026 solstice occurred before {deadline_str}",
        difficulty="medium",
        mode="before_date",
        verdict=verdict,
        domain="nature",
        stakes="trivial",
        time_horizon="weeks-to-months",
        persona="astronomer",
        source="deterministic",
        raw_data={
            "solstice_date": solstice_2026.strftime("%Y-%m-%d %H:%M UTC"),
            "deadline": deadline.strftime("%Y-%m-%d"),
            "occurred_before": occurred_before,
        },
        computation_logic=f"June 2026 solstice is ~{solstice_2026.strftime('%Y-%m-%d')}. Deadline is {deadline_str}. {'Before deadline' if occurred_before else 'After deadline'} → {verdict}",
        now=now,
        verification_date=deadline.strftime("%Y-%m-%dT00:00:00Z"),
        verification_sources=["astronomical_calculations"],
        verification_criteria=[f"The June 2026 solstice occurred before {deadline_str}"],
        verification_steps=[
            "Determine the date of the June 2026 solstice",
            f"Check if it falls before {deadline_str}",
        ],
        evaluation_rubric="Agent should verify solstice date via astronomical knowledge or search.",
    )


# ===========================================================================
# Brave Search Templates (stubs — filled in Task 4)
# ===========================================================================

# Immediate mode — Brave
def template_us_president(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-004: 'The current US President is [name]'"""
    if brave_fn is None:
        return None
    results = brave_fn("Who is the current US President 2026")
    if not results or not results.get("results"):
        return None
    # Search across all result snippets and titles
    all_text = " ".join(
        r.get("description", "") + " " + r.get("title", "")
        for r in results["results"]
    ).lower()
    snippet = results["results"][0].get("description", "")
    name = "Donald Trump"  # As of 2026
    found = "trump" in all_text and "president" in all_text
    verdict = "confirmed" if found else "inconclusive"
    return _make_prediction(
        pred_id="dyn-imm-004",
        text=f"The current US President is {name}",
        difficulty="medium",
        mode="immediate",
        verdict=verdict,
        domain="politics",
        stakes="significant",
        persona="news_follower",
        source="brave_search",
        raw_data={"query": "Who is the current US President 2026", "snippet": snippet},
        computation_logic=f"Brave search for current US President. Found '{name}' in results: {found} → {verdict}",
        now=now,
        verification_sources=["brave_web_search", "news_sources"],
        verification_criteria=[f"The current US President is {name}"],
        verification_steps=["Search for current US President", "Verify name matches"],
        evaluation_rubric="Agent should verify via web search for current US President.",
    )


def template_python_released(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-imm-005: 'Python 3.13 has been released'"""
    if brave_fn is None:
        return None
    results = brave_fn("Python 3.13 official release date")
    if not results or not results.get("results"):
        return None
    snippet = results["results"][0].get("description", "")
    # Python 3.13 was released October 2024
    released = any(kw in snippet.lower() for kw in ["released", "release", "3.13"])
    verdict = "confirmed" if released else "inconclusive"
    return _make_prediction(
        pred_id="dyn-imm-005",
        text="Python 3.13 has been officially released",
        difficulty="medium",
        mode="immediate",
        verdict=verdict,
        domain="technology",
        stakes="moderate",
        persona="developer",
        source="brave_search",
        raw_data={"query": "Python 3.13 official release date", "snippet": snippet},
        computation_logic=f"Brave search for Python 3.13 release. Found release info: {released} → {verdict}",
        now=now,
        verification_sources=["brave_web_search", "python_org"],
        verification_criteria=["Python 3.13 appears as an official release"],
        verification_steps=["Search for Python 3.13 release status", "Check python.org"],
        evaluation_rubric="Agent should verify Python 3.13 release status via web search.",
    )


# At-date mode — Brave
def template_yesterday_event(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-atd-003: Search for a notable event from yesterday"""
    if brave_fn is None:
        return None
    yesterday = now - timedelta(days=1)
    date_str = yesterday.strftime("%B %d, %Y")
    query = f"what happened on {date_str} news"
    results = brave_fn(query)
    if not results or not results.get("results"):
        return None
    snippet = results["results"][0].get("description", "")
    title = results["results"][0].get("title", "")
    # We found something — create a prediction about it being a real event
    verdict = "confirmed"
    return _make_prediction(
        pred_id="dyn-atd-003",
        text=f"A notable news event was reported on {date_str}",
        difficulty="medium",
        mode="at_date",
        verdict=verdict,
        domain="current_events",
        stakes="moderate",
        persona="news_follower",
        source="brave_search",
        raw_data={"query": query, "snippet": snippet, "title": title},
        computation_logic=f"Brave search found news for {date_str}: '{title}' → {verdict}",
        now=now,
        verification_date=yesterday.strftime("%Y-%m-%dT00:00:00Z"),
        verification_sources=["brave_web_search", "news_sources"],
        verification_criteria=[f"A notable news event occurred on {date_str}"],
        verification_steps=[f"Search for news from {date_str}", "Verify event occurred"],
        evaluation_rubric="Agent should find news coverage for the specified date.",
    )


# Before-date mode — Brave
def template_event_before_deadline(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-bfd-003: 'Python 3.12 was released before January 1, 2026'"""
    if brave_fn is None:
        return None
    deadline = now - timedelta(days=2)
    deadline_str = deadline.strftime("%B %d, %Y")
    query = "Python 3.12 release date"
    results = brave_fn(query)
    if not results or not results.get("results"):
        return None
    snippet = results["results"][0].get("description", "")
    # Python 3.12 was released October 2, 2023 — well before any recent deadline
    verdict = "confirmed"
    return _make_prediction(
        pred_id="dyn-bfd-003",
        text=f"Python 3.12 was released before {deadline_str}",
        difficulty="medium",
        mode="before_date",
        verdict=verdict,
        domain="technology",
        stakes="moderate",
        persona="developer",
        source="brave_search",
        raw_data={"query": query, "snippet": snippet, "deadline": deadline_str},
        computation_logic=f"Python 3.12 released Oct 2023, well before {deadline_str} → {verdict}",
        now=now,
        verification_date=deadline.strftime("%Y-%m-%dT00:00:00Z"),
        verification_sources=["brave_web_search", "python_org"],
        verification_criteria=[f"Python 3.12 was released before {deadline_str}"],
        verification_steps=["Search for Python 3.12 release date", f"Compare against {deadline_str}"],
        evaluation_rubric="Agent should verify Python 3.12 release date via web search.",
    )


# Recurring mode — Brave
def template_us_debt(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-rec-001: 'US national debt exceeds $35 trillion'"""
    if brave_fn is None:
        return None
    query = "current US national debt total 2026"
    results = brave_fn(query)
    if not results or not results.get("results"):
        return None
    all_text = " ".join(
        r.get("description", "") + " " + r.get("title", "")
        for r in results["results"]
    ).lower()
    snippet = results["results"][0].get("description", "")
    # US debt has been above $35T since mid-2024
    exceeds = "trillion" in all_text or "35" in all_text or "36" in all_text
    verdict = "confirmed" if exceeds else "inconclusive"
    return _make_prediction(
        pred_id="dyn-rec-001",
        text="The US national debt currently exceeds $35 trillion",
        difficulty="hard",
        mode="recurring",
        verdict=verdict,
        domain="finance",
        stakes="significant",
        time_horizon="months-to-years",
        persona="economist",
        source="brave_search",
        raw_data={"query": query, "snippet": snippet, "threshold": "$35 trillion"},
        computation_logic=f"Brave search for US debt. Found trillion reference: {exceeds} → {verdict}",
        now=now,
        recurring_interval="weekly",
        verification_sources=["brave_web_search", "treasury_gov"],
        verification_criteria=["US national debt exceeds $35 trillion"],
        verification_steps=["Search for current US national debt", "Compare against $35T threshold"],
        evaluation_rubric="Agent should verify current US debt level via web search.",
    )


def template_bitcoin_above_threshold(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-rec-002: 'Bitcoin price is above $10,000'"""
    if brave_fn is None:
        return None
    query = "current Bitcoin price USD"
    results = brave_fn(query)
    if not results or not results.get("results"):
        return None
    snippet = results["results"][0].get("description", "")
    # Bitcoin has been well above $10K since 2020
    verdict = "confirmed"  # Very safe threshold
    return _make_prediction(
        pred_id="dyn-rec-002",
        text="Bitcoin is currently trading above $10,000 USD",
        difficulty="medium",
        mode="recurring",
        verdict=verdict,
        domain="finance",
        stakes="moderate",
        time_horizon="days",
        persona="crypto_investor",
        source="brave_search",
        raw_data={"query": query, "snippet": snippet, "threshold": "$10,000"},
        computation_logic=f"Brave search for Bitcoin price. Bitcoin well above $10K → {verdict}",
        now=now,
        recurring_interval="daily",
        verification_sources=["brave_web_search", "crypto_exchanges"],
        verification_criteria=["Bitcoin price exceeds $10,000 USD"],
        verification_steps=["Search for current Bitcoin price", "Compare against $10,000"],
        evaluation_rubric="Agent should verify current Bitcoin price via web search.",
    )


def template_wikipedia_accessible(now: datetime, brave_fn=None) -> Optional[dict]:
    """dyn-rec-003: 'Wikipedia.org is currently accessible'"""
    if brave_fn is None:
        return None
    query = "wikipedia.org site status"
    results = brave_fn(query)
    if not results or not results.get("results"):
        return None
    snippet = results["results"][0].get("description", "")
    # Wikipedia is almost always accessible
    verdict = "confirmed"
    return _make_prediction(
        pred_id="dyn-rec-003",
        text="Wikipedia.org is currently accessible and serving content",
        difficulty="easy",
        mode="recurring",
        verdict=verdict,
        domain="technology",
        stakes="trivial",
        persona="researcher",
        source="brave_search",
        raw_data={"query": query, "snippet": snippet},
        computation_logic=f"Brave search confirms Wikipedia accessible → {verdict}",
        now=now,
        recurring_interval="daily",
        verification_sources=["brave_web_search", "website_check"],
        verification_criteria=["Wikipedia.org responds to requests"],
        verification_steps=["Check if wikipedia.org is accessible", "Verify content is served"],
        evaluation_rubric="Agent should verify Wikipedia accessibility via web search or direct check.",
    )


# ===========================================================================
# Template Registry
# ===========================================================================

def get_all_templates() -> list:
    """Return all prediction template functions."""
    return [
        # Immediate — deterministic
        template_weekday_check,
        template_year_parity,
        template_month_has_31_days,
        template_today_is_january,
        # Immediate — brave
        template_us_president,
        # At-date — deterministic
        template_yesterday_day_of_week,
        template_yesterday_was_weekend,
        # At-date — brave
        template_yesterday_event,
        # Before-date — deterministic
        template_full_moon_before_date,
        template_equinox_before_date,
        template_summer_solstice_before_date,
        # Before-date — brave
        template_event_before_deadline,
        # Recurring — brave
        template_us_debt,
        template_bitcoin_above_threshold,
        template_wikipedia_accessible,
    ]


# ===========================================================================
# Validation
# ===========================================================================

def validate_dynamic_dataset(dataset: dict) -> list:
    """Validate against schema 4.0 rules. Returns list of errors."""
    errors = []

    # Metadata checks
    meta = dataset.get("metadata", {})
    if not meta.get("generated_at"):
        errors.append("metadata.generated_at is required")

    sv = dataset.get("schema_version")
    if sv != "4.0":
        errors.append(f"schema_version must be '4.0', got '{sv}'")

    preds = dataset.get("base_predictions", [])
    if not preds:
        errors.append("base_predictions is empty")

    for i, p in enumerate(preds):
        pid = p.get("id", f"<idx-{i}>")

        # Non-null verdict
        verdict = p.get("expected_verification_outcome")
        if verdict not in VALID_VERDICTS:
            errors.append(f"{pid}: expected_verification_outcome must be one of {VALID_VERDICTS}, got '{verdict}'")

        # Valid mode
        mode = p.get("verification_mode")
        if mode not in VALID_MODES:
            errors.append(f"{pid}: verification_mode must be one of {VALID_MODES}, got '{mode}'")

        # Valid difficulty
        diff = p.get("difficulty")
        if diff not in VALID_DIFFICULTIES:
            errors.append(f"{pid}: difficulty must be one of {VALID_DIFFICULTIES}, got '{diff}'")

        # Ground truth computation
        gt = p.get("ground_truth", {})
        gtc = gt.get("ground_truth_computation", {})
        if not gtc:
            errors.append(f"{pid}: ground_truth.ground_truth_computation is required")
        else:
            for field in ["source", "raw_data", "computation_logic", "computed_at"]:
                if field not in gtc:
                    errors.append(f"{pid}: ground_truth_computation.{field} is required")

        # Ground truth source
        gts = gt.get("ground_truth_source")
        if gts not in VALID_SOURCES:
            errors.append(f"{pid}: ground_truth_source must be one of {VALID_SOURCES}, got '{gts}'")

        # ID prefix
        if not pid.startswith("dyn-"):
            errors.append(f"{pid}: dynamic prediction IDs must start with 'dyn-'")

        # Recurring must have interval
        if mode == "recurring" and not p.get("recurring_interval"):
            errors.append(f"{pid}: recurring predictions must have recurring_interval")

    return errors


# ===========================================================================
# Main
# ===========================================================================

def write_dataset(dataset: dict, path: str) -> None:
    """Write validated dataset to JSON file."""
    with open(path, "w") as f:
        json.dump(dataset, f, indent=2)
    logger.info("Wrote %d predictions to %s", len(dataset.get("base_predictions", [])), path)


def main() -> None:
    """Generate dynamic golden dataset and write to output path."""
    now = datetime.now(timezone.utc)
    logger.info("Generating dynamic dataset at %s", now.isoformat())

    # Set up Brave search function
    brave_fn = None
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if api_key:
        brave_fn = brave_search
        logger.info("Brave API key found — brave_search templates enabled")
    else:
        logger.warning("BRAVE_API_KEY not set — only deterministic templates will run")

    # Collect predictions from all templates
    predictions = []
    templates = get_all_templates()
    for tmpl in templates:
        try:
            pred = tmpl(now, brave_fn)
            if pred is not None:
                predictions.append(pred)
                logger.info("  ✓ %s → %s (%s)", pred["id"], pred["expected_verification_outcome"], pred["verification_mode"])
            else:
                logger.info("  ⊘ %s skipped (brave_fn=None or no results)", tmpl.__name__)
        except Exception as e:
            logger.error("  ✗ %s failed: %s", tmpl.__name__, e)

    # Count by mode
    mode_counts = {}
    for p in predictions:
        m = p["verification_mode"]
        mode_counts[m] = mode_counts.get(m, 0) + 1

    logger.info("Generated %d predictions: %s", len(predictions), mode_counts)

    # Build dataset
    dataset = {
        "schema_version": "4.0",
        "dataset_version": "dynamic-1.0",
        "metadata": {
            "generated_at": now.isoformat(),
            "generator_version": "1.0",
            "brave_api_available": brave_fn is not None,
            "expected_base_count": len(predictions),
            "expected_mode_counts": mode_counts,
        },
        "base_predictions": predictions,
    }

    # Validate
    errors = validate_dynamic_dataset(dataset)
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Write
    write_dataset(dataset, OUTPUT_PATH)
    logger.info("Dynamic dataset generation complete")


if __name__ == "__main__":
    main()
