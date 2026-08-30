# CLAUDE.md — AgentLens

## Project Overview
**AgentLens** is a research project that collects agent behavioral trajectories — (prompt, tool) tuples — as a CrewAI + Llama 3.2 3B agent runs tasks, then trains a lightweight classifier to learn a tool selection policy. The goal is to replace expensive LLM-based tool routing with a fast, trained model and address objective drift in long-horizon agents.

**Collaborator:** Dr. Ricardo Calix (Purdue Northwest)
**Stack:** Python, CrewAI, Ollama (Llama 3.2 3B local), scikit-learn, pandas

---

## Research Goals
- Collect agent behavioral trajectory data automatically via logging wrappers
- Train a lightweight model (logistic regression → neural net) on (prompt → tool) pairs
- Show that a trained policy can replace LLM tool routing (faster, cheaper, drift-resistant)
- Publish two papers (see deadlines below)

---

## Paper Deadlines
| Paper | Venue | Deadline | Scope |
|---|---|---|---|
| Conference | IEEE Big Data 2026 | **Aug 21, 2026** | Single agent, dataset + proof of concept |
| Journal | IEEE Trans. Computational Social Systems | **Nov 10, 2026** | Multi-agent + RL, full framework |

---

## Project Structure
```
agentlens/
├── CLAUDE.md           ← this file
├── SKILLS.md           ← reusable task patterns for Claude
├── MEMORY.md           ← running project log
├── data/
│   ├── sales.csv       ← sample CSV for TableSummarizer tool
│   └── trajectories/   ← saved (prompt, tool) logs
├── agents/
│   └── crew_agent.py   ← CrewAI agent with logging wrappers
├── tools/
│   ├── calculator.py
│   ├── search.py
│   └── summarizer.py
├── training/
│   ├── train.py        ← TF-IDF + LogisticRegression pipeline
│   └── evaluate.py     ← accuracy, F1, confusion matrix
├── notebooks/
│   └── TrainAIagentsUseTools3.ipynb  ← Calix's baseline notebook
└── paper/
    └── agentlens_paper.tex / overleaf link
```

---

## Core Pipeline (3 Phases)

### Phase 1 — Tool Logging
Every tool is wrapped with a `logging_tool` decorator that appends `(prompt, tool_name)` to a `logs` list before execution. This is the trajectory collection — zero overhead, fully automatic.

### Phase 2 — Agent Run
A CrewAI agent with Llama 3.2 3B (via Ollama at `http://localhost:11434`) receives queries and picks tools. All decisions are silently logged.

### Phase 3 — Train Policy
Logs → TF-IDF vectorization → Logistic Regression → `predict_tool(query)` function.
Future: swap in neural net, SVM, or fine-tuned small LM. Add RL for journal paper.

---

## Current Bottleneck
Training data is only 9 queries — far too small. **Priority task: expand to 500+ diverse queries** across all tool categories before any meaningful evaluation.

---

## Tools Currently Defined
| Tool | Description |
|---|---|
| `Calculator` | Math operations via `eval()` |
| `Search` | General knowledge lookup |
| `TableSummarizer` | CSV describe + head via pandas |

---

## Key Conventions
- Always run Ollama locally before running agent: `ollama run llama3.2:3b`
- Save trajectory logs to `data/trajectories/` as CSV after each run
- Use `scikit-learn` metrics (accuracy, F1, confusion matrix) for every model eval
- Keep the pipeline modular — tools, logging, training, and inference are separate files
- Do NOT hardcode queries — load from a JSON/CSV file so the dataset is easy to expand

---

## What NOT to Do
- Do not retrain the LLM itself — only train the lightweight policy model
- Do not overcomplicate the agent setup — keep it single-agent until the conference paper is done
- Do not skip metrics — every model run must produce a confusion matrix
- Do not mix Phase 1 (data collection) with Phase 3 (trained inference) in the same run

---

## Commands
```bash
# Start Ollama
ollama run llama3.2:3b

# Run agent and collect trajectories
python agents/crew_agent.py

# Train tool policy
python training/train.py

# Evaluate model
python training/evaluate.py
```

---

## Git Commit Workflow
Every task ends with a commit. No exceptions.
```bash
git add .
git commit -m "[phase]-[step]: short description"
# Examples:
# "setup-00: init repo structure"
# "tools-01: add logging wrapper"
# "data-03: expand dataset to 500 queries"
# "eval-05: add confusion matrix"
```
Full step-by-step build plan with commit points → see **IMPLEMENTATION.md**

---

## Next Steps (Priority Order)
1. Expand query dataset to 500+ examples across 3+ tool categories
2. Save trajectory logs to CSV automatically after each agent run
3. Add proper train/test split and evaluation metrics
4. Add 1-2 more tools (e.g., weather, unit converter) to make classification harder
5. Write conference paper draft on Overleaf (Dr. Calix will share access)
6. Thursday demo: show AgentOS to Dr. Calix (independent study closeout)
