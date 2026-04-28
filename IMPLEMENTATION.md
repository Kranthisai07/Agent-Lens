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

- [ ] **3.1** Create `data/queries.json` with initial 9 queries from Calix's notebook
- [ ] **3.2** Use Claude to generate 100 queries per tool category (300 total minimum)
  - Calculator queries: math, percentages, conversions, word problems
  - Search queries: facts, history, definitions, people, news
  - Summarizer queries: CSV stats, column info, data questions
- [ ] **3.3** Review generated queries — remove duplicates, fix any mislabeled ones
- [ ] **3.4** Add query count printout so you always know dataset size
- [ ] **3.5** Target: 500+ queries before training

```bash
git commit -m "data-03: expand query dataset to 500+ examples across 3 tool categories"
```

---

## Phase 4 — Training Pipeline
**Goal:** Train logistic regression policy model on collected trajectories.

- [ ] **4.1** Create `training/train.py`
- [ ] **4.2** Load `data/trajectories/logs.csv`
- [ ] **4.3** Print class distribution — make sure tools are balanced
- [ ] **4.4** TF-IDF vectorizer with `ngram_range=(1,2)`, `max_features=5000`
- [ ] **4.5** 80/20 train/test split with `random_state=42`
- [ ] **4.6** Train `LogisticRegression(max_iter=1000)`
- [ ] **4.7** Save model: `joblib.dump(model, "models/policy_model.pkl")`
- [ ] **4.8** Save vectorizer: `joblib.dump(vec, "models/tfidf_vectorizer.pkl")`
- [ ] **4.9** Add `predict_tool(query)` function using saved model

```bash
git commit -m "train-04: TF-IDF + LogisticRegression pipeline, saves model and vectorizer"
```

---

## Phase 5 — Evaluation
**Goal:** Proper metrics for the paper.

- [ ] **5.1** Create `training/evaluate.py`
- [ ] **5.2** Load saved model + vectorizer
- [ ] **5.3** Run on test split
- [ ] **5.4** Print:
  - Accuracy
  - F1 (macro + per class)
  - Classification report
  - Confusion matrix (heatmap saved as PNG)
- [ ] **5.5** Save confusion matrix to `data/confusion_matrix.png`
- [ ] **5.6** Baseline comparison: random guessing = `1/num_tools`
- [ ] **5.7** Record results in MEMORY.md

```bash
git commit -m "eval-05: accuracy, F1, confusion matrix, baseline comparison"
```

---

## Phase 6 — Model Comparison (Paper Table)
**Goal:** Compare multiple classifiers for the results section.

- [ ] **6.1** Add to `training/evaluate.py`:
  - Logistic Regression (baseline)
  - SVM (linear kernel)
  - MLP (64, 32 hidden layers)
  - Optional: Random Forest
- [ ] **6.2** Output comparison table: model | accuracy | F1-macro | train time
- [ ] **6.3** Save table to `data/model_comparison.csv`
- [ ] **6.4** This table goes directly into the paper

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
| 3 — Dataset Expansion | 🔴 Not started |
| 4 — Training Pipeline | 🔴 Not started |
| 5 — Evaluation | 🔴 Not started |
| 6 — Model Comparison | 🔴 Not started |
| 7 — Paper (Conference) | 🔴 Not started |
| 8 — Multi-Agent + RL | 🔴 Not started |

---

## Update After Every Session
Check off completed steps, update status table, update MEMORY.md.
