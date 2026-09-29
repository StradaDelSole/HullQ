"""Unit tests for hullq.domain.buyer_lead — SLICE-0070.

Covers `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md` §8: bounded
name/email/message/submission-operation-id normalization, control-character
rejection (with the message field's newline/tab exemption), and the
LeadId/SubmissionOperationId identity kinds.
"""

from __future__ import annotations

import pytest

from hullq.domain.buyer_lead import (
    MAX_BUYER_EMAIL_LENGTH,
    MAX_BUYER_MESSAGE_LENGTH,
    MAX_BUYER_NAME_LENGTH,
    MAX_SUBMISSION_OPERATION_ID_LENGTH,
    ContactEmailVerificationState,
    LeadId,
    LeadSourceChannel,
    SubmissionOperationId,
    normalize_buyer_email,
    normalize_buyer_message,
    normalize_buyer_name,
    normalize_submission_operation_id,
)

# ---------------------------------------------------------------------------
# Identity kinds
# ---------------------------------------------------------------------------


def test_lead_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        LeadId("")


def test_submission_operation_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        SubmissionOperationId("")


def test_lead_id_and_submission_operation_id_are_runtime_distinct() -> None:
    lead_id = LeadId("X")
    submission_id = SubmissionOperationId("X")
    assert lead_id != submission_id


def test_contact_email_verification_state_v0_1_only_has_unverified() -> None:
    assert set(ContactEmailVerificationState) == {ContactEmailVerificationState.UNVERIFIED}


def test_lead_source_channel_v0_1_only_has_public_listing_contact() -> None:
    assert set(LeadSourceChannel) == {LeadSourceChannel.HULLQ_PUBLIC_LISTING_CONTACT}


# ---------------------------------------------------------------------------
# normalize_buyer_name
# ---------------------------------------------------------------------------


def test_normalize_buyer_name_trims_boundary_whitespace() -> None:
    assert normalize_buyer_name("  Jane Buyer  ") == "Jane Buyer"


def test_normalize_buyer_name_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        normalize_buyer_name(123)  # type: ignore[arg-type]


def test_normalize_buyer_name_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_name("   ")


def test_normalize_buyer_name_rejects_over_length() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_name("x" * (MAX_BUYER_NAME_LENGTH + 1))


def test_normalize_buyer_name_accepts_at_max_length() -> None:
    value = "x" * MAX_BUYER_NAME_LENGTH
    assert normalize_buyer_name(value) == value


def test_normalize_buyer_name_rejects_control_characters() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_name("Jane\x07Buyer")


def test_normalize_buyer_name_rejects_embedded_newline() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_name("Jane\nBuyer")


# ---------------------------------------------------------------------------
# normalize_buyer_email
# ---------------------------------------------------------------------------


def test_normalize_buyer_email_trims_boundary_whitespace() -> None:
    assert normalize_buyer_email("  jane@example.com  ") == "jane@example.com"


def test_normalize_buyer_email_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        normalize_buyer_email(None)  # type: ignore[arg-type]


def test_normalize_buyer_email_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_email("")


def test_normalize_buyer_email_rejects_missing_at() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_email("jane.example.com")


def test_normalize_buyer_email_rejects_missing_domain_dot() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_email("jane@example")


def test_normalize_buyer_email_rejects_embedded_whitespace() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_email("jane @example.com")


def test_normalize_buyer_email_rejects_over_length() -> None:
    local = "x" * (MAX_BUYER_EMAIL_LENGTH)
    with pytest.raises(ValueError):
        normalize_buyer_email(f"{local}@example.com")


def test_normalize_buyer_email_rejects_control_characters() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_email("jane\x00@example.com")


# ---------------------------------------------------------------------------
# normalize_buyer_message
# ---------------------------------------------------------------------------


def test_normalize_buyer_message_trims_boundary_whitespace() -> None:
    assert normalize_buyer_message("  Interested in this boat.  ") == "Interested in this boat."


def test_normalize_buyer_message_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        normalize_buyer_message(42)  # type: ignore[arg-type]


def test_normalize_buyer_message_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_message("   \n  ")


def test_normalize_buyer_message_rejects_over_length() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_message("x" * (MAX_BUYER_MESSAGE_LENGTH + 1))


def test_normalize_buyer_message_accepts_at_max_length() -> None:
    value = "x" * MAX_BUYER_MESSAGE_LENGTH
    assert normalize_buyer_message(value) == value


def test_normalize_buyer_message_preserves_embedded_newlines() -> None:
    assert normalize_buyer_message("Line one.\nLine two.") == "Line one.\nLine two."


def test_normalize_buyer_message_normalizes_crlf_to_lf() -> None:
    assert normalize_buyer_message("Line one.\r\nLine two.") == "Line one.\nLine two."


def test_normalize_buyer_message_rejects_non_newline_control_characters() -> None:
    with pytest.raises(ValueError):
        normalize_buyer_message("Interested\x07in this boat.")


# ---------------------------------------------------------------------------
# normalize_submission_operation_id
# ---------------------------------------------------------------------------


def test_normalize_submission_operation_id_trims_boundary_whitespace() -> None:
    assert normalize_submission_operation_id("  op-1  ") == "op-1"


def test_normalize_submission_operation_id_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        normalize_submission_operation_id(1)  # type: ignore[arg-type]


def test_normalize_submission_operation_id_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_submission_operation_id("")


def test_normalize_submission_operation_id_rejects_over_length() -> None:
    with pytest.raises(ValueError):
        normalize_submission_operation_id("x" * (MAX_SUBMISSION_OPERATION_ID_LENGTH + 1))
