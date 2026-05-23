# Known Bugs

## Weekly Digest — Cluster Labeling

**Status:** Open  
**Priority:** Low — cosmetic, does not affect digest generation  

### Description

When clustering by embedding (`_cluster_by_embedding` in `aiapi/agents/synthesis/nodes.py`), the AI-generated cluster label can be completely wrong. In testing, an article titled "When to Use LangGraph" (clearly an AI Framework article) was placed in a single-article cluster and labelled "Renewable Energy Innovations".

### Root cause (hypothesis)

`_label_cluster` sends only the article titles to the AI with no prior category or topic context. With a single-article cluster and a short title, the model appears to hallucinate an unrelated label rather than deriving one from the content.

### Reproduction

Run `weekly_digest_task` for a user with articles that produce single-article embedding clusters. The label for that cluster will sometimes be nonsensical.

### Possible fixes (not yet investigated)

- Fall back to the article's existing `category` field when a cluster has only one article
- Include article summaries and key topics in the label prompt (currently only titles are sent, capped at 10)
- Add a sanity check: if the generated label shares no semantic overlap with the article titles, re-prompt or use the category fallback
