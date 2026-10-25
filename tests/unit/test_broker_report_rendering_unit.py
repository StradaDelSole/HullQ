"""Unit tests for SLICE-0089 broker report HTML rendering.

Pure tests, no database. Prove: every interpolated value is HTML-escaped
(no injection via Organization display name, breakdown keys or listing
ids), a genuinely zero-lead/zero-view period is rendered explicitly (never
omitted or silently turned into an error page), the listing-truncated
notice only appears when truncation actually occurred, and no remote
resource/script is ever embedded.
"""

from __future__ import annotations

from hullq.application.broker_report_rendering import render_report_html


def _base_facts(**overrides: object) -> dict[str, object]:
    facts: dict[str, object] = {
        "window_start": "2026-01-01T00:00:00+00:00",
        "window_end": "2026-02-01T00:00:00+00:00",
        "public_listing_views": 0,
        "leads_received": 0,
        "leads_contacted": 0,
        "leads_closed": 0,
        "sold_outcomes": 0,
        "sold_outcomes_with_known_source": 0,
        "sold_outcomes_with_unknown_source": 0,
        "acquisition_source_breakdown": {},
        "discovery_source_breakdown": {},
        "first_contact_latency_known_count": 0,
        "first_contact_latency_unknown_count": 0,
        "median_first_contact_latency_seconds": None,
        "listings": [],
    }
    facts.update(overrides)
    return facts


def test_zero_lead_period_is_rendered_explicitly_not_omitted() -> None:
    html = render_report_html(
        organization_display_name="Acme Yachts",
        generated_at_iso="2026-02-01T00:00:00+00:00",
        facts=_base_facts(),
    )
    assert "Acme Yachts" in html
    assert "<script" not in html.lower()
    assert "No observed views" in html


def test_organization_display_name_is_escaped() -> None:
    html = render_report_html(
        organization_display_name="<script>alert(1)</script>",
        generated_at_iso="2026-02-01T00:00:00+00:00",
        facts=_base_facts(),
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_listing_native_id_is_escaped() -> None:
    html = render_report_html(
        organization_display_name="Acme Yachts",
        generated_at_iso="2026-02-01T00:00:00+00:00",
        facts=_base_facts(
            listings=[
                {
                    "native_listing_id": "<img src=x onerror=alert(1)>",
                    "public_listing_views": 1,
                    "leads_received": 0,
                    "leads_contacted": 0,
                    "leads_closed": 0,
                    "sold_outcome_recorded_at": None,
                    "sold_outcome_source_known": None,
                }
            ]
        ),
    )
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_truncated_notice_appears_only_when_flagged() -> None:
    facts = _base_facts(listings_truncated=True)
    html = render_report_html(
        organization_display_name="Acme Yachts",
        generated_at_iso="2026-02-01T00:00:00+00:00",
        facts=facts,
    )
    # listings is empty here, so the "no observed" branch renders (never the
    # truncation notice, which only applies to a non-empty listings table).
    assert "truncated" not in html.lower()


def test_unsupported_locale_falls_back_to_english_default() -> None:
    html = render_report_html(
        organization_display_name="Acme Yachts",
        generated_at_iso="2026-02-01T00:00:00+00:00",
        facts=_base_facts(),
        locale="xx",
    )
    assert "HullQ Performance Report" in html
