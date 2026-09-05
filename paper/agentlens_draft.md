# AgentLens: Behavioral Trajectory Learning for Automated Tool Selection in AI-Assisted Cybersecurity Agents

**Kranthi [Last Name]**, **Ricardo Calix**
Purdue University Northwest
{kranthi, rcalix}@pnw.edu

> **Format note.** This is a review draft in Markdown. Target venue: IEEE Big
> Data 2026 (or equivalent), IEEE two-column conference style. Section length
> targets are noted in `<!-- comments -->` and tallied at the end. Tables and
> figures are described inline; the final LaTeX will use `IEEEtran` with
> `\twocolumn`, `table`, and `figure*` environments as marked.

---

## Abstract
<!-- target: <=150 words -->

Large language model (LLM) agents increasingly orchestrate external tools to
complete multi-step tasks, but on ambiguous or long-horizon queries they select
tools inconsistently, latching onto surface keywords rather than task intent. We
present **AgentLens**, a framework that treats an agent's own tool decisions as
training data: a logging wrapper records *(prompt, tool)* behavioral
trajectories as the agent runs, and a lightweight classifier learns a
tool-selection policy that replaces LLM routing. We instantiate AgentLens on a
cybersecurity attacker/defender scenario with 11 SSH-based tools and a 640-query
labeled dataset spanning direct and deliberately ambiguous queries. A TF-IDF +
SVM policy, evaluated with 5-fold cross-validation, reaches **98.3% ± 0.8%**
accuracy versus **79.4%** for the Llama 3.2 3B baseline, and **94.5% ± 2.5%**
versus **73.5%** on hard queries, while routing each query in **0.3 ms** versus
**209 ms** (700× faster). Trained trajectory policies can thus replace LLM tool
routing—faster, cheaper, and more accurate.

---

## 1. Introduction
<!-- target: ~400 words -->

Modern AI agents built on LLMs solve complex tasks by decomposing them into
steps and invoking external tools—search engines, code interpreters, shell
commands. The quality of such an agent depends less on its language fluency than
on a narrower competence: given the current task, *which tool should it call?*
On clearly worded requests this is easy. On ambiguous, underspecified, or
multi-step requests it is not, and small locally-hosted models are especially
brittle. They tend to match a salient keyword in the prompt to a tool name and
ignore the surrounding intent—reading "scan the target and see what comes back"
as a version scan when a port sweep was meant.

This failure is costly in cybersecurity. An AI-assisted penetration-testing
agent that chooses the wrong reconnaissance tool wastes time and, worse, can
miss an exposed service and the vulnerability behind it. A defensive agent that
reads the wrong log misses an active intrusion. As agents are given real
offensive and defensive tooling, reliable tool selection becomes a safety
property, not a convenience.

Rather than fine-tuning the LLM—expensive, opaque, and hard to reproduce on
commodity hardware—AgentLens takes a behavioral view. As the agent runs, every
tool decision it makes is logged as a *(prompt, tool)* pair. These trajectories
become a labeled dataset from which a lightweight classifier learns the
tool-selection policy directly. At inference the trained policy replaces the LLM
for routing: it is deterministic, sub-millisecond, and—because it is trained on
ground-truth labels rather than the LLM's own guesses—more accurate than the
model it replaces.

We instantiate and evaluate AgentLens on a cybersecurity attacker/defender
scenario. Our contributions are:

1. **A trajectory-collection framework** that automatically and transparently
   logs an agent's tool decisions with rich metadata, at zero modeling cost.
2. **A labeled dataset** of 640 cybersecurity agent queries across 11 tools and
   three agent roles, with difficulty and query-style annotations that isolate
   *why* tool selection is hard.
3. **A trained policy classifier** that outperforms LLM routing by **19
   percentage points overall** and **21 points on ambiguous queries**, at
   **700× lower latency**.
4. **An empirical analysis of LLM tool-selection failure modes**, showing that
   genuinely ambiguous and multi-step queries—not merely long ones—are where a
   small LLM breaks down, and that a trained policy closes exactly this gap.

---

## 2. Related Work
<!-- target: ~300 words -->

**LLM tool use.** Toolformer [1] teaches a model to self-annotate when to call
APIs; ToolLLM [2] and Gorilla [3] scale tool repertoires to thousands of APIs;
ReAct [4] interleaves reasoning traces with tool actions. These works make the
*LLM itself* the router at every step. AgentLens instead *observes* the router
and distills its task into a standalone classifier, removing the LLM from the
inference path entirely.

**AI agents in cybersecurity.** A growing line of work applies LLM agents to
automated penetration testing and vulnerability discovery, wiring models to
scanners and shells. This research focuses on *what the agent can accomplish*;
AgentLens focuses on the reliability and cost of the tool-routing decision
underneath, and contributes a labeled benchmark for it in the security domain.

**Behavioral cloning and imitation learning.** Learning a policy from logged
expert state–action pairs is the classical behavioral-cloning setup [5].
AgentLens is behavioral cloning where the "state" is a natural-language prompt
and the "action" is a tool; unlike typical imitation learning we clone against
*corrected* ground-truth labels rather than the demonstrator's raw actions,
which lets the student exceed the teacher.

**Lightweight classifiers vs. LLMs for routing.** Recent systems use small
models or embeddings to route queries to models or tools for efficiency. We push
this to its conclusion for the tool-selection subproblem: a TF-IDF + linear
model routes in 0.3 ms and, on our task, is more accurate than a 3B LLM. AgentLens
adds a difficulty-annotated benchmark that quantifies *when* the cheap router is
enough and characterizes the LLM failure modes it repairs.

<!-- References are numbered placeholders; full BibTeX to be added with Calix. -->
**References (to complete):** [1] Schick et al., *Toolformer* (2023); [2] Qin et
al., *ToolLLM* (2023); [3] Patil et al., *Gorilla* (2023); [4] Yao et al.,
*ReAct* (2023); [5] Pomerleau, *ALVINN / behavioral cloning* (1991); plus
automated-pentesting and LLM-routing citations.

---

## 3. Methodology
<!-- target: ~500 words -->

### 3.1 System Architecture

AgentLens has three components: the **agent**, the **trajectory logger**, and
the **policy classifier**. During data collection the agent runs normally and
the logger records every decision; after training, the policy classifier can
serve tool-routing decisions with no LLM in the loop.

```
 COLLECTION (Phase 1–2)
   Query ─▶ LLM Agent ─▶ Tool Selection ─▶ Execute Tool
                                │
                                ▼
                 Log(prompt, tool_predicted, tool_ground_truth,
                     agent_role, difficulty, category, run_id)

 TRAINING (Phase 3)
   Logs ─▶ TF-IDF ─▶ Classifier (LR/SVM/MLP/RF) ─▶ Policy Model

 DEPLOYMENT
   Future Query ─▶ Policy Model ─▶ Tool        (no LLM call)
```

*Figure 1* will render this pipeline. The design keeps collection, training, and
inference in separate modules so the trained policy can be dropped in front of,
or in place of, the LLM router.

### 3.2 Trajectory Collection

Every tool is wrapped by a `logging_tool` decorator that appends a trajectory
record to a shared log before the tool executes; the wrapper is transparent to
the tool's return value, so collection adds no behavioral overhead. Each record
carries the schema **`prompt, tool_predicted, tool_ground_truth, agent_role,
difficulty, category, run_id`**. Crucially we log both the tool the LLM *chose*
(`tool_predicted`, the baseline) and the *correct* tool (`tool_ground_truth`,
the training label); training on the latter is what allows the policy to surpass
the LLM.

We drive tool selection by calling the Ollama API directly rather than through a
CrewAI ReAct loop. The 3B model could not reliably emit CrewAI's verbose
tool-call format and frequently returned empty responses; a direct call asking
for a single-word tool name from the role's tool set is robust and also yields
cleaner trajectories (the original natural-language query is logged, not an
LLM-rewritten tool input). The LLM is **Llama 3.2 3B** served locally by Ollama
(`temperature=0`, `seed=42`).

Tool execution runs over a live SSH connection to an isolated Ubuntu 20.04 VM
(VirtualBox NAT, paramiko connection pooling). Commands execute with a
10-second timeout; tool selection is recorded independently of execution
success, ensuring trajectory labels reflect LLM routing decisions rather than
infrastructure state. Of 640 queries, 470 commands executed successfully on the
real VM; the remaining 170 reflect infrastructure constraints (nmap requires
snap installation on the SeedLabs VM; SSH-to-self requires key-based auth)
rather than agent errors.

### 3.3 Dataset

The cybersecurity scenario defines **11 tools** across three roles: an
**attacker** (4 tools: SSHConnect, NmapScan, PortScan, CheckVulnerability), a
**defender** (5 tools: ReadAuthLog, ListeningPorts, BlockIP, CheckFailedLogins,
ListProcesses), and **shared** utilities (2 tools: GetSystemInfo, ReadSyslog).
The dataset contains **640 labeled queries** (attacker 261, defender 273, shared
106), generated by a seeded, reproducible template expander. Each query is tagged
`easy` (440, one unambiguous tool cue) or `hard` (200), and hard queries are
split into five style categories designed to probe distinct failure modes.

**Table I — Query categories and LLM accuracy** (Llama 3.2 3B):

| Category | n | LLM Acc | Design |
|---|---|---|---|
| direct (easy) | 440 | 82.0% | one clear tool cue (control) |
| ambiguous | 40 | 57.5% | two+ tools plausible, no disambiguating keyword |
| multistep | 40 | 70.0% | mini-workflow; labelled by primary step |
| trick | 40 | 72.5% | decoy keyword / negation for another tool |
| natural | 40 | 82.5% | casual phrasing, no jargon |
| opposite | 40 | 85.0% | leads toward a sibling tool, then corrects |

### 3.4 Policy Classifier

Queries are vectorized with **TF-IDF, (1,2)-grams, `max_features=5000`**. We
train four classifiers—Logistic Regression, linear SVM, MLP (64, 32), and Random
Forest (100 trees)—on `tool_ground_truth`. We evaluate with **5-fold
StratifiedKFold** stratified on the combined `tool × difficulty` label, so every
(tool, difficulty) cell appears in each fold. The vectorizer is refit inside
each fold to prevent train/test leakage. We report mean ± standard deviation of
overall accuracy, hard-subset accuracy, and macro-F1 across folds.

---

## 4. Experiments and Results
<!-- target: ~400 words -->

### 4.1 Main Results

**Table II — Tool-selection accuracy and latency** (5-fold CV, mean ± std;
LLM baseline is a single deterministic pass, no CV):

| Method | Overall Acc | Hard Acc | Latency |
|---|---|---|---|
| LLM Baseline (Llama 3.2 3B) | 79.4% | 73.5% | 209 ms |
| **SVM (linear)** | **98.3% ± 0.8%** | **94.5% ± 2.5%** | 0.3 ms |
| Logistic Regression | 98.1% ± 0.6% | 94.0% ± 2.0% | 0.3 ms |
| MLP (64, 32) | 98.0% ± 0.8% | 93.5% ± 2.5% | 0.3 ms |
| Random Forest | 97.8% ± 1.5% | 93.0% ± 4.9% | 0.3 ms |

All four classifiers beat the LLM decisively. The best, linear SVM, improves on
the LLM by **18.9 points overall** and **21.0 points on hard queries**. The four
models are statistically indistinguishable overall (overlapping ± intervals);
Random Forest has the widest hard-query spread (±4.9%). *Figure 2* is the
aggregated out-of-fold confusion matrix (n = 640, pooled 98.3%): the 11 residual
errors all fall between semantically adjacent tools—NmapScan↔PortScan,
ListProcesses↔ListeningPorts, and within the log family (ReadAuthLog,
CheckFailedLogins, ReadSyslog).

### 4.2 LLM Failure-Mode Analysis

The category breakdown (Table I) localizes where the LLM fails. Accuracy
collapses on **ambiguous** queries (57.5%) and is weak on **multistep** (70.0%)
and **trick** (72.5%) queries, while remaining high on direct, natural, and
opposite phrasings. The dominant confusion is NmapScan vs. PortScan: asked to
"scan the target and see what comes back," the 3B model cannot decide between a
service/version scan and a port sweep because neither keyword is present. In
short, the model latches onto surface keywords and, when they are absent or
misleading, guesses. The trained classifier does not share this weakness: having
learned from ground-truth labels rather than the LLM's predictions, it recovers
the intended tool on exactly these categories, lifting hard-query accuracy from
73.5% to 94.5%.

### 4.3 Latency Analysis

Measured over real inference calls, the classifier routes a query in **0.3 ms**;
the LLM's median is **209 ms** and its mean **816 ms**, inflated by cold-start
outliers (max 7.7 s). At the median this is a **~700× speedup**; routing the full
640-query set takes the classifier ~0.2 s versus ~135 s for the LLM. Sub-
millisecond, deterministic routing makes production deployment of the trained
policy feasible at scale, and removes per-query model cost entirely.

---

## 5. Discussion
<!-- target: ~200 words -->

The results support a simple claim with broad implications for agentic AI: for
the bounded subproblem of tool selection, a policy *cloned* from an agent's own
behavior—and corrected against ground truth—can be faster, cheaper, and more
accurate than the LLM that generated it. Where the general-domain version of this
task saturates (a linear model reaches ~100% because keywords fully determine the
tool), the cybersecurity task is genuinely hard, and the ~21-point hard-query gap
is where the contribution lives.

**Limitations.** The dataset is synthetic, built from seeded templates rather
than real penetration-test transcripts, so absolute numbers may not transfer to
operator-written queries. Real VM execution is confirmed on a single Ubuntu
20.04 VM via SSH (ping 8.8.8.8: 3/3 packets, 7-8ms RTT). The full two-VM
attacker/defender lab (isolated network, separate attacker and defender hosts)
remains as future work for the journal paper extension. And the baseline is a
single 3B model—larger LLMs may route better, narrowing the gap.

**Future work.** Building on the confirmed single-VM execution, we will stand up
the isolated two-VM attacker/defender lab so trajectories carry genuine tool
outputs and success signals from separate hosts. We will extend to a two-agent
attacker/defender setup with reinforcement learning (the journal follow-up), and
evaluate a middle tier—fine-tuned small encoders (BERT/Qwen via TRL)—between the
TF-IDF policy and the full LLM.

---

## 6. Conclusion
<!-- target: ~150 words -->

We presented AgentLens, a framework that turns an LLM agent's own tool decisions
into training data for a lightweight tool-selection policy. On a cybersecurity
attacker/defender scenario with 11 tools and a 640-query difficulty-annotated
dataset, a TF-IDF + SVM policy trained on collected trajectories reaches 98.3% ±
0.8% accuracy—19 points above the Llama 3.2 3B router it replaces—and 94.5% ±
2.5% on hard, ambiguous queries where the LLM manages only 73.5%, all at 0.3 ms
per query versus 209 ms. The key insight is that the LLM generates its own
training data for free, and that training against ground-truth labels lets the
student surpass the teacher precisely on the ambiguous cases that matter. We will
release the framework, dataset, and models as open source. AgentLens lays the
groundwork for a reinforcement-learning-based multi-agent extension with real
tool execution.

---

<!-- ===================== REVIEW APPENDIX (not for camera-ready) ===================== -->

## Appendix A — Draft self-review

### A.1 Word counts per section

Prose only — tables, the ASCII figure, reference lines, and HTML comments are
excluded from the count (they carry additional content not reflected in these
numbers).

| Section | Target | Prose words | Status |
|---|---|---|---|
| Abstract | ≤150 | 146 | on target |
| 1. Introduction | ~400 | 371 | on target |
| 2. Related Work | ~300 | 292 | on target |
| 3. Methodology | ~500 | 414 | **under (prose)** — §3.3/§3.4 content sits in Table I and the pipeline figure |
| 4. Experiments | ~400 | 297 | **under (prose)** — Table II carries the numbers; expand §4.2 analysis |
| 5. Discussion | ~200 | 180 | on target |
| 6. Conclusion | ~150 | 133 | slightly under |

### A.2 Sections under target length (flagged)
- **§3 Methodology (414 prose words vs 500).** Not padding-worthy on its own —
  much of the section's substance is in Table I and the architecture figure. If
  the venue counts prose strictly, add ~2–3 sentences to §3.2 on the metadata
  fields and to §3.4 on why linear TF-IDF suffices here.
- **§4 Experiments (297 prose words vs 400).** Table II holds the results; the
  natural expansion is §4.2, e.g. a worked NmapScan-vs-PortScan example and
  per-role accuracy (attacker 68.2%, defender 85.3%, shared 91.5%).
- **§6 Conclusion (133 vs 150).** Within trimming distance; add one sentence on
  the open-source URL once the repo is public.
- **§1, §2** are a touch under but within tolerance; §2 can absorb the two
  pending citation sentences once references are chosen.

### A.3 Three things that need Dr. Calix's input before finalizing
1. **Target venue and author metadata.** IEEE Big Data 2026's submission
   deadline (Aug 21, 2026) has passed; confirm the actual target venue and its
   page/format limits, plus the correct author last name, affiliations, and
   ORCID/email for the byline.
2. **Related-work scope and citations.** Confirm the reference set—especially
   which automated-pentesting and LLM-routing papers to cite—and whether the
   framing should lean "dataset/benchmark contribution" or "systems
   contribution," which changes emphasis in §1 and §2.
3. **Which LLM-baseline numbers are canonical.** The paper uses the
   trajectory-collection run (overall 79.4%, hard 73.5%, ambiguous 57.5%). An
   earlier dataset-generation pass reported ambiguous at 52.5% under a different
   prompt. Confirm we standardize on the collection-run figures throughout (as
   drafted) before any table is frozen.

### A.4 Figures/tables to create for the final paper
- **Figure 1 — System architecture.** `paper/figures/fig1_architecture.png`
  (collection → training → deployment); generated, grayscale, print-safe.
- **Figure 2 — CV confusion matrix.** `paper/figures/fig2_confusion_matrix.png`
  (aggregated out-of-fold, n=640); generated, publication-ready.
- **Figure 3 — Per-category LLM accuracy.** `paper/figures/fig3_category_accuracy.png`
  (bar chart from Table I highlighting the ambiguous dip); generated.
- **Figure 4 — Latency comparison.** `paper/figures/fig4_latency.png` (log-scale:
  classifier 0.3 ms vs LLM median 209 ms / mean 816 ms); generated.
- **Table I — Category breakdown** (drafted).
- **Table II — Main CV results** (drafted; source `data/cyber_cv_results.csv`).

### A.5 Data provenance (for reproducibility statement)
All numbers trace to committed artifacts: `data/trajectories/cyber_logs.csv`
(640 rows), `data/cyber_cv_results.csv`, `data/cyber_baseline_predictions.csv`,
`data/llm_latency.json`, and `paper/figures/fig2_confusion_matrix.png`. Generators:
`scripts/generate_cyber_queries.py`, `agents/cyber_agent.py`,
`training/train_cyber.py`, `training/evaluate_cyber.py`.
