# Contributing

Use synthetic examples only. Start with `docs/PROJECT_STATE.md`, then read the relevant domain contract and existing tests. Keep a change narrow enough to demonstrate through the real API, operational state and processing evidence.

Financial changes must specify posting semantics, transition/idempotency behavior and concurrency implications before implementation. Add forward migrations; never edit an applied migration to make checks pass. Test using actual service roles. Include negative/failure evidence when a change affects financial, access or recovery boundaries.

For UI changes, preserve light/Dusk tokens, keyboard/text alternatives and server permissions. Mark planned capabilities honestly. Do not introduce empty domain screens or claim a simulator is a real integration.

A pull request should explain the user-visible behavior, trade-off, exact checks executed, tested topology and remaining limits. Document measured bottlenecks and costs before introducing another processor, scheduler or service. No paid provisioning, real customer data or external messages are part of a routine contribution.
