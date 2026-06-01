# Lightweight Evaluation Guide

This MVP uses lightweight qualitative evals plus mocked unit tests. The goal is not benchmark perfection; it is to verify that the assistant behaves like a credible senior PM for subscription, growth, and telehealth product questions.

## Evaluation Criteria

Score each answer from 1 to 5.

| Criterion | What Good Looks Like |
|---|---|
| Relevance | Directly answers the user's product question and stays in the D2C/B2C subscription or telehealth context. |
| Groundedness | Uses retrieved knowledge as evidence and avoids unsupported facts or invented citations. |
| Practical Value | Produces concrete recommendations, metrics, experiments, owners, and decision rules. |
| Compliance Risk | Avoids guaranteed health claims, diagnosis/treatment advice, policy-unsafe ad copy, and manipulative retention tactics. |
| Actionability | Gives a PM or growth team a realistic next step for the next 7-30 days. |

## Suggested Manual Eval Flow

1. Run the app in demo mode or with an OpenAI key.
2. Ask the prompts from `docs/demo_questions.md`.
3. Open the debug sidebar and confirm active subagents match the query.
4. Check that retrieved chunks are plausible for the question.
5. Score the final answer on the five criteria above.
6. Record weak answers and improve prompts, source docs, or routing keywords.

## Automated Checks

The repository also includes mocked tests and scripts that do not call OpenAI:

```bash
pytest
python scripts/run_evals.py
python scripts/run_stress_tests.py
```

These checks cover routing, JSON extraction/normalization, chunking, FAISS indexing with fake embeddings, memory summary refresh behavior, settings loading, and boundary/stress behavior.
