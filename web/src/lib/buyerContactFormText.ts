// SLICE-0070: fixed English copy for the bounded buyer contact form on the
// public listing page, mirroring `shortlistText.ts`'s single-import
// convention (imported both server-side, for initial markup, and
// client-side, by the wiring script) -- the listing page's existing
// English-only convention (no locale-routing redesign is authorized here
// per contract §8) applies identically to this form.
//
// Never implies the submitted email is verified (contract §11).
import type { BuyerLeadFormText } from "./buyerLeadForm.ts";

export interface BuyerContactFormText extends BuyerLeadFormText {
  heading: string;
  disclaimer: string;
  nameLabel: string;
  emailLabel: string;
  messageLabel: string;
  submitLabel: string;
}

export const buyerContactFormText: BuyerContactFormText = {
  heading: "Contact the seller",
  disclaimer: "Your email is not verified by HullQ.",
  nameLabel: "Your name",
  emailLabel: "Your email",
  messageLabel: "Message",
  submitLabel: "Send message",
  submittingLabel: "Sending…",
  successLabel: "Message sent. The listing organization will contact you directly.",
  invalidInputLabel: "Please check your name, email and message and try again.",
  listingNotAvailableLabel: "This listing is no longer available.",
  serviceErrorLabel: "We couldn't send your message. Please try again.",
};
