"""Run on your machine (needs internet once to download the model) to calibrate RETRIEVAL_MIN_SCORE.

    python scripts/check_embeddings.py
Relevant questions should score clearly above unrelated ones; set RETRIEVAL_MIN_SCORE between the two groups.
"""
from app.core.config import get_settings
from app.services.embeddings import get_embedding_provider

CLAUSES = ["Pre-existing diseases are covered only after a waiting period of 36 months of continuous coverage.",
           "Room rent is capped at 1 percent of the Sum Insured per day.",
           "A co-payment of 10 percent applies to members above 60 years."]
RELEVANT = ["What is the waiting period for pre-existing diseases?", "Is room rent capped?", "What is my co-payment percentage?"]
UNRELATED = ["Give me a chocolate cake recipe", "Who won the cricket match?", "How do I reset my router?"]

p = get_embedding_provider()
docs = p.embed_documents(CLAUSES)
dot = lambda a, b: sum(x * y for x, y in zip(a, b))
print(f"model: {p.name}  current RETRIEVAL_MIN_SCORE={get_settings().retrieval_min_score}")
for title, qs in (("relevant", RELEVANT), ("unrelated", UNRELATED)):
    for q in qs:
        v = p.embed_query(q)
        print(f"{title:9} best={max(dot(v, d) for d in docs):.3f}  {q}")
