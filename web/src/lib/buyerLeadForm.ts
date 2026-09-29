// SLICE-0070: client-side wiring for the bounded buyer contact form on the
// public listing page (`pages/listings/[native_listing_id].astro`).
// Submits to the same-origin proxy route
// (`pages/listings/[native_listing_id]/contact.ts`), never FastAPI's host
// directly, and never implies the submitted email is verified (contract
// §11: "The form must not imply the email is verified").
import type { BuyerLeadContactOutcome } from "./buyerLeadApi.ts";

export interface BuyerLeadFormText {
  submittingLabel: string;
  successLabel: string;
  invalidInputLabel: string;
  listingNotAvailableLabel: string;
  serviceErrorLabel: string;
}

/**
 * Classify one contact-submission HTTP response into the bounded outcome
 * vocabulary. Pure and DOM-free -- the only place response-shape parsing
 * happens, so it stays independently unit-testable.
 */
export function parseContactResponse(status: number, body: unknown): BuyerLeadContactOutcome {
  if (status === 200 || status === 201) {
    const parsed = (body ?? {}) as { status?: unknown; lead_id?: unknown; received_at?: unknown };
    if (
      (parsed.status === "CREATED" || parsed.status === "ALREADY_EXISTS") &&
      typeof parsed.lead_id === "string" &&
      typeof parsed.received_at === "string"
    ) {
      return {
        kind: parsed.status === "CREATED" ? "created" : "already_exists",
        leadId: parsed.lead_id,
        receivedAt: parsed.received_at,
      };
    }
    return { kind: "service_error" };
  }
  if (status === 400) return { kind: "invalid_input" };
  if (status === 404) return { kind: "listing_not_available" };
  if (status === 409) return { kind: "submission_conflict" };
  return { kind: "service_error" };
}

/** Pure label selection -- unit-testable without touching the DOM. */
export function contactResultText(
  outcome: BuyerLeadContactOutcome,
  text: BuyerLeadFormText,
): string {
  switch (outcome.kind) {
    case "created":
    case "already_exists":
      return text.successLabel;
    case "invalid_input":
      return text.invalidInputLabel;
    case "listing_not_available":
      return text.listingNotAvailableLabel;
    case "submission_conflict":
    case "service_error":
      return text.serviceErrorLabel;
  }
}

/**
 * Whether the current bounded opaque submission-operation identity should
 * be replaced before the next submit attempt. A fresh identity is needed
 * once a Lead has actually been durably created (so a later, genuinely new
 * message never collides with the prior one's idempotency key) and after a
 * SUBMISSION_CONFLICT (reusing that same identity could only ever conflict
 * again). `invalid_input`/`listing_not_available`/`service_error` keep the
 * identity unchanged -- contract §11's "visible retry-safe service failure
 * state" requires a plain retry of the same attempt to stay idempotent.
 */
export function shouldRotateSubmissionOperationId(outcome: BuyerLeadContactOutcome): boolean {
  return (
    outcome.kind === "created" ||
    outcome.kind === "already_exists" ||
    outcome.kind === "submission_conflict"
  );
}

function contactEndpoint(nativeListingId: string): string {
  return `/listings/${encodeURIComponent(nativeListingId)}/contact`;
}

/**
 * Wires the single `[data-buyer-contact-form]` on the page to the same-
 * origin contact proxy. Safe to call once per page load. *fetchImpl*
 * defaults to the real `window.fetch` and is overridable only for tests
 * that construct a DOM without a network-capable `fetch`.
 */
export function initBuyerContactForm(
  root: ParentNode,
  text: BuyerLeadFormText,
  fetchImpl: typeof fetch = window.fetch.bind(window),
): void {
  const form = root.querySelector<HTMLFormElement>("[data-buyer-contact-form]");
  if (!form) return;
  const nativeListingId = form.dataset.nativeListingId;
  if (!nativeListingId) return;
  const resultEl = root.querySelector<HTMLElement>("[data-buyer-contact-result]");
  const submitButton = form.querySelector<HTMLButtonElement>("button[type=submit]");

  let submissionOperationId = crypto.randomUUID();

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const requestBody = {
      submission_operation_id: submissionOperationId,
      name: String(formData.get("name") ?? ""),
      email: String(formData.get("email") ?? ""),
      message: String(formData.get("message") ?? ""),
    };

    if (submitButton) submitButton.disabled = true;
    if (resultEl) resultEl.textContent = text.submittingLabel;

    void fetchImpl(contactEndpoint(nativeListingId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    })
      .then(async (response) => {
        const parsedBody: unknown = await response.json().catch(() => null);
        return parseContactResponse(response.status, parsedBody);
      })
      .catch((): BuyerLeadContactOutcome => ({ kind: "service_error" }))
      .then((outcome) => {
        if (submitButton) submitButton.disabled = false;
        if (resultEl) resultEl.textContent = contactResultText(outcome, text);
        if (shouldRotateSubmissionOperationId(outcome)) {
          submissionOperationId = crypto.randomUUID();
        }
        if (outcome.kind === "created" || outcome.kind === "already_exists") {
          form.reset();
        }
      });
  });
}
