# Senior Product Manager AI Agent (MVP)

Lightweight local-first MVP for a domain-expert PM assistant in D2C/B2C weight-loss subscription and telehealth products.

## Stack
- Python
- LangGraph
- OpenAI API (`gpt-5.2` only for LLM calls)
- OpenAI text embeddings (`text-embedding-3-small`)
- FAISS local vector store
- Streamlit UI

## Project Structure
- `app.py` - Streamlit chat app + debug sidebar.
- `src/pm_agent/config.py` - Environment settings.
- `src/pm_agent/llm.py` - OpenAI chat + embedding wrappers.
- `src/pm_agent/prompts.py` - System prompts and routing keywords.
- `src/pm_agent/rag.py` - Document loading, chunking, FAISS build/retrieval.
- `src/pm_agent/orchestrator.py` - LangGraph sequential orchestrator + subagents.
- `src/pm_agent/memory.py` - Conversation summary memory.
- `scripts/ingest_docs.py` - Build FAISS index from `/docs`.
- `docs/*` - Seed knowledge base content.

## Quickstart
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Configure environment:
   ```bash
   cp .env.example .env
   # set OPENAI_API_KEY
   ```
   Optional model fallback if `gpt-5.2` is unavailable for your key:
   ```bash
   # in .env
   OPENAI_MODEL=gpt-5.2
   OPENAI_FALLBACK_MODEL=gpt-5
   OPENAI_REASONING_EFFORT=high
   ```
4. Build local index:
   ```bash
   python scripts/ingest_docs.py
   ```
5. Run UI:
   ```bash
   streamlit run app.py
   ```

## Import External Articles Into KB
Use this to import curated URLs into `docs/growth` and `docs/competitors`:

```bash
python scripts/import_external_articles.py
python scripts/ingest_docs.py
```

## Notes
- Subagents are prompt-routed and called sequentially by the orchestrator.
- Subagent handoff uses a compressed shared JSON contract (`agent`, `summary`, `key_findings`, `recommendations`, `assumptions`, `compliance_flags`, optional `experiments`).
- No autonomous loops, no external DB, no enterprise infra.
- Debug sidebar shows active subagents, retrieved chunks, and token usage.
