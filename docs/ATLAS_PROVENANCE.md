# Atlas provenance

Inspected 17 October 2026 directly from `subhanjandas/banking-model-atlas`.

| Item | Verified value |
|---|---|
| Imported commit | `69586431f1ed0ed5bf3c7d698b246b0662542d6d` |
| Default branch HEAD at inspection | Same commit; no drift from the supplied baseline |
| Application / model | 1.2.0 / 0.5.0 |
| Upstream license | MIT, copyright 2026 Subhanjan Das |
| Original new-repository HEAD | `81498870632b53d3e20ba9195830035f3d9c1941`, initial README only |

Read the requested README, platform handoff, engineering lab, validation coverage, interview guide, banking model, transition matrix, validation checks, scenario fixture, durable pipeline and engineering tests. Inspected UI entry points, graph URL-state handling, styles, theme logic and both CI workflows. Machine-readable inspected-file SHA-256 hashes are in `provenance/atlas-inspection.json`.

## Selected reuse

- `provenance/atlas-selected-model.json`: selected customer/account/payment/return/journal definitions and related rule specifications, with upstream identity.
- `provenance/atlas-lifecycle.json`: original transition matrices, retained as reference; the application enforces a deliberately smaller command vocabulary.
- `provenance/atlas-mapping.json`: explicit mapping from reference entities to application tables. Joint holders, product catalogs and many other Atlas tables are not mechanically imported.
- Light colors `#f8f9f6`, `#18353b`, `#26634f`; muted Dusk surfaces `#202a2c` and `#263234`; DM Sans and Manrope; rounded panels, restrained sage, readable inspector pattern. New application layouts are independently implemented.
- Test specifications: over-return prevention; balanced-but-wrong account detection; preserved originals; duplicate/out-of-order source versions; failed publication retaining the last good result; actual process exits.
- Canadian CAD scenario and Toronto business-date convention. New synthetic personas and funding amounts are independent of Atlas fixture balances.

The upstream MIT text is preserved in `provenance/ATLAS_LICENSE`; the new project uses the same copyright holder's MIT license. Dependencies retain their own licenses; font assets use SIL Open Font License. Bank of Canada data has separate source terms, not the project's MIT grant.

## Deep links

Atlas's `src/model.ts` validates the `entity` and `journey` URL parameters. The selected entity IDs are checked against the actual model. Examples:

- https://subhanjandas.github.io/banking-model-atlas/?entity=payment_order
- https://subhanjandas.github.io/banking-model-atlas/?entity=payment_event
- https://subhanjandas.github.io/banking-model-atlas/?entity=payment_return
- https://subhanjandas.github.io/banking-model-atlas/?entity=journal
- https://subhanjandas.github.io/banking-model-atlas/?journey=trace_a_deposit_payment

Atlas's existing Engineering Reference is static public evidence for a local lab. Maple Harbour's control room queries its own running backend. Neither embeds nor replaces the other. No Atlas files or other user repositories were modified.
