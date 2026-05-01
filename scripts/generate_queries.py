"""Generate and validate data/queries.json — 500+ labeled (query, tool) pairs.

Keeps the original 9 baseline queries at the top of the output, then
appends ~167 deduplicated queries per tool (Calculator, Search, TableSummarizer).
Run: python scripts/generate_queries.py
"""

import json
import random
from collections import Counter
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
QUERIES_PATH = ROOT / "data" / "queries.json"

# ---------- baseline 9 (preserved verbatim, in order) ----------
SEED_QUERIES = [
    {"query": "What is 25 multiplied by 48?", "tool": "Calculator"},
    {"query": "What is the square root of 144?", "tool": "Calculator"},
    {"query": "What is 15% of 200?", "tool": "Calculator"},
    {"query": "Who invented the telephone?", "tool": "Search"},
    {"query": "What is the capital of Japan?", "tool": "Search"},
    {"query": "What is machine learning?", "tool": "Search"},
    {"query": "Summarize the sales data", "tool": "TableSummarizer"},
    {"query": "What are the columns in the dataset?", "tool": "TableSummarizer"},
    {"query": "Give me the statistics of the sales table", "tool": "TableSummarizer"},
]

# ---------- Calculator pool ----------

ARITH_TEMPLATES = [
    "What is {a} plus {b}?",
    "Calculate {a} + {b}",
    "Compute the sum of {a} and {b}",
    "Add {a} and {b}",
    "Find {a} added to {b}",
    "{a} minus {b} equals what?",
    "What is {a} - {b}?",
    "Subtract {b} from {a}",
    "Compute {a} take away {b}",
    "What is {a} times {b}?",
    "Calculate {a} multiplied by {b}",
    "Find the product of {a} and {b}",
    "Multiply {a} by {b}",
    "What is {a} divided by {b}?",
    "Calculate {a} / {b}",
    "Find the quotient of {a} and {b}",
    "Divide {a} by {b}",
]

PCT_TEMPLATES = [
    "What is {p}% of {n}?",
    "Find {p} percent of {n}",
    "Calculate {p}% of {n}",
    "{p}% of {n} is what?",
    "What's {p} percent of {n}?",
    "Compute {p}% of {n}",
]

WORD_PROBLEMS = [
    "If I have {n} boxes of {m} items, how many items in total?",
    "A teacher has {m} students in each of {n} classes; how many students total?",
    "I bought {n} packs with {m} candies each — how many candies altogether?",
    "If a car travels {n} miles per hour for {h} hours, what is the total distance?",
    "If you split ${t} equally among {n} people, how much does each person get?",
    "A train covers {d} miles in {h} hours. What is its average speed in mph?",
    "A book has {p} pages and you read {r} per day. How many days to finish?",
    "There are {n} apples in a basket and {m} more are added. How many apples now?",
    "A baker makes {n} cookies per batch and bakes {b} batches. Total cookies?",
    "If a printer prints {p} pages per minute, how many pages in {m} minutes?",
    "A water tank fills at {r} gallons per minute. Volume after {m} minutes?",
    "I save ${a} per week. How much will I have after {w} weeks?",
    "A field is {l} meters long and {w} meters wide. What is its area?",
    "A box is {l} cm by {w} cm by {h} cm. What is its volume?",
]

MULTI_STEP = [
    "What is {a} squared divided by {b}?",
    "Square root of {a} plus {b}",
    "What is {a} cubed minus {b}?",
    "Compute ({a} + {b}) multiplied by {c}",
    "Calculate {a}^2 + {b}^2",
    "Find the average of {a}, {b}, and {c}",
    "What is {p}% of ({a} + {b})?",
    "Evaluate ({a} - {b}) divided by {c}",
    "What is {a} plus {b} plus {c}?",
    "Compute {a} times {b} minus {c}",
    "Find the result of {a} / {b} + {c}",
    "What is the square of {a} minus the square of {b}?",
]

REAL_WORLD = [
    "A shirt costs ${p}, discounted {d}%. What is the final price?",
    "A meal is ${p} and the tip is {t}%; what is the total bill?",
    "Sales tax is {t}% on a ${p} item. What is the final cost?",
    "A loan of ${p} at {r}% simple interest for one year. How much interest?",
    "Gas is ${p} per gallon and the tank holds {g} gallons. Total cost?",
    "An employee earns ${h}/hour for {w} hours per week. Weekly pay?",
    "Convert {km} kilometers to miles (1 km = 0.621 miles)",
    "Convert {f} degrees Fahrenheit to Celsius",
    "Convert {c} degrees Celsius to Fahrenheit",
    "A recipe for {s} servings uses {q} cups of flour. How much for {ns} servings?",
    "If {x} out of {n} students passed, what percentage passed?",
    "A car uses {g} gallons to travel {m} miles. What is the mpg?",
    "An item originally ${p} is now ${q}. What is the percent decrease?",
    "Stock went from ${a} to ${b}. What is the percent change?",
    "A {p}% tip on a ${b} bill is how much?",
    "If {n} workers finish a job in {d} days, how long for {m} workers?",
]


def gen_calculator(target=170):
    out = []
    seen = set()

    def add(q):
        if q not in seen:
            seen.add(q)
            out.append(q)

    for tmpl in ARITH_TEMPLATES:
        for _ in range(3):
            a = random.randint(2, 999)
            b = random.randint(2, 99)
            add(tmpl.format(a=a, b=b))

    pcts = [5, 8, 10, 12, 15, 18, 20, 25, 30, 33, 40, 45, 50, 60, 65, 70, 75, 80, 90]
    for tmpl in PCT_TEMPLATES:
        for _ in range(8):
            add(tmpl.format(p=random.choice(pcts), n=random.randint(50, 2500)))

    for tmpl in WORD_PROBLEMS:
        for _ in range(3):
            add(
                tmpl.format(
                    n=random.randint(3, 25),
                    m=random.randint(4, 40),
                    h=random.randint(1, 8),
                    t=random.randint(50, 500),
                    d=random.randint(60, 600),
                    p=random.randint(120, 600),
                    r=random.randint(10, 60),
                    b=random.randint(2, 12),
                    a=random.randint(20, 200),
                    w=random.randint(4, 52),
                    l=random.randint(5, 40),
                )
            )

    for tmpl in MULTI_STEP:
        for _ in range(3):
            add(
                tmpl.format(
                    a=random.randint(3, 50),
                    b=random.randint(2, 30),
                    c=random.randint(2, 25),
                    p=random.choice(pcts),
                )
            )

    for tmpl in REAL_WORLD:
        for _ in range(3):
            add(
                tmpl.format(
                    p=random.randint(15, 800),
                    d=random.choice([10, 15, 20, 25, 30, 40, 50]),
                    t=random.choice([8, 10, 15, 18, 20, 25]),
                    r=random.choice([3, 4, 5, 6, 7, 8, 10]),
                    g=random.randint(8, 25),
                    h=random.randint(12, 60),
                    w=random.randint(20, 50),
                    km=random.randint(5, 500),
                    f=random.randint(0, 110),
                    c=random.randint(-20, 100),
                    s=random.randint(2, 8),
                    q=random.randint(1, 6),
                    ns=random.randint(10, 30),
                    x=random.randint(10, 200),
                    n=random.randint(20, 400),
                    m=random.randint(50, 600),
                    a=random.randint(20, 500),
                    b=random.randint(20, 500),
                )
            )

    random.shuffle(out)
    return out[:target]


# ---------- Search pool ----------

# Hand-curated diverse subjects to drive natural variation
SEARCH_SUBJECTS = [
    # science / nature
    ("photosynthesis", "concept"),
    ("the theory of relativity", "concept"),
    ("DNA", "concept"),
    ("black holes", "concept"),
    ("the immune system", "concept"),
    ("evolution by natural selection", "concept"),
    ("the water cycle", "concept"),
    ("plate tectonics", "concept"),
    ("nuclear fusion", "concept"),
    ("quantum entanglement", "concept"),
    ("global warming", "concept"),
    ("the periodic table", "concept"),
    # tech
    ("machine learning", "concept"),
    ("the internet", "concept"),
    ("blockchain", "concept"),
    ("artificial intelligence", "concept"),
    ("encryption", "concept"),
    ("the cloud", "concept"),
    # history / events
    ("the French Revolution", "event"),
    ("World War 2", "event"),
    ("the Cold War", "event"),
    ("the Industrial Revolution", "event"),
    ("the moon landing", "event"),
    ("the fall of the Roman Empire", "event"),
    ("the Renaissance", "event"),
    ("the Cuban Missile Crisis", "event"),
    ("the signing of the Declaration of Independence", "event"),
    ("the Great Depression", "event"),
    ("the discovery of penicillin", "event"),
    # people
    ("Marie Curie", "person"),
    ("Albert Einstein", "person"),
    ("Nelson Mandela", "person"),
    ("Leonardo da Vinci", "person"),
    ("Mahatma Gandhi", "person"),
    ("Isaac Newton", "person"),
    ("Ada Lovelace", "person"),
    ("Alan Turing", "person"),
    ("Cleopatra", "person"),
    ("Charles Darwin", "person"),
    ("Rosa Parks", "person"),
    ("Stephen Hawking", "person"),
    ("Frida Kahlo", "person"),
    ("Nikola Tesla", "person"),
    ("Martin Luther King Jr.", "person"),
    # geography
    ("the Nile River", "place"),
    ("Mount Everest", "place"),
    ("the Amazon rainforest", "place"),
    ("the Sahara Desert", "place"),
    ("Antarctica", "place"),
    ("the Great Wall of China", "place"),
    ("the Pacific Ocean", "place"),
    ("the Andes mountains", "place"),
    ("the Mariana Trench", "place"),
    ("the Mediterranean Sea", "place"),
    # countries / capitals
    ("France", "country"),
    ("Brazil", "country"),
    ("Japan", "country"),
    ("Egypt", "country"),
    ("Australia", "country"),
    ("Canada", "country"),
    ("India", "country"),
    ("Germany", "country"),
    ("South Africa", "country"),
    ("Russia", "country"),
    ("Mexico", "country"),
    ("Argentina", "country"),
    ("Italy", "country"),
    ("Norway", "country"),
    # arts / culture
    ("the Mona Lisa", "artifact"),
    ("the Eiffel Tower", "artifact"),
    ("Shakespeare's Hamlet", "artifact"),
    ("the Sistine Chapel", "artifact"),
    ("the Iliad", "artifact"),
    ("Beethoven's Ninth Symphony", "artifact"),
    # general phenomena
    ("how rainbows form", "phenomenon"),
    ("how vaccines work", "phenomenon"),
    ("how airplanes fly", "phenomenon"),
    ("how solar panels generate electricity", "phenomenon"),
    ("how the human heart works", "phenomenon"),
    ("how memory works in the brain", "phenomenon"),
    ("how lightning is formed", "phenomenon"),
    ("why the sky is blue", "phenomenon"),
    ("how black holes form", "phenomenon"),
    ("how earthquakes happen", "phenomenon"),
]

CONCEPT_TEMPLATES = [
    "What is {x}?",
    "Tell me about {x}.",
    "Define {x}.",
    "Give me an overview of {x}.",
    "Can you explain {x}?",
    "What does {x} mean?",
]
EVENT_TEMPLATES = [
    "When did {x} happen?",
    "Tell me about {x}.",
    "What was {x}?",
    "What caused {x}?",
    "Summarize {x} for me.",
    "Why is {x} historically significant?",
]
PERSON_TEMPLATES = [
    "Who is {x}?",
    "Tell me about {x}.",
    "What is {x} known for?",
    "Why is {x} famous?",
    "Give me a biography of {x}.",
    "When did {x} live?",
]
PLACE_TEMPLATES = [
    "Where is {x}?",
    "Tell me about {x}.",
    "What is special about {x}?",
    "Why is {x} famous?",
    "Describe {x}.",
]
COUNTRY_TEMPLATES = [
    "What is the capital of {x}?",
    "What language is spoken in {x}?",
    "What is the population of {x}?",
    "Tell me about {x}.",
    "What currency is used in {x}?",
    "Where is {x} located?",
]
ARTIFACT_TEMPLATES = [
    "Tell me about {x}.",
    "Who created {x}?",
    "Why is {x} significant?",
    "What is the history of {x}?",
]
PHENOMENON_TEMPLATES = [
    "Explain {x}.",
    "Tell me {x}.",
    "Describe {x}.",
    "Help me understand {x}.",
    "Could you explain {x}?",
]

KIND_TO_TEMPLATES = {
    "concept": CONCEPT_TEMPLATES,
    "event": EVENT_TEMPLATES,
    "person": PERSON_TEMPLATES,
    "place": PLACE_TEMPLATES,
    "country": COUNTRY_TEMPLATES,
    "artifact": ARTIFACT_TEMPLATES,
    "phenomenon": PHENOMENON_TEMPLATES,
}


def gen_search(target=170):
    out = []
    seen = set()
    pool = list(SEARCH_SUBJECTS)
    random.shuffle(pool)

    for subject, kind in pool:
        for tmpl in KIND_TO_TEMPLATES[kind]:
            q = tmpl.format(x=subject)
            if q not in seen:
                seen.add(q)
                out.append(q)
            if len(out) >= target:
                return out

    # If still short, cycle pool with second-pass templates
    return out[:target]


# ---------- TableSummarizer pool ----------

# Sales CSV columns: date, product, region, units_sold, revenue
NUMERIC_COLS = ["revenue", "units_sold"]
CATEGORICAL_COLS = ["region", "product", "date"]

STAT_OPS = ["average", "mean", "median", "max", "min", "total", "sum", "standard deviation", "range"]
COL_PHRASES = {
    "revenue": ["revenue", "sales revenue", "the revenue column", "earnings"],
    "units_sold": ["units sold", "the units_sold column", "unit sales", "the number of units sold"],
}

OVERVIEW_TEMPLATES = [
    "Summarize the sales data.",
    "Describe the dataset.",
    "Show me a summary of the sales table.",
    "Give me the statistics of the dataset.",
    "What does the sales dataset look like?",
    "Run a summary on the data.",
    "Print the data summary.",
    "Show describe() output for the table.",
    "Give me an overview of the data.",
    "Describe the sales CSV.",
    "Show summary statistics for the sales data.",
    "I want to see the data summary.",
    "Show me a quick look at the data.",
    "Give me a description of the dataset.",
    "What's in this dataset?",
]

COLUMN_TEMPLATES = [
    "What columns does the table have?",
    "List the columns in the dataset.",
    "Which columns are in the data?",
    "Show me the column names.",
    "What fields are in the sales CSV?",
    "Print the dataset columns.",
    "What is the schema of the table?",
    "Give me the column list.",
    "What columns are present in the dataset?",
    "Show me the headers of the data.",
]

ROW_TEMPLATES = [
    "How many records are in the dataset?",
    "How many rows does the table have?",
    "What is the size of the data?",
    "How big is the sales dataset?",
    "Count the rows in the table.",
    "Tell me the number of records.",
    "How many entries are in the data?",
    "What is the row count?",
    "Show me the dataset size.",
]

MISSING_TEMPLATES = [
    "Are there any missing values in the dataset?",
    "Are there any nulls in the data?",
    "Check for missing data in the table.",
    "Does the dataset contain NaN values?",
    "Tell me if any rows have missing fields.",
    "How many missing values are in the data?",
    "Are there any empty cells in the dataset?",
    "Run a missing-values check on the table.",
]

HEAD_TEMPLATES = [
    "Show me the first few rows of the data.",
    "Print the head of the dataset.",
    "Give me a preview of the table.",
    "Show the first 5 rows of the sales data.",
    "Display the top of the dataset.",
    "Let me see some sample rows from the table.",
    "Show me the head of the sales CSV.",
]

STATCOL_TEMPLATES = [
    "What is the {op} {col} in the dataset?",
    "Calculate the {op} of {col}.",
    "Compute the {op} {col}.",
    "What is the {op} of the {col} column?",
    "Show me the {op} {col} from the data.",
    "Find the {op} of {col} in the table.",
    "Give me the {op} {col}.",
    "What's the {op} {col}?",
]

GROUPBY_TEMPLATES = [
    "Which {dim} has the highest {col}?",
    "Which {dim} has the lowest {col}?",
    "Show the top {dim} by {col}.",
    "Which {dim} sold the most {col}?",
    "What is the total {col} per {dim}?",
    "Break down {col} by {dim}.",
    "Group the data by {dim} and show {col} totals.",
    "Compare {col} across {dim} values.",
    "What is the average {col} for each {dim}?",
]

AGG_TEMPLATES = [
    "What is the total {col}?",
    "What is the grand total of {col}?",
    "Sum up {col} across the dataset.",
    "Add up the {col} column.",
    "What is the cumulative {col}?",
]


def gen_summarizer(target=170):
    out = []
    seen = set()

    def add(q):
        if q not in seen:
            seen.add(q)
            out.append(q)

    for q in OVERVIEW_TEMPLATES + COLUMN_TEMPLATES + ROW_TEMPLATES + MISSING_TEMPLATES + HEAD_TEMPLATES:
        add(q)

    for tmpl in STATCOL_TEMPLATES:
        for col_key, phrasings in COL_PHRASES.items():
            for col_phrase in phrasings:
                for op in STAT_OPS:
                    add(tmpl.format(op=op, col=col_phrase))
                    if len(out) >= target:
                        return out[:target]

    for tmpl in GROUPBY_TEMPLATES:
        for dim in CATEGORICAL_COLS:
            for col_key, phrasings in COL_PHRASES.items():
                add(tmpl.format(dim=dim, col=phrasings[0]))

    for tmpl in AGG_TEMPLATES:
        for col_key, phrasings in COL_PHRASES.items():
            for col_phrase in phrasings:
                add(tmpl.format(col=col_phrase))

    return out[:target]


# ---------- assemble + validate ----------

def main():
    calc_qs = gen_calculator(170)
    search_qs = gen_search(170)
    summ_qs = gen_summarizer(170)

    seed_strings = {q["query"] for q in SEED_QUERIES}

    def labeled(qs, tool):
        return [{"query": q, "tool": tool} for q in qs if q not in seed_strings]

    full = list(SEED_QUERIES)
    full += labeled(calc_qs, "Calculator")
    full += labeled(search_qs, "Search")
    full += labeled(summ_qs, "TableSummarizer")

    # global dedupe just in case (preserve order)
    seen = set()
    deduped = []
    for entry in full:
        if entry["query"] in seen:
            continue
        seen.add(entry["query"])
        deduped.append(entry)

    QUERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUERIES_PATH.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # validation report
    counts = Counter(e["tool"] for e in deduped)
    queries_only = [e["query"] for e in deduped]
    dupes = [q for q, c in Counter(queries_only).items() if c > 1]

    print(f"Wrote {QUERIES_PATH} with {len(deduped)} entries.")
    print("Per-tool counts:")
    for t, c in sorted(counts.items()):
        print(f"  {t}: {c}")
    print(f"Duplicates: {len(dupes)}")
    if dupes:
        for d in dupes[:5]:
            print(f"  - {d!r}")

    assert len(deduped) >= 500, f"need ≥500 entries, got {len(deduped)}"
    for tool, c in counts.items():
        assert c >= 160, f"tool {tool} has only {c} entries (need ≥160)"
    assert not dupes, f"duplicates found: {dupes[:3]}"
    print("Validation passed.")


if __name__ == "__main__":
    main()
