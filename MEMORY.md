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
- Expanding training dataset (currently 9 queries — needs 500+)

### What's Next 🔴
- Add train/test split + proper metrics (accuracy, F1, confusion matrix)
- Add 1-2 more tools to make task harder and more interesting
- Persistent log saving to CSV
- Conference paper draft (Overleaf)

---

## Key Decisions Made
- **Use Mistral 7B via Ollama locally** — free, reproducible, no API costs
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
| — | — | No commits yet |

---

## Update This File After Every Session
```
### Session — [Date]
- What was done:
- What was decided:
- Action items:
- Blockers:
```
