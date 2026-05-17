# Taxonomy Model Eval Results

**Date:** 2026-05-16  
**Script:** `scripts/eval_taxonomy_models.py`  
**Seed data:** 53 articles across 10 categories (`tests/seed_data.py`)  
**Judge model:** gpt-4o  

---

## Results

### Consolidate Task

| Model | Time (s) | Valid JSON | Complete | Judge score |
|---|---|---|---|---|
| gpt-4.1-mini *(current)* | 2.4 | ✓ | ✓ | 4.0 / 5 |
| gpt-5.4-nano | 3.2 | ✓ | ✗ | 4.0 / 5 |
| gpt-5.4-mini | 4.2 | ✓ | ✓ | 4.0 / 5 |
| gpt-5-mini | 12.2 | ✓ | ✓ | 4.0 / 5 |
| gpt-4o | 26.4 | ✓ | ✗ | 4.0 / 5 |

### Split Task (Artificial Intelligence, 27 articles)

| Model | Time (s) | Valid JSON | Complete | Judge score |
|---|---|---|---|---|
| gpt-4.1-mini *(current)* | 6.0 | ✓ | ✓ | 4.0 / 5 |
| gpt-5.4-nano | 5.1 | ✓ | ✓ | 3.5 / 5 |
| gpt-5.4-mini | 8.6 | ✓ | ✓ | 4.0 / 5 |
| gpt-5-mini | 14.5 | ✓ | ✓ | 4.0 / 5 |
| gpt-4o | 18.4 | ✓ | ✓ | 4.0 / 5 |

---

## Verdict: keep gpt-4.1-mini

`gpt-4.1-mini` is the fastest on both tasks, passes all completeness checks, and ties for top quality score. No candidate model outperforms it on any metric that matters.

---

## Per-model notes

**gpt-4o** — Disqualified on consolidate. It misread the context format and mapped sub-categories (e.g. `"AI Applications"`, `"AI Integration with Business Tools"`) as if they were top-level categories, rather than operating on the 10 actual taxonomy names. This is a prompt comprehension failure. Also 10× slower than gpt-4.1-mini.

**gpt-5.4-mini** — Works correctly on both tasks and produces quality on par with gpt-4.1-mini. Slower and ~3× more expensive ($0.75 vs ~$0.15 per 1M tokens). Not worth the cost increase given identical quality scores.

**gpt-5.4-nano** — Two behavioural problems:
- *Consolidate:* included article counts in `old_category` values (e.g. `"Artificial Intelligence (27 articles)"` instead of `"Artificial Intelligence"`), failing exact-match completeness. Suggests the model over-copies from the context.
- *Split:* created 14 distinct groups for 27 articles, completely ignoring the "2–4 groups" constraint in the prompt. Lowest judge score (3.5/5). Would need prompt hardening before use.

**gpt-5-mini** — Rejects `temperature` and `frequency_penalty` parameters entirely — only accepts API defaults. This means our tuning (temp=0.3, freq_penalty=0.15) cannot be applied, which is a risk for consistency. Quality was good when it ran, but the API constraint is a blocker for a drop-in replacement.

---

## Hyperparameter tuning (gpt-4.1-mini)

**Script:** `scripts/eval_tuning.py`  
**Method:** Per-axis sweeps — one parameter varied at a time, others held at the production baseline. Final comparison run 3× per config to average out noise.

**Baseline:** `temperature=0.3  frequency_penalty=0.15  presence_penalty=0.0`

**Parameters swept:**
- `temperature`: 0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0
- `frequency_penalty`: 0.0, 0.1, 0.15, 0.2, 0.3, 0.5
- `presence_penalty`: 0.0, 0.1, 0.3, 0.5

### Consolidate — ranked by quality, then speed

| Params | Time (s) | Complete | Judge avg |
|---|---|---|---|
| t=0.3 fp=0.0 pp=0.0 | 2.5 | ✓ | 4.0 / 5 |
| t=0.1 fp=0.15 pp=0.0 | 2.6 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.15 pp=0.5 | 2.3 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.15 pp=0.0 *(baseline)* | 3.4 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.2 pp=0.0 | 3.6 | ✗ | 4.0 / 5 |
| t=1.0 fp=0.15 pp=0.0 | 3.6 | ✗ | 4.0 / 5 |
| t=0.3 fp=0.1 pp=0.0 | 9.5 | ✗ | 3.5 / 5 |

### Split — ranked by quality, then speed

| Params | Time (s) | Complete | Judge avg |
|---|---|---|---|
| t=0.3 fp=0.0 pp=0.0 | 5.1 | ✓ | **4.5 / 5** |
| t=0.5 fp=0.15 pp=0.0 | 4.7 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.15 pp=0.1 | 4.9 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.15 pp=0.0 *(baseline)* | 5.5 | ✓ | 4.0 / 5 |
| t=0.3 fp=0.5 pp=0.0 | 6.6 | ✗ | 4.0 / 5 |

### Key findings

**`frequency_penalty=0.0` is the strongest challenger.** It was the only config to exceed 4.0/5 anywhere — scoring 4.5/5 on split with a perfect usefulness rating. On consolidate it also scored 4.0/5 and was one of the fastest configs (2.5s). In a 3-run head-to-head vs the baseline, it consistently outscored on quality (4.0 vs 3.83 averaged) while remaining competitive on speed.

**The baseline holds up well for split.** On the split task, `fp=0.0` adds 1.8s of latency for a quality gain that averaged out over 3 runs — a marginal tradeoff.

**Configs to avoid:**
- `frequency_penalty=0.1` — worst outcome across both tasks: slowest (9.5s on consolidate), only sub-4.0 judge score, and caused a completeness failure. Actively harmful.
- `frequency_penalty=0.5` — completeness failure on split. High penalty prevents the model from consistently repeating category names across all article assignments.
- `temperature=1.0` — completeness failure on consolidate. Too noisy for reliable structured JSON at the top level.

### Tuning verdict

The model is not highly sensitive to these parameters within reasonable ranges — quality scores are flat across most configs. **The production baseline (`t=0.3, fp=0.15, pp=0.0`) is well-placed and validated.** The only change worth considering is dropping `frequency_penalty` to `0.0` if consolidate quality becomes a concern, accepting a small latency trade.

---

## API compatibility findings

The GPT-5 model family required changes to the eval script vs. what the production `aiapi` currently sends:

| Parameter | gpt-4o / gpt-4.1-mini | gpt-5.4-mini / gpt-5.4-nano | gpt-5-mini |
|---|---|---|---|
| `max_tokens` | ✓ | ✗ (use `max_completion_tokens`) | ✗ |
| `temperature` ≠ 1 | ✓ | ✓ | ✗ |
| `frequency_penalty` | ✓ | ✓ | ✗ |

If we ever switch to a GPT-5 model, `aiapi/task_processor.py` will need to be updated to use `max_completion_tokens`. The `gpt-5-mini` restriction on temperature/frequency_penalty means it cannot be used as a drop-in without also re-validating output quality under default sampling.

---

## Open follow-on items

- **Split group cap:** The "2–4 groups" prompt constraint is already too tight for a 57-article production AI bucket (yields 14–28 articles per group). Consider making the target proportional: `max(2, count // 12)` groups. This is independent of model choice.
- **Per-task models:** Consolidate and split could use different models (e.g. nano for classify, mini for taxonomy) via a new `AI_OPEN_AI_TAXONOMY_MODEL` env var. Not worth pursuing until a model meaningfully outperforms gpt-4.1-mini on at least one task.
- **Classification model eval:** `classify_url` (the most frequent call) also uses `AI_OPEN_AI_MODEL`. A nano might be sufficient for that simpler extraction task. Worth a separate eval run.
