# MEMORY.md — AgentLens
Running project log. Update this after every work session.

---

## Project Identity
- **Name:** AgentLens
- **Researcher:** Kranthi (Purdue NW PhD student)
- **Advisor:** Dr. Ricardo Calix (Purdue NW)
- **Started:** April 2026

---

## The Core Idea
Agents running long tasks drift from their goal — they forget context, pick wrong tools, repeat steps. Instead of retraining the LLM, we observe the agent's behavior (trajectories) and train a tiny classifier to predict which tool to use given a prompt. This keeps the agent on track cheaply.

**Key insight:** The LLM generates the training data for us. Just let it run and log everything.

---

## What Has Been Tried (and Why It Was Dropped)

| Approach | Outcome | Why Dropped |
|---|---|---|
| Agent Operating System (AgentOS) | Built and working | Too broad for a paper; independent study project |
| NIO (context compression) | Delayed drift ~50-60 turns | Didn't solve drift, just delayed it |
| Neural network on trajectories | Pipeline worked | Training data too small (9 queries), poor results |

**Current approach:** TF-IDF + Logistic Regression on (prompt → tool) pairs. Simple, explainable, extensible.

---

## Paper Plan

### Paper 1 — Conference
- **Venue:** IEEE Big Data 2026
- **Deadline:** August 21, 2026
- **Notification:** October 2026
- **Conference date:** December 14-17, 2026 (Phoenix, AZ)
- **Scope:** Single agent, 3 tools, dataset contribution + proof of concept
- **Framing:** "A Dynamic Agent Behavioral Trajectory Dataset for Smart Tool Decision Making"
- **Status:** 🔴 Not started — need to expand dataset first

### Paper 2 — Journal
- **Venue:** IEEE Transactions on Computational Social Systems
- **Special Issue:** Cyber-Physical Social Intelligence
- **Deadline:** November 10, 2026
- **Scope:** Multi-agent (2 agents), RL-based policy, full framework
- **Relevant topic match:** "LLM-driven multi-agent systems for planning and collective decision making"
- **Status:** 🔴 Not started — depends on Paper 1

---

## Meetings Log

### Meeting 1 — April 2026 (with Dr. Calix)
- Reviewed Calix's baseline notebook (`TrainAIagentsUseTools3.ipynb`)
- Agreed: pipeline is correct, data is the bottleneck
- Agreed: start simple (1 agent), scale up for journal
- Decided project name: **AgentLens**
- **Action items from Kranthi:**
  - [ ] Thursday 4-5pm: Demo AgentOS to Dr. Calix (close out independent study)
  - [ ] Expand training queries to 500+
  - [ ] Save logs to CSV automatically
  - [ ] Find alternate IEEE/ACM conference if Big Data doesn't fit
  - [ ] Calix will create Overleaf doc and share access

---

## Current Status

### What's Done ✅
- Baseline notebook from Calix (`TrainAIagentsUseTools3.ipynb`)
- 3 tools defined: Calculator, Search, TableSummarizer
- Logging wrapper (`logging_tool`) collecting (prompt, tool) tuples
- End-to-end pipeline: agent run → log → vectorize → train → predict
- AgentOS (separate project, independent study — complete)

### What's In Progress 🟡
- Phase 9 — Cyber scenario. Pipeline + dataset + 11-tool dispatch + training all
  done. Classifier beats LLM 96.9% vs 81.2% (hard 90% vs 80%) on the held-out set.
  Next: larger hard test set (n=40 is noisy), then build the VMs for real execution.
- Phase 7 — paper. Blocked on a venue decision (Big Data deadline passed 2026-08-21)
  and on the dataset-difficulty problem below.

### Dataset Snapshot — 2026-04-28 (post Phase 3)
- **Source labels:** `data/queries.json`, 518 entries, balanced (Calculator 173 / Search 172 / TableSummarizer 173), 0 dupes
- **Generator:** `scripts/generate_queries.py` (seeded `random.seed(42)`) — reproducible
- **Trajectories collected:** `data/trajectories/logs.csv`, 518 rows
- **LLM (Llama 3.2 3B) accuracy vs ground-truth labels: 76.8% (398/518)**
- **Confusion (gt → llm picked):**
  - TableSummarizer → Calculator: 61 (LLM grabs "Calculate"/"average" cues)
  - Search → TableSummarizer: 32
  - Search → Calculator: 26
  - TableSummarizer → Search: 1
- **Implication:** the LLM over-predicts Calculator (260 vs 173 true). A trained classifier should beat 76.8% comfortably; that's our Phase 4–5 baseline-to-beat in the paper.

### What's Next 🔴
- **Build a harder dataset** — current task is saturated (see Phase 4-5 Results)
- Decide venue with Calix; IEEE Big Data 2026 deadline has passed
- Add 1-2 more tools / the cybersecurity SSH toolset
- Conference paper draft (Overleaf link still not shared)


### Phase 4-5 Results — 2026-08-29

**Trajectory re-run** (`run_id 20260829-133312`, schema now includes ground truth):
- 518 queries, balanced 173 Calculator / 172 Search / 173 TableSummarizer
- **LLM (Llama 3.2 3B) baseline: 407/518 = 78.6%** on the full set, 78.85% on the test split
- LLM confusion: TableSummarizer→Calculator 63, Search→TableSummarizer 28,
  Search→Calculator 19, TableSummarizer→Search 1
- LLM still over-predicts Calculator (255 predicted vs 173 true) — stable across all 3 runs

**Model comparison** (TF-IDF 1-2gram, max_features=5000 → 1424 features;
stratified 80/20, random_state=42; 414 train / 104 test). Full table in
`data/model_comparison.csv`:

| Model | Accuracy | F1 macro | Train time | F1 Calc | F1 Search | F1 TableSumm |
|---|---|---|---|---|---|---|
| **MLP (64,32)** | **1.0000** | **1.0000** | 421.5 ms | 1.0000 | 1.0000 | 1.0000 |
| SVM (linear) | 0.9904 | 0.9903 | 16.8 ms | 1.0000 | 0.9855 | 0.9855 |
| LogisticRegression | 0.9808 | 0.9807 | 17.5 ms | 0.9859 | 0.9706 | 0.9855 |
| RandomForest (100) | 0.9615 | 0.9616 | 136.9 ms | 0.9565 | 0.9429 | 0.9855 |

Saved: `models/policy_model.pkl` (MLP), `models/tfidf_vectorizer.pkl`,
`models/label_classes.json`. Confusion matrix: `data/confusion_matrix.png`.

**Baselines**
| Baseline | Accuracy |
|---|---|
| Random guessing (1/3) | 0.3333 |
| Majority class | 0.3365 |
| LLM routing (test split) | 0.7885 |
| **Trained classifier** | **1.0000** |

Gain over LLM: **+21.15 percentage points**; 100% relative error reduction.

**Latency** (measured, `data/llm_latency.json`, n=12 real Ollama calls):
| Route | ms/query |
|---|---|
| Classifier, single | 0.331 |
| Classifier, batched | 0.018 |
| LLM, median | 209.4 |
| LLM, mean | 815.7 (skewed by a 7.7 s cold start; stdev 2158 ms) |

**Speedup: ~632x vs LLM median, ~2461x vs mean.** Routing all 518 queries:
0.17 s (classifier) vs ~423 s (LLM). The earlier "~2-3 s/query" assumption was
wrong — measure, do not assume.

**⚠️ The headline number is not a good result.**
100% accuracy with a perfectly diagonal confusion matrix means the task is
saturated, not that the method is strong. The dataset is template-generated and
each class carries an unambiguous lexical cue ("Calculate…", "Who invented…",
"the dataset"). A grouped split that shares no template between train and test
also scores 100%, so this is not train/test leakage — the task is simply too
easy. Consequences:
- The confusion matrix figure is empty (all zeros off-diagonal) — useless as a
  paper figure.
- The 4-model comparison table shows no separation; nothing to conclude.
- No reviewer will accept "we beat a 3B LLM at keyword matching" as a finding.

`predict_tool()` gets all 8 spot-check queries right at >0.98 confidence,
including the 4 the LLM gets wrong ("Calculate the average revenue in the
dataset", "How many records are in the dataset?", "What is the population of
Mexico?", "Define photosynthesis"). Note 6 of those 8 are in the training data;
only 2 are genuinely held out. Nothing was flagged uncertain at the 0.7
threshold — the model is uniformly overconfident, which is itself evidence the
task is trivial.

**What has to change before Phase 7:** the pipeline is now complete and correct
end-to-end; the bottleneck has moved from *code* to *task difficulty*. The
cybersecurity attacker/defender dataset needs genuinely ambiguous queries
(two plausible tools), overlapping vocabulary between tools, and human-written
phrasings — targeting a task where TF-IDF lands in the 70-80s, not 100.


### Cyber Scenario — cyber-01 — 2026-08-29

The project's pivot to a cybersecurity attacker/defender use case now has a
working (mock) pipeline. This is the journal-paper (Phase 8) direction and a
response to the Phase 4-5 saturation problem: SSH tool selection is a harder,
more ambiguous task than Calc/Search/Table.

**Built:**
- `docs/VM_SETUP.md` — two Ubuntu 20.04 VMs, VirtualBox host-only 192.168.56.0/24
  (attacker .101 / defender .102), SSH + `agentlens` user, isolation warnings.
- `tools/cyber/` package: `ssh_connector.py` (paramiko), `attacker_tools.py`
  (NmapScan, PortScan, CheckVulnerability), `defender_tools.py` (ReadAuthLog,
  ListeningPorts, CheckFailedLogins, BlockIP, ListProcesses), `shared_tools.py`
  (get_system_info, read_syslog), plus `config.py`, `mocks.py`, and a
  `logging_tool`/`cyber_logs` pair mirroring `tools/__init__.py`.
- `agents/cyber_agent.py` — attacker + defender agents, per-role tool sets and
  system prompts, LLM tool selection with an offline keyword fallback.
- `data/cyber_queries.json` — 60-query stub (10 per tool × 3 tools × 2 agents).

**MOCK_MODE:** default True (env `AGENTLENS_MOCK` overrides). Tools return canned
nmap/auth.log/ss/iptables output so the pipeline runs with no VMs. Flip to False
once VM_SETUP.md is done. Live mode fails gracefully (SSH timeout -> error
string) rather than crashing.

**Trajectory schema (new columns):** `prompt, tool_predicted, tool_ground_truth,
agent_role, run_id`, written to SEPARATE files
`data/trajectories/attacker_logs.csv` and `defender_logs.csv`.

**Smoke test (run_id 20260829-150610, MOCK_MODE):**
- attacker 30/30 queries, LLM baseline 23/30 = 76.7% (confuses PortScan vs
  NmapScan on some phrasings — a genuinely ambiguous distinction, which is the point)
- defender 30/30 queries, LLM baseline 30/30 = 100.0%
- both CSVs written, 5-field schema, zero nulls

**Dependency:** `paramiko` (5.0.0) added to requirements.txt.

**Security note:** authorized lab use only. All recon/firewall tools target VMs
the researcher owns on an isolated host-only network. `agentlens123` is a
throwaway lab credential; passwords are never logged (only host+user on connect).

**Not done yet:** real VMs (VM_SETUP.md written, lab unbuilt); the full labelled
cyber dataset (this is a 60-row stub — needs the ambiguous/human-written queries
that justify the harder task); training/eval on cyber trajectories; RL layer.


### Cyber Dataset — cyber-02 — 2026-08-29

Expanded the 60-query stub into a full labelled dataset. This is the key
deliverable for a NON-saturated task (contrast the general dataset's 100%
classifier / 78.6% LLM ceiling in Phase 4-5 Results).

**`data/cyber_queries.json` — 640 queries**, generated by
`scripts/generate_cyber_queries.py` (seeded, reproducible, self-validating).
- 11 tools, corrected names: attacker {SSHConnect, NmapScan, PortScan,
  CheckVulnerability}; defender {ReadAuthLog, ListeningPorts, BlockIP,
  CheckFailedLogins, ListProcesses}; shared {GetSystemInfo, ReadSyslog}
- By agent: attacker 264 / defender 276 / shared 100; every tool >= 40
- Two new fields per row: `difficulty` (easy/hard) and `category`
  (direct / ambiguous / opposite / multistep / natural / trick)
- 440 easy (direct) + 200 hard (40 per hard category); 0 duplicates

**LLM baseline** (`scripts/measure_cyber_baseline.py`, llama3.2:3b, each agent's
full tool list offered; `data/cyber_baseline_predictions.csv`):

| Slice | n | LLM acc |
|---|---|---|
| Overall | 640 | 79.7% |
| easy (direct) | 440 | 83.0% |
| **hard** | **200** | **72.5%** (target 65-75% — met) |

**Category breakdown (the paper's "which query types fool the LLM" table):**
| Category | n | LLM acc | Reads as |
|---|---|---|---|
| direct | 440 | 83.0% | clear cue baseline |
| ambiguous | 40 | 52.5% | two+ tools plausible, no disambiguating keyword |
| multistep | 40 | 70.0% | workflow phrasing; LLM picks a later step |
| trick | 40 | 72.5% | decoy keyword / negation for another tool |
| natural | 40 | 82.5% | casual phrasing — mostly handled |
| opposite | 40 | 85.0% | leading-then-correcting phrasing — mostly handled |

**Finding:** genuinely ambiguous queries (no keyword tell) and multi-step
workflows fool the small LLM most; casual/opposite phrasing it handles. The
first tuning pass had the hard subset at 79.5% because the `ambiguous`
templates still leaked the disambiguating keyword (87.5% acc); stripping those
cues dropped it to 52.5% and pulled the hard subset into band. Even easy/direct
is only 83% — this task is not saturated, so the trained classifier has real
headroom here (unlike the general dataset).

**Still open:** `agents/cyber_agent.py` routes only 3 tools/role and drops
`agent=shared`, so only 349/640 flow through it — extend dispatch to all 11
tools + shared before collecting cyber trajectories and training. VMs still
unbuilt (mock mode).


### Cyber Dispatch + Training — cyber-02 (dispatch/train) — 2026-08-29

Extended agents/cyber_agent.py to all 11 tools across 3 roles, collected full
trajectories, and trained the cyber policy. **This is the paper's headline
result** — unlike the general dataset (classifier saturates at 100%, no margin
over the LLM), the cyber task gives the trained classifier a real, non-trivial
win over the LLM, including on hard queries.

**Dispatch:** attacker {SSHConnect, NmapScan, PortScan, CheckVulnerability},
defender {ReadAuthLog, ListeningPorts, BlockIP, CheckFailedLogins, ListProcesses},
shared {GetSystemInfo, ReadSyslog}. Routed by the query's `agent` field. All
640/640 queries now route (was 349/640).

**Trajectory schema** (data/trajectories/cyber_logs.csv, one combined file):
prompt, tool_predicted, tool_ground_truth, agent_role, difficulty, category, run_id.

**Collection (run_id 20260829-162521, MOCK_MODE, 640 rows):**
- LLM overall 79.4%, hard 73.5% — reproduces the dataset-gen 72.5% (per-role
  prompt wording accounts for the ~1 pt difference)
- by role: attacker 68.2%, defender 85.3%, shared 91.5%

**Training** (training/train_cyber.py; TF-IDF (1,2)-gram/5000; stratified 80/20
on DIFFICULTY -> 512 train / 128 test, 40 hard in test):

| Model | Overall | Hard | Easy | macro F1 |
|---|---|---|---|---|
| **SVM (best)** | **96.9%** | **90.0%** | 100% | 0.970 |
| LogReg | 96.9% | 90.0% | 100% | 0.970 |
| MLP | 96.9% | 90.0% | 100% | 0.970 |
| RandomForest | 95.3% | 85.0% | 100% | 0.956 |

**Paper results table** (training/evaluate_cyber.py, same 128-row test split for
all methods; latency: classifier 0.3 ms vs LLM median 209 ms):

| Method | Overall | Hard | Latency |
|---|---|---|---|
| LLM Baseline | 81.2% | 80.0% | 209 ms |
| LogReg / SVM / MLP | 96.9% | 90.0% | 0.3 ms |
| RandomForest | 95.3% | 85.0% | 0.3 ms |

**Best classifier vs LLM on the held-out set: 96.9% vs 81.2% overall,
90.0% vs 80.0% hard** — a real margin on exactly the ambiguous queries, at ~700x
lower latency. On the full 640 (which the classifier can't be scored on, having
trained on 80%) the LLM hard baseline is 73.5%.

**Confusion matrix** (data/cyber_confusion_matrix.png, paper figure) has real
content, not an empty diagonal: NmapScan<->PortScan, ListeningPorts->NmapScan,
GetSystemInfo->ReadSyslog, ReadSyslog->ReadAuthLog — semantically adjacent tools.

**Caveats:**
- Hard TEST subset is only n=40, so 90.0% = 36/40 — wide error bars; report with
  a CI or a larger hard test set before final numbers.
- Trajectories are MOCK_MODE (canned tool output); tool *selection* is real LLM,
  tool *execution* is fake. VMs still unbuilt.
- LLM baseline on the test split (81.2%/80.0%) runs higher than on the full set
  (79.4%/73.5%) just from which rows fell into the split; the test-split figure
  is the fair same-rows comparison, the full-set figure is the honest baseline.

Saved: models/cyber_policy_model.pkl (SVM, gitignored), cyber_tfidf_vectorizer.pkl
(gitignored), cyber_label_classes.json, data/cyber_model_comparison.csv,
data/cyber_confusion_matrix.png, data/cyber_test_index.json.

---

## Key Decisions Made
- **Use Llama 3.2 3B via Ollama locally** — free, reproducible, no API costs (switched from Mistral 7B on 2026-04-28 due to 8 GB RAM constraint on dev machine; weaker LLM also strengthens the "trained classifier replaces routing" narrative)
- **Bypass CrewAI's ReAct loop — call Ollama directly for tool selection** (decided 2026-04-28). Llama 3.2 3B couldn't reliably emit CrewAI's verbose tool-call format and failed with empty LLM responses on most queries. We now ask the LLM for a single-word tool name (Calculator / Search / TableSummarizer) per query and dispatch to the wrapped tool directly. Trajectory semantics improved as a side-effect — logs now record the original natural-language query, not the LLM's rewritten tool input.
- **Keep it single-agent for the conference paper** — multi-agent is journal scope
- **No RL for Paper 1** — supervised fine-tuning only; RL is journal Paper 2
- **Dataset paper framing for Paper 1** — easier to publish, still novel
- **Do NOT retrain the LLM** — only train the lightweight policy/classifier

---

## Important Links & Resources
- Calix baseline notebook: `notebooks/TrainAIagentsUseTools3.ipynb`
- IEEE Big Data 2026: [search "IEEE Big Data 2026 call for papers"]
- IEEE Trans. Computational Social Systems special issue: deadline Nov 10, 2026
- Overleaf paper: [add link when Calix shares]
- CrewAI docs: https://docs.crewai.com
- Ollama: https://ollama.ai

---

## Terminology Reference
| Term | Meaning in AgentLens |
|---|---|
| Trajectory | The sequence of (prompt, tool) pairs an agent produces on a task |
| Smart Tool | A tool that has a trained model inside to predict behavior |
| Policy | The trained classifier that maps prompt → tool |
| Drift | When an agent deviates from its original goal over many turns |
| Logging wrapper | `logging_tool()` decorator that records tool usage silently |

---

## Commit Log
| Commit | Phase | Description |
|---|---|---|
| 29be410 | setup-00 | init agentlens repo structure |
| 59ee898 | tools-01 | add Calculator, Search, Summarizer with logging wrapper |
| b2cf78e | agent-02 | CrewAI agent with Llama 3.2 3B, loads queries from JSON, saves logs to CSV |
| 1188169 | data-03 | expand query dataset to 500+ examples across 3 tool categories |
| 3f646e6 | rescue-00 | restore docs and trajectories to version control |
| e57a51e | fix-01 | log ground truth labels alongside LLM predictions, fix eval() security issue |
| aa05b91 | train-04+eval-05 | TF-IDF classifier pipeline, 4-model comparison, confusion matrix |
| 97e83bf | cyber-01 | SSH tool suite, attacker/defender agents, mock mode |
| 27acef3 | cyber-02 | 640-query labelled dataset, difficulty+category, LLM baseline 72.5% hard |
| (this) | cyber-02 | full 11-tool dispatch, cyber trajectory collection, classifier training |

---

## Update This File After Every Session
```
### Session — [Date]
- What was done:
- What was decided:
- Action items:
- Blockers:
```
