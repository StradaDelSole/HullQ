// SLICE-0096 independent review Finding D: mirrors searchText.test.ts's
// identical PARTIAL-page zero-result wording discipline for the entirely
// separate Power-only Search surface -- a buyer reading a PARTIAL zero-match
// Power page must never see wording that could equally describe a final/
// exhaustive absence.
import assert from "node:assert/strict";
import { test } from "node:test";

import { powerSearchText } from "../powerSearchText.ts";
import { SUPPORTED_LOCALES } from "../searchText.ts";

test("every supported locale has complete, distinct PARTIAL-page zero-result text (Finding D)", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = powerSearchText[locale];
    assert.ok(t.noDesignLinkedMatchesPartial.length > 0, `${locale}.noDesignLinkedMatchesPartial`);
    assert.ok(
      t.noDesignLinkedMatchesButPublisherClaimsExistPartial(3).includes("3"),
      `${locale}.noDesignLinkedMatchesButPublisherClaimsExistPartial must interpolate its count`,
    );
    assert.notEqual(
      t.noDesignLinkedMatchesPartial,
      t.noDesignLinkedMatches,
      `${locale}: a PARTIAL zero-match page must never read like the COMPLETE "no matches" claim`,
    );
    assert.notEqual(
      t.noDesignLinkedMatchesButPublisherClaimsExistPartial(3),
      t.noDesignLinkedMatchesButPublisherClaimsExist(3),
      `${locale}: the PARTIAL publisher-claims-exist wording must differ from the COMPLETE wording`,
    );
  }
});
