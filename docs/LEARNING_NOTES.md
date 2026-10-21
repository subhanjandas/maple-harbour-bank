# Learning notes

The production-bundle gate caught a preview configuration mismatch: Vite preview needs the same `/maple-harbour-bank/` base as the built Pages asset URLs. Development-server success alone was insufficient. The same candidate also failed an updated certifi security advisory; upgrading only the transitive lock preserves a narrow remediation and forces a fresh image/audit run.

## Live observatory engineering notes · release 0.4

A credible live dashboard needs actual instrumentation and explicit units. Source-event counts and current-state projections have different grains; financial charts must not read unapproved events. A durable synthetic workload can demonstrate meaningful idempotency and recovery without inventing production throughput.

Workload responses exposed a subtle snapshot issue: caching a mutable run object can change the response to a duplicate scheduling request as its cursor advances. The command cache now clones the response when accepted, and acceptance retries after progress to prove stable behaviour.

The first browser run passed all financial/recovery scenarios but rejected mobile overflow. Existing compact summary-card CSS inherited a two-column row inside each new dashboard card; the observatory now declares its own block layout. The test remains strict about actual document width and reports overflow elements. This is recorded as a failed candidate, not hidden as a successful initial test.


## A working increment is narrower than a technology diagram

The payment slice executes a real database transaction and durable pipeline. It is meaningful even before Kafka/Spark are present. Calling PostgreSQL analytical tables “Delta” would erase an important implementation boundary; the application, manifest and documentation label that distinction.

## Correctness needs independent questions

Balanced debits/credits cannot alone prove the customer balance or chosen accounts are right. Deferred journal checks and account roll-forward checks answer different questions. Analytical source controls answer a third: did the consumer receive the source versions it was expected to process? None proves that unseen real payment rails were complete.

## Database execution caught what compilation missed

The first CI PostgreSQL run failed during seed commit. A generic trigger's `CASE` expression referenced `NEW.journal_id` on a journal record that had only `NEW.id`. PostgreSQL resolved the incompatible record field even though that branch was not selected. Separate `IF` statements fixed the trigger in a forward migration. The original failed run remains inspectable; later passes are not substituted for that history.

## RLS has an owner boundary

Tests using a superuser to run the application would miss service grants and policy behavior. API and worker tests use actual separate login roles. A managed database owner may not be superuser: forcing owner row security inside a SECURITY DEFINER ledger check can hide the lines the check must inspect. The schema owner is trusted, the application is not the owner, and an ordinary-owner migration test is part of acceptance.

## Recovery depends on the exact crash window

The worker commits archive evidence before source acknowledgement. Killing it in between must cause redelivery without another archive row. Killing it inside the publication transaction must leave the old publication visible. These are different tests and both use child-process termination, not only a caught exception.

## Financial time and reporting time are different

A return has a booked date and a reporting attribution. Moving its reporting period should not credit the customer again. The aggregate version records the revision; Gold rebuilds current attribution while preserving old events and original financial journals.

## Measurements need units and limits

One accepted payment emits three initial lifecycle snapshots and two ledger lines. A generated million-row source-query fixture therefore says nothing about executing a million banking commands. Tail latency varied materially between the measured hot-account repetitions; report that variation and the workload before choosing an optimization.

## A small public demo has real operational responsibilities

Persistence, OIDC, visitor isolation, secret storage, quota/retention, backup restore and shutdown matter even for synthetic funds. A free frontend alone is not a deployed banking backend. The initial core stays local until these requirements and the spending ceiling are resolved.
