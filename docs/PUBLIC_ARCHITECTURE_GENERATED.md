# Architecture generated from the shared manifest

Do not edit the diagram by hand. Run `python scripts/render_architecture.py`.

```mermaid
flowchart TD
  web["Public banking application (implemented)"]
  api["Browser command engine (implemented)"]
  core["IndexedDB journal store (implemented)"]
  outbox["Transactional outbox (implemented)"]
  worker["Browser Web Worker (implemented)"]
  bronze["Bronze event archive (implemented)"]
  silver["Silver projections (implemented)"]
  gold["Gold publication (implemented)"]
  serving["Approved scenario views (implemented)"]
  cdc["Debezium → Kafka (planned)"]
  delta["Spark + Delta Lake (planned)"]
  airflow["Airflow orchestration (planned)"]
  generator["Seeded source simulator (implemented)"]
  web --> api
  api --> core
  core --> outbox
  outbox --> worker
  worker --> bronze
  bronze --> silver
  silver --> gold
  gold --> serving
  outbox -.-> cdc
  cdc -.-> delta
  airflow -.-> delta
  generator --> api
```

PUBLIC DEMO · GitHub Pages + browser worker + IndexedDB · no hosted API
