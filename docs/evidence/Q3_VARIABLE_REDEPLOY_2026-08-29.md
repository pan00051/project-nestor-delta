# Q3 variable-redeploy experiment — 2026-08-29

## Question

Does changing a Railway service variable create a redeploy of the previously
uploaded source that can receive public traffic before a subsequent source
upload completes?

This is the concrete candidate mechanism for the historical capabilities
response: `scripts/deploy-railway.sh` sets `NESTOR_BUILD_SHA` and then runs
`railway up`. The first command can therefore start the prior source before the
second command uploads the new source.

## Method

The sampler was started against canonical and cache-busted capabilities before
any variable change. `NESTOR_BUILD_SHA` was then temporarily changed from the
real revision `c6afbb581ff7` to the valid hexadecimal sentinel
`deadbeef3333`. This changes only the provenance label read at process startup;
it does not change analysis, API, ledger, or Report behavior.

After the sampler observed the sentinel serving public requests,
`NESTOR_BUILD_SHA` was restored to `c6afbb581ff7`. Sampling continued for more
than 80 seconds after the first restored response.

Raw evidence: `q3-variable-redeploy-2026-08-29.jsonl`

- SHA-256: `650cade410ba7d3aa7d410b54105c114d085553687c22cf0084450c5f0bddeae`
- 134 records from `2026-08-29T06:34:44.918957Z` through
  `2026-08-29T06:38:56.690810Z`
- Every record contains the complete response headers and body.

## Timeline

| UTC | Event |
|---|---|
| 06:34:44 | Baseline canonical HTTP 200, revision `c6afbb581ff7` |
| 06:35:24 | Sentinel variable change created redeploy `cfa0b9bf-ca81-4047-8a51-547b2292f500` |
| 06:35:56 | Canonical request returned HTTP 502 at cutover |
| 06:35:58 | First public HTTP 200 from sentinel revision `deadbeef3333` |
| 06:37:04 | Restoring the real variable created redeploy `93139bad-ddf5-4d38-851d-7e67feec4015` |
| 06:37:12 | Last public sentinel response |
| 06:37:29 | Cache-busted request returned HTTP 502 at restore cutover |
| 06:37:30 | First restored HTTP 200 from `c6afbb581ff7` |
| 06:38:56 | Last sample, after more than 80 seconds of stable restored traffic |

Both redeploys reported image digest
`sha256:05785cf1d9e7acad2541c10fdbcc039b6d131e18a073be821ffc13d755f7b4b3`.
No new source was uploaded during the experiment.

## Results

- 132 HTTP 200 responses and two cutover HTTP 502 responses.
- The variable-triggered redeploy served 48 successful sentinel responses: 24
  canonical and 24 cache-busted.
- The observed sentinel service window lasted about 74 seconds.
- After restore, 50 consecutive successful responses returned the real
  revision; no sentinel response returned.
- Every successful response retained pipeline
  `s10.sha256.3665b88553ad`, `Cache-Control: no-store`, and the ledger block.
  That is expected because the prior source for this controlled run was already
  `c6afbb581ff7`.

## Conclusion

The candidate mechanism is confirmed: a variable change can start the
previously uploaded source and that redeploy can serve public requests. In the
current deployment script, the previous source is also given the *new*
`NESTOR_BUILD_SHA` before the new source upload starts. During an upgrade from a
pre-ledger version, that process can therefore return the previous
`pipeline_version` and omit the ledger block while appearing to carry the new
source revision.

This reproduces the mechanism capable of producing every structural feature of
the historical stale response. The original request cannot be tied to a
deployment ID retroactively, so historical attribution remains a high-confidence
inference rather than direct request-level proof.

Q3 diagnosis is complete. Remediation is intentionally not part of this
experiment: `scripts/deploy-railway.sh` remains unchanged. Before another
production source deploy, the variable update must be made non-deploying or the
upload/verification sequence must otherwise prevent prior-source traffic from
being accepted as the new build.
