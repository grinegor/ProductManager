from __future__ import annotations

import sys
import time
from pathlib import Path
import html
import re

import streamlit as st
from openai import NotFoundError

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from pm_agent.config import load_settings
from pm_agent.llm import OpenAIClient
from pm_agent.memory import ConversationMemory
from pm_agent.orchestrator import PMOrchestrator
from pm_agent.rag import RAGStore


def normalize_assistant_markdown(text: str) -> str:
    # Keep headings/lists/tables, but aggressively remove broken emphasis tokens.
    cleaned = text.replace("\r\n", "\n")
    cleaned = cleaned.replace("`", "")
    cleaned = cleaned.replace("\\*", "")

    normalized_lines: list[str] = []
    for line in cleaned.split("\n"):
        current = line
        # Preserve markdown bullet lines, but normalize marker.
        current = re.sub(r"^\s*\*\s+", "- ", current)
        # Remove broken emphasis markers that frequently leak from model outputs.
        current = current.replace("**", "")
        current = current.replace("*", "")
        current = current.replace("__", "")
        current = re.sub(r"(?<!\w)_(?!\w)", "", current)
        normalized_lines.append(current)

    cleaned = "\n".join(normalized_lines)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def preview_plain_text(text: str) -> str:
    cleaned = normalize_assistant_markdown(text)
    cleaned = cleaned.replace("**", "").replace("*", "")
    cleaned = cleaned.replace("__", "").replace("_", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def render_assistant_plain(text: str, container) -> None:
    safe = html.escape(normalize_assistant_markdown(text)).replace("\n", "<br>")
    container.markdown(
        f"<div style='line-height:1.65; font-size:1.05rem; color:rgba(255,255,255,0.92);'>{safe}</div>",
        unsafe_allow_html=True,
    )


@st.cache_resource
def build_runtime() -> tuple:
    settings = load_settings()
    llm_client = OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.embedding_model,
        fallback_model=settings.fallback_openai_model,
        reasoning_effort=settings.openai_reasoning_effort,
    )
    rag_store = RAGStore(settings, llm_client)
    orchestrator = PMOrchestrator(settings, llm_client, rag_store)
    memory = ConversationMemory(llm_client=llm_client, refresh_after_messages=8)
    return settings, rag_store, orchestrator, memory


def render_debug_panel(debug_data: dict, memory_summary: str, has_index: bool) -> None:
    st.sidebar.header("Debug Panel")
    st.sidebar.write(f"FAISS index loaded: {'yes' if has_index else 'no'}")

    if not debug_data:
        st.sidebar.info("No debug data yet. Ask a question to populate diagnostics.")
        return

    active_subagents = debug_data.get("active_subagents", [])
    token_usage = debug_data.get("token_usage", {})
    retrieved_chunks = debug_data.get("retrieved_chunks", [])

    st.sidebar.subheader("Active Subagents")
    st.sidebar.write(", ".join(active_subagents) if active_subagents else "none")

    st.sidebar.subheader("Token Usage")
    st.sidebar.json(token_usage)

    st.sidebar.subheader("Memory Summary")
    st.sidebar.caption(memory_summary or "(empty)")

    st.sidebar.subheader("Retrieved Chunks")
    if not retrieved_chunks:
        st.sidebar.caption("No chunks retrieved for last answer.")
    else:
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk.get("source", "unknown")
            score = chunk.get("score", 0.0)
            snippet = chunk.get("text", "")[:220]
            st.sidebar.markdown(f"**{idx}.** `{source}` (score: {score:.3f})")
            st.sidebar.caption(snippet)

    with st.sidebar.expander("Subagent Outputs"):
        subagent_outputs = debug_data.get("subagent_outputs", {})
        st.markdown("**GrowthAgent**")
        st.write(subagent_outputs.get("growth", ""))
        st.markdown("**SubscriptionAgent**")
        st.write(subagent_outputs.get("subscription", ""))
        st.markdown("**ComplianceAgent**")
        st.write(subagent_outputs.get("compliance", ""))


def stream_text(text: str, delay: float = 0.01) -> None:
    placeholder = st.empty()
    rendered = ""
    for word in text.split(" "):
        rendered += word + " "
        placeholder.write(preview_plain_text(rendered.strip()))
        time.sleep(delay)
    render_assistant_plain(text, placeholder)


def main() -> None:
    st.set_page_config(page_title="Senior PM AI Agent", layout="wide")
    st.markdown(
        """
        <style>
        /* Assistant avatar/icon background */
        [data-testid="stChatMessageAvatarAssistant"] {
            background-color: #1e90ff !important;
            color: #ffffff !important;
        }
        /* User avatar/icon background */
        [data-testid="stChatMessageAvatarUser"] {
            background-color: #39ff14 !important;
            color: #06120a !important;
        }
        /* Chat input bar (container + textarea) */
        [data-testid="stChatInput"] {
            border: none !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            outline: none !important;
        }
        [data-testid="stChatInput"] textarea {
            caret-color: #39ff14 !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        [data-testid="stChatInput"]:focus-within {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        [data-testid="stChatInput"] textarea:focus,
        [data-testid="stChatInput"] textarea:focus-visible {
            outline: none !important;
            border: none !important;
            box-shadow: none !important;
        }
        /* Streamlit internal input container states (typing/active) */
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] > div:focus-within,
        [data-testid="stChatInput"] [data-baseweb="base-input"],
        [data-testid="stChatInput"] [data-baseweb="base-input"]:focus-within,
        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="textarea"]:focus-within {
            border-color: #39ff14 !important;
            box-shadow: none !important;
            outline: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Senior Product Manager AI Agent (Weight Loss / Telehealth)")
    st.caption("MVP stack: LangGraph + GPT-5.2 + OpenAI Small Embeddings + FAISS + Streamlit")

    settings, rag_store, orchestrator, memory = build_runtime()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory_summary" not in st.session_state:
        st.session_state.memory_summary = ""
    if "debug_data" not in st.session_state:
        st.session_state.debug_data = {}

    with st.sidebar:
        st.header("Knowledge Base")
        st.write(f"Primary LLM: `{settings.openai_model}`")
        st.write(
            f"Fallback LLM: `{settings.fallback_openai_model or '(disabled)'}`"
        )
        st.write(f"Reasoning effort: `{settings.openai_reasoning_effort}`")
        st.write(f"Active LLM: `{orchestrator.llm_client.active_model}`")
        st.write(f"Docs path: `{settings.docs_dir}`")
        st.write(f"Index path: `{settings.faiss_index_path}`")
        if st.button("Rebuild FAISS Index", use_container_width=True):
            with st.spinner("Building embeddings + FAISS index..."):
                stats = rag_store.build_from_docs()
            st.success(
                f"Indexed {stats['documents']} docs into {stats['chunks']} chunks."
            )

    render_debug_panel(
        debug_data=st.session_state.debug_data,
        memory_summary=st.session_state.memory_summary,
        has_index=rag_store.has_index(),
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_assistant_plain(message["content"], st)
            else:
                st.markdown(message["content"])

    user_input = st.chat_input("Ask about funnel, retention, CAC/LTV, pricing, or compliance...")
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    history_for_context = st.session_state.messages[-settings.max_history_messages :]

    with st.chat_message("assistant"):
        try:
            with st.spinner("Running orchestrator + subagents..."):
                result = orchestrator.run(
                    user_query=user_input,
                    chat_history=history_for_context,
                    memory_summary=st.session_state.memory_summary,
                )
            stream_text(result.final_answer, delay=0.01)
        except NotFoundError as exc:
            st.error(
                "Model is not available for this API key. "
                "Set OPENAI_MODEL to a model you have access to, or configure OPENAI_FALLBACK_MODEL."
            )
            st.exception(exc)
            return

    st.session_state.messages.append({"role": "assistant", "content": result.final_answer})

    updated_summary, summary_usage = memory.maybe_refresh_summary(
        history=st.session_state.messages,
        previous_summary=st.session_state.memory_summary,
    )
    st.session_state.memory_summary = updated_summary

    token_usage = dict(result.token_usage)
    token_usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0) + summary_usage.prompt_tokens
    token_usage["completion_tokens"] = token_usage.get("completion_tokens", 0) + summary_usage.completion_tokens
    token_usage["total_tokens"] = token_usage.get("total_tokens", 0) + summary_usage.total_tokens

    st.session_state.debug_data = {
        "active_subagents": result.active_subagents,
        "retrieved_chunks": [
            {
                "source": c.source,
                "score": c.score,
                "text": c.text,
            }
            for c in result.retrieved_chunks
        ],
        "token_usage": token_usage,
        "subagent_outputs": result.subagent_outputs,
    }


if __name__ == "__main__":
    main()
