# Q3 deployment-window evidence — 2026-08-29

## Scope

This record covers the API cutover from `01a9e6ca2637` to `c6afbb581ff7`.
Sampling started before the deployment command and continued for more than 60
seconds after the first new response. The pipeline fingerprint remained
`s10.sha256.3665b88553ad`, so `source_revision` was the cutover discriminator.

Raw evidence: `q3-deploy-window-2026-08-29.jsonl`

- SHA-256: `2ecc4304609e26026d2f1eb95cb86c1e62fc45fcc222d061db43d5547561e69c`
- 127 records from `2026-08-29T06:06:27.107818Z` through
  `2026-08-29T06:10:01.119917Z`
- Each record contains the complete response headers and body plus the sampler's
  extracted revision, cache, ledger, request, trace, and upstream-zone fields.

## Deployment timeline

| UTC | Event |
|---|---|
| 06:06:27 | First pre-deploy canonical sample: HTTP 200, revision `01a9e6ca2637`, no `Cache-Control` |
| 06:07:05 | `railway variables --set` created redeploy `967ad3fe-c063-4efe-955b-59c0a3275a29` from the prior image; Railway removed it before the sampler observed it serving |
| 06:07:10 | CLI upload created deployment `acf3549e-f497-4cee-8da4-21ce7b8c7d86` |
| 06:07:57 | Last old-version HTTP 200 sample |
| 06:08:14 | One canonical request returned HTTP 502 during cutover |
| 06:08:15 | First new cache-busted HTTP 200: revision `c6afbb581ff7`, `Cache-Control: no-store` |
| 06:08:17 | First new canonical HTTP 200 with the same revision and cache policy |
| 06:10:01 | Last recorded sample; the new version had remained stable for more than 100 seconds |

Railway reported `acf3549e-f497-4cee-8da4-21ce7b8c7d86` as `SUCCESS`, one
replica in `sfo`, Serverless disabled, and `/data` mounted. The uploaded image
digest was `sha256:ccf0e7223a7108e59c81d5bf430254309519aa21188830b85082e0cc9e6209bc`.

## Results

- 126 HTTP 200 responses and one cutover HTTP 502.
- For each mode, 30 successful old responses and 33 successful new responses.
- After the first new response, no old revision reappeared.
- All 66 successful new responses had `Cache-Control: no-store`, a `ledger`
  block, and `ledger_observed_at`.
- Canonical and cache-busted URLs did not diverge on revision or ledger shape.
- The new process exposed two ledger observation times,
  `2026-08-29T06:08:00.904125Z` and `2026-08-29T06:09:02.277568Z`, demonstrating
  the bounded refresh after approximately 60 seconds.
- Every record reported upstream zone `railway/us-west2`. The two observed
  `x-hikari-trace` values are retained as routing evidence only, not interpreted
  as application-instance identities.

## Interpretation

This deployment did not reproduce the historical stale-response symptom. It
supports neither a canonical-URL cache hit nor a period in which successful old
and new application responses alternated. It did expose one brief unavailable
response at cutover.

The historical mechanism therefore remains unproven. The current operational
defect is accepted with that residual explicitly recorded: provenance endpoints
now declare `no-store`, deployment verification remains cache-busted, and this
observed cutover produced no stale successful response. The automatic old-image
redeploy caused by setting `NESTOR_BUILD_SHA` is a deployment-script follow-up;
it was removed before serving in this run and is not claimed as the historical
cause.

## Post-deploy verification

- `/health`: HTTP 200, revision `c6afbb581ff7`, `Cache-Control: no-store`,
  ledger configured/durable/writable at `/data/relationship_ledger.jsonl`.
- `/api/v1/capabilities`: same revision and ledger observation, pipeline
  `s10.sha256.3665b88553ad`.
- `/api/v1/audit` with the bundled Spain case: HTTP 200 and
  `outcome: ok_to_analyze`.
- Local required suite before deploy: `182 passed`.
- No web source changed since the prior deployed revision, so no web redeploy
  was performed.
