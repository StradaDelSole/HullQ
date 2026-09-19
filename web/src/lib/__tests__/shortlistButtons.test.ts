import assert from "node:assert/strict";
import { test } from "node:test";

import { shortlistButtonLabel } from "../shortlistButtons.ts";

const text = { saveLabel: "Save to shortlist", savedLabel: "Saved" };

test("shortlistButtonLabel: not saved shows the save label", () => {
  assert.equal(shortlistButtonLabel(false, text), "Save to shortlist");
});

test("shortlistButtonLabel: saved shows the saved label", () => {
  assert.equal(shortlistButtonLabel(true, text), "Saved");
});
