# Deployment and economics · CAD 0

## Verified public deployment

**https://subhanjandas.github.io/maple-harbour-bank/** is live on GitHub Pages. [Successful deployment](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39090991069), source `8ee3566baebbcf89c7e3677c6fd93803ae422441`, release 0.3. The HTTPS app returned HTTP 200 and passed a direct visible-UI payment, settlement, partial return, publication and recovery smoke. [Actual exported evidence](../evidence/live-pages-verification.json).

Pages serves the same React shell with browser worker processing and IndexedDB persistence. [Exact differences from the PostgreSQL profile](PUBLIC_DEMO.md). No paid resources, new hosting account or runtime credential is required. The agreed budget is **CAD 0**. Prior paid-provider investigations are superseded and retained only in Git history.

## Publish and roll back

`.github/workflows/pages.yml` runs six public browser journeys, builds with `VITE_PUBLIC_DEMO=true VITE_BASE_PATH=/maple-harbour-bank/`, packages an artifact, then deploys main using official `configure-pages`, `upload-pages-artifact` and `deploy-pages` actions. The repository's Pages source is GitHub Actions, verified by the successful deployment. A Pages deployment uses repository-managed `GITHUB_TOKEN` and job OIDC permissions; no user token is bundled into the application.

For an update, merge verified source to main and inspect the Pages workflow's terminal result. To republish unchanged main, use Actions → Public portfolio · test and deploy Pages → Run workflow. To roll back, revert the faulty source change and let the same acceptance/deploy path publish the previous behaviour. Do not reset or rewrite customer ledger state as a deployment rollback. Compatible browser schema v1 is retained; future schema changes require an explicit migration and recovery design.

A failed build/test does not deploy. GitHub Pages continues serving the previous successful artifact. A failure inside a visitor's analytical refresh independently retains that scenario's last-good publication.

## Cost and resource policy

Standard GitHub-hosted runners are free for this public repository; larger runners are not used. Pages hosts this non-commercial, synthetic portfolio. Workflow artifacts expire after **one day**, limiting retained test/video/build storage. Public static assets are about 1 MB excluding font/browser cache overhead; the exact packaged artifact is in the deployment run. No web-server process is kept alive through CI.

The browser processes only its own scenario, capped at 500 payments, 5,000 events, 200 proposals and 100 installments per payment. A scenario can be cleared or evicted by the browser and does not sync between devices. Worker execution stops when all pages close and resumes from persisted state when reopened. Browser storage/CPU and GitHub service limits are real constraints; no unrestricted hosting guarantee is made.

Official references: [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [Pages limits and intended use](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Server lab and shutdown

FastAPI, PostgreSQL and the durable Python worker are still available through `compose.yaml` and both Dockerfiles. [Main CI](https://github.com/subhanjandas/maple-harbour-bank/actions/runs/39090991147) built/started the containers, processed an actual HTTP payment/return, and restored a logical backup into a separate database. Those CI deployments stop; they are not a publicly hosted shared database.

`docker compose down` stops the local services and preserves the named database volume. Avoid `down -v` unless deliberately disposing of the synthetic local database. For the public site, GitHub Settings → Pages can disable publication; this does not erase any visitor's browser storage. No cloud resource cleanup or billing shutdown is needed for this release because none was provisioned.

Atlas remains independently deployed and unchanged. The public architecture explorer defaults to the Pages/browser topology; the PostgreSQL topology is explicitly a reference when viewed from Pages. Cloud Kafka/Spark/Delta/Airflow and production OIDC remain outside the current zero-cost hosted profile.
