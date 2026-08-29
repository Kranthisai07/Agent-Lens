# IMPLEMENTATION.md — AgentLens
Step-by-step build plan. Every step ends with a git commit.
Check off tasks as you complete them.

---

## Git Commit Convention
```bash
git add .
git commit -m "[phase]-[step]: short description"

# Examples:
git commit -m "setup-01: init repo structure and requirements"
git commit -m "tools-02: add Calculator and Search tools with logging"
git commit -m "data-03: expand query dataset to 500 examples"
git commit -m "train-04: add TF-IDF + LogisticRegression pipeline"
git commit -m "eval-05: add accuracy, F1, confusion matrix metrics"
git commit -m "paper-06: add methodology section draft"
```

---

## Phase 0 — Repo Setup
- [x] **0.1** Create project folder `agentlens/`
- [x] **0.2** Create folder structure:
  ```
  agentlens/
  ├── CLAUDE.md
  ├── SKILLS.md
  ├── MEMORY.md
  ├── IMPLEMENTATION.md
  ├── requirements.txt
  ├── data/
  │   ├── queries.json        ← prompt dataset
  │   └── trajectories/       ← saved (prompt, tool) logs
  ├── agents/
  │   └── crew_agent.py
  ├── tools/
  │   ├── __init__.py
  │   ├── calculator.py
  │   ├── search.py
  │   └── summarizer.py
  ├── training/
  │   ├── train.py
  │   └── evaluate.py
  ├── notebooks/
  │   └── TrainAIagentsUseTools3.ipynb
  └── paper/
  ```
- [x] **0.3** Create `requirements.txt`:
  ```
  crewai
  ollama
  scikit-learn
  pandas
  numpy
  matplotlib
  seaborn
  joblib
  ```
- [x] **0.4** `git init`, add `.gitignore` (ignore `data/trajectories/*.csv` if large, `__pycache__`, `.env`)
- [x] **0.5** First commit

```bash
git commit -m "setup-00: init agentlens repo structure"
```

---

## Phase 1 — Tools + Logging Wrapper
**Goal:** Clean, modular tool definitions with automatic trajectory logging.

- [x] **1.1** Create `tools/calculator.py` — math eval tool
- [x] **1.2** Create `tools/search.py` — general knowledge search tool
- [x] **1.3** Create `tools/summarizer.py` — CSV describe/head tool
- [x] **1.4** Create `tools/__init__.py` — export all tools + `logging_tool` wrapper
- [x] **1.5** The `logging_tool` wrapper must:
  - Accept `(tool_name, func)` 
  - Append `{"prompt": input, "tool": tool_name}` to a shared `logs` list
  - Return the tool function result unchanged
- [x] **1.6** Test each tool manually (no agent yet)

```bash
git commit -m "tools-01: add Calculator, Search, Summarizer with logging wrapper"
```

---

## Phase 2 — CrewAI Agent
**Goal:** Single agent that uses tools and generates trajectory data automatically.

- [x] **2.1** Create `agents/crew_agent.py`
- [x] **2.2** ~~Configure Ollama LLM via CrewAI LLM~~ — **pivot:** call Ollama directly via `ollama.chat`. CrewAI's ReAct loop produced empty LLM responses with Llama 3.2 3B (model too small for the verbose tool-call format). Direct call uses a tiny system prompt asking for one-word tool name. See MEMORY.md.
- [x] **2.3** ~~CrewAI Agent with `max_iter=5`~~ — replaced by direct LLM call + dispatch table. Tools still wrapped via `logging_tool` so trajectories are logged identically.
- [x] **2.4** Load queries from `data/queries.json` (not hardcoded)
- [x] **2.5** Run agent on each query, collect logs
- [x] **2.6** After run, save logs to `data/trajectories/logs.csv` (append mode)
- [x] **2.7** Test with 3 queries, verify CSV is populated correctly — then full 9-query run, all 9 tools correctly classified

```bash
git commit -m "agent-02: CrewAI agent with Llama 3.2 3B, loads queries from JSON, saves logs to CSV"
```

---

## Phase 3 — Dataset Expansion
**Goal:** Go from 9 queries to 500+ diverse (prompt, tool) pairs.

- [x] **3.1** Create `data/queries.json` with initial 9 queries from Calix's notebook
- [x] **3.2** Generate 165+ queries per tool category via `scripts/generate_queries.py` (templated, seeded for reproducibility)
  - Calculator: 173 — basic arithmetic, percentages, word problems, multi-step, real-world
  - Search: 172 — concepts, events, people, places, countries, artifacts, phenomena
  - TableSummarizer: 173 — overview, columns, rows, missing-values, head, statcol, group-by, aggregation
- [x] **3.3** Review generated queries — `scripts/generate_queries.py` self-validates: 0 duplicates, all tools ≥160 entries
- [x] **3.4** Validation script prints total + per-tool counts + duplicates on every run
- [x] **3.5** Target met: 518 queries, balanced across 3 tools

```bash
git commit -m "data-03: expand query dataset to 500+ examples across 3 tool categories"
```

---

## Phase 4 — Training Pipeline
**Goal:** Train logistic regression policy model on collected trajectories.

- [x] **4.1** Create `training/train.py`
- [x] **4.2** Load `data/trajectories/logs.csv` — trains on `tool_ground_truth`, uses `tool_predicted` as the LLM baseline column
- [x] **4.3** Print class distribution — 173/172/173, imbalance ratio 1.01x
- [x] **4.4** TF-IDF vectorizer with `ngram_range=(1,2)`, `max_features=5000` → 1424 features
- [x] **4.5** Stratified 80/20 split with `random_state=42` — 414 train / 104 test
- [x] **4.6** Train `LogisticRegression(max_iter=1000)` — plus SVM, MLP, RandomForest (Phase 6 pulled forward)
- [x] **4.7** Save model: `models/policy_model.pkl` (best by macro F1 = MLP)
- [x] **4.8** Save vectorizer: `models/tfidf_vectorizer.pkl` (+ `models/label_classes.json`)
- [x] **4.9** `predict_tool(query)` in `training/predict.py` → `{"tool", "confidence"}`

```bash
git commit -m "train-04: TF-IDF + LogisticRegression pipeline, saves model and vectorizer"
```

---

## Phase 5 — Evaluation
**Goal:** Proper metrics for the paper.

- [x] **5.1** Create `training/evaluate.py`
- [x] **5.2** Load saved model + vectorizer
- [x] **5.3** Run on test split — reuses `train.py:build_split` so the split is identical
- [x] **5.4** Print accuracy, F1 (macro + per class), classification report, confusion matrix
- [x] **5.5** Save confusion matrix to `data/confusion_matrix.png` (seaborn, dpi=150)
- [x] **5.6** Baseline comparison: random 0.3333, majority 0.3365, LLM 0.7885, classifier 1.0000
- [x] **5.7** Record results in MEMORY.md

> ⚠️ **Result is saturated.** The best model scores **100.0%** on the test split and
> the confusion matrix is perfectly diagonal — zero errors to analyse. This is a
> property of the dataset, not a research finding: the templated queries carry
> unambiguous lexical cues. See MEMORY.md "Phase 4-5 Results" for why this is
> not publishable as-is and what has to change.

```bash
git commit -m "eval-05: accuracy, F1, confusion matrix, baseline comparison"
```

---

## Phase 6 — Model Comparison (Paper Table)
**Goal:** Compare multiple classifiers for the results section.

- [x] **6.1** Implemented in `training/train.py` (not evaluate.py — all four models are
  trained in one pass so the split and vectorizer are shared):
  - Logistic Regression (baseline) — 0.9808 acc / 0.9807 F1
  - SVM (linear kernel) — 0.9904 / 0.9903
  - MLP (64, 32 hidden layers) — 1.0000 / 1.0000  ← selected
  - Random Forest (n=100) — 0.9615 / 0.9616
- [x] **6.2** Comparison table: model | accuracy | F1-macro | train time | per-class F1
- [x] **6.3** Save table to `data/model_comparison.csv`
- [x] **6.4** Table is paper-ready, but see the Phase 5 caveat — every model is at or
  near ceiling, so the table shows no meaningful separation between classifiers.

```bash
git commit -m "eval-06: multi-model comparison table for paper results section"
```

---

## Phase 7 — Paper Writing (IEEE Big Data 2026)
**Goal:** Conference paper draft on Overleaf.

- [ ] **7.1** Wait for Calix to share Overleaf link
- [ ] **7.2** Draft Abstract (150 words)
- [ ] **7.3** Draft Introduction — problem, motivation, contributions
- [ ] **7.4** Draft Related Work — agent frameworks, tool use, policy learning
- [ ] **7.5** Draft Methodology — pipeline diagram + description
- [ ] **7.6** Draft Experiments — dataset stats, model results, confusion matrix
- [ ] **7.7** Draft Conclusion + Future Work (mention RL for journal)
- [ ] **7.8** Internal review with Dr. Calix
- [ ] **7.9** Submit by **August 21, 2026**

```bash
git commit -m "paper-07: add paper draft figures and supplementary materials"
```

---

## Phase 8 — Multi-Agent Extension (ICA 2026 Journal)
**Goal:** Extend to 2 agents + RL for journal paper.

- [ ] **8.1** Add second agent with different tool subset
- [ ] **8.2** Agents communicate via shared task decomposition
- [ ] **8.3** Add RL layer (policy gradient or Q-learning on tool selection)
- [ ] **8.4** Re-run evaluation with multi-agent trajectories
- [ ] **8.5** Submit by **November 10, 2026** to IEEE ICA-2026

```bash
git commit -m "multiagent-08: add second agent and RL tool selection policy"
```

---

## Current Status
| Phase | Status |
|---|---|
| 0 — Repo Setup | 🟢 Done |
| 1 — Tools + Logging | 🟢 Done |
| 2 — CrewAI Agent | 🟢 Done (direct Ollama, not CrewAI ReAct) |
| 3 — Dataset Expansion | 🟢 Done (518 queries; LLM 78.6% on re-run 20260829-133312) |
| 4 — Training Pipeline | 🟢 Done (4 models trained, saved) |
| 5 — Evaluation | 🟢 Done (100% test acc — saturated, see caveat) |
| 6 — Model Comparison | 🟢 Done (folded into train.py, `data/model_comparison.csv`) |
| 7 — Paper (Conference) | 🔴 Not started |
| 8 — Multi-Agent + RL | 🔴 Not started |

---

## Update After Every Session
Check off completed steps, update status table, update MEMORY.md.
