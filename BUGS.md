# Known Bugs

## Web digest job poll never reports "finished"

**Status:** Fixed
**Fixed in:** `recap/queries.py` (`job_status_value`), used by `routes.digest_job_status` and the API

### Description

`routes.digest_job_status` (`GET /digest/job/<job_id>`) returns `str(job.get_status())`. RQ's
`JobStatus` is a `str` Enum, so on Python 3.12 that is `"JobStatus.FINISHED"`, not `"finished"`,
and the polling JS in `index.html` / `digest.html` (`s.status === 'finished'`) never matches. The
API equivalent (`GET /api/v1/digest/job/<id>`) sends `status.value` and is not affected.

### Fix applied

Both job-status endpoints return `job_status_value(job)` (the enum's `.value`). The web route
tests in `tests/recap/integration/test_digest_routes.py` now mock `get_status` with the real
`JobStatus` enum (they used plain strings, which hid the bug).

## Weekly Digest — Cluster Labeling

**Status:** Fixed  
**Fixed in:** `aiapi/agents/synthesis/nodes.py`

### Description

When clustering by embedding, single-article clusters caused `_label_cluster` to hallucinate
unrelated labels. Confirmed example: "When to Use LangGraph" was labelled "Renewable Energy
Innovations" because only the article title was sent with no category or topic context.

### Fix applied

Two changes in `_cluster_by_embedding` / `_label_cluster`:

1. **Smaller n_clusters**: formula changed from `min(5, len(embedded))` to
   `min(5, max(1, len(embedded) // 2))`, targeting ~2 articles per cluster and preventing
   single-article clusters in most cases.

2. **Category fallback**: `_label_cluster` now returns the article's existing `category` field
   directly when a single-article cluster still occurs, rather than sending a bare title to the AI.

### Regression coverage

`tests/aiapi/unit/test_synthesis_nodes.py` — `TestLabelCluster`, `TestClusterByEmbedding` (8 tests)  
`tests/aiapi/eval/test_clustering_eval.py` — AI eval using the exact title that triggered the bug
