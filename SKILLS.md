# SKILLS.md — AgentLens

Reusable task patterns and prompts for Claude when working on this project.
Reference this file to get consistent, high-quality help across sessions.

---

## Skill 1 — Expand Query Dataset

**When to use:** You need more (prompt, tool) training pairs.

**Prompt template:**
```
Generate 100 diverse queries for an AI agent tool selection dataset.
The agent has these tools:
- Calculator: math operations, arithmetic, percentages, unit conversion via math
- Search: general knowledge, facts, people, news, definitions, history
- TableSummarizer: anything about a CSV, dataframe, dataset, statistics, columns

Return as a JSON list of objects with fields: "query" and "tool".
Make queries varied in phrasing, length, and complexity.
Distribute roughly evenly across tools.
Do not repeat similar queries.
```

---

## Skill 2 — Add a New Tool

**When to use:** You want to add a new tool to the agent and logging pipeline.

**Steps:**
1. Define the tool function in `tools/<toolname>.py`
2. Wrap it with `logging_tool("ToolName", your_function)` in `agents/crew_agent.py`
3. Add it to the `tools` list passed to the CrewAI Agent
4. Add a description row in `CLAUDE.md` tools table
5. Generate ~50 example queries for the new tool and add to the dataset

**Template:**
```python
def my_new_tool(x: str) -> str:
    """One sentence description of what this tool does."""
    # implementation
    return result

# In agents/crew_agent.py:
Tool(
    name="MyNewTool",
    func=logging_tool("MyNewTool", my_new_tool),
    description="Use for [specific use case]"
)
```

---

## Skill 3 — Train and Evaluate Policy Model

**When to use:** You have trajectory data and want to train + measure the classifier.

**Steps:**
1. Load logs CSV: `pd.read_csv("data/trajectories/logs.csv")`
2. Split: `train_test_split(X, y, test_size=0.2, random_state=42)`
3. Vectorize: `TfidfVectorizer(ngram_range=(1,2))`
4. Train: `LogisticRegression(max_iter=1000)`
5. Evaluate:
```python
from sklearn.metrics import classification_report, confusion_matrix
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
```
6. Save model + vectorizer with `joblib.dump()`

**Baseline to beat:** random guessing accuracy = 1/num_tools

---

## Skill 4 — Write a Paper Section

**When to use:** You need to draft a section of the conference or journal paper.

**Prompt template:**
```
Write the [Introduction / Related Work / Methodology / Experiments / Conclusion]
section for a research paper titled:
"AgentLens: A Behavioral Trajectory Framework for Tool Policy Learning in LLM Agents"

Key claims:
- LLM agents suffer from objective drift in long-horizon tasks
- We collect (prompt, tool) trajectory tuples automatically via logging wrappers
- A lightweight trained classifier can replace LLM-based tool routing
- This saves token cost and reduces drift

Target venue: [IEEE Big Data 2026 / IEEE Trans. Computational Social Systems]
Tone: formal academic. Length: [short/medium/long].
```

---

## Skill 5 — Debug CrewAI Agent Issues

**Common issues and fixes:**

| Issue | Fix |
|---|---|
| Ollama not responding | Run `ollama run llama3.2:3b` first, check port 11434 |
| Tool not being called | Make tool description more specific in `Tool(description=...)` |
| Agent loops forever | Set `max_iter=5` in Agent config |
| Logs empty after run | Check `logging_tool` wrapper is applied before `Tool()` is created |
| TF-IDF fails | Ensure all texts are `str` type: `[str(x) for x in texts]` |

---

## Skill 6 — Save Trajectories to CSV

**When to use:** After an agent run, persist logs to disk.

```python
import pandas as pd

def save_logs(logs, path="data/trajectories/logs.csv"):
    df = pd.DataFrame(logs, columns=["prompt", "tool"])
    # Append if file exists, create if not
    try:
        existing = pd.read_csv(path)
        df = pd.concat([existing, df], ignore_index=True)
    except FileNotFoundError:
        pass
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} total trajectories to {path}")
```

---

## Skill 7 — Generate Confusion Matrix Visualization

**When to use:** You want a visual for the paper or presentation.

```python
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

def plot_confusion(y_test, y_pred, labels):
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels, cmap='Blues')
    plt.xlabel('Predicted Tool')
    plt.ylabel('Actual Tool')
    plt.title('AgentLens — Tool Prediction Confusion Matrix')
    plt.tight_layout()
    plt.savefig('data/confusion_matrix.png', dpi=150)
    plt.show()
```

---

## Skill 8 — Compare Models (Baseline vs Neural Net)

**When to use:** You want to benchmark logistic regression vs a neural net for the paper.

```python
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.metrics import f1_score

models = {
    "LogisticRegression": LogisticRegression(max_iter=1000),
    "MLP": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500),
    "SVM": SVC(kernel='linear')
}

results = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    results[name] = {
        "accuracy": (preds == y_test).mean(),
        "f1_macro": f1_score(y_test, preds, average='macro')
    }

import pandas as pd
print(pd.DataFrame(results).T)
```
