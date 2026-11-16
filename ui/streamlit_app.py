import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="FinCon Research", page_icon="📚", layout="wide")

@st.cache_resource
def get_pipeline():
    from src.generation.chain import FinConRAGPipeline
    return FinConRAGPipeline()

styles = {
    "Research Desk": ("#f6f2e9", "#fffdf8", "#292e2b", "#42665a", "Georgia, serif"),
    "Analyst Terminal": ("#111d20", "#1c2c2f", "#e5f1ed", "#70d5bd", "Arial, sans-serif"),
    "Compliance Brief": ("#f4f7fb", "#ffffff", "#172943", "#315b97", "Arial, sans-serif"),
}
names = list(styles)
requested = st.query_params.get("style", names[0])
if "style" not in st.session_state:
    st.session_state.style = requested if requested in names else names[0]
with st.sidebar:
    st.markdown("## FinCon Research")
    st.radio("Visual style", names, key="style")
    st.markdown("---")
    top_k = st.slider("Results to rerank", 1, 8, 3)
    if st.button("Run document ingestion"):
        try:
            with st.spinner("Building document indexes..."):
                from src.ingestion.run_ingestion import run_ingestion_pipeline
                run_ingestion_pipeline()
                get_pipeline.clear()
            st.success("Document ingestion complete.")
        except Exception as exc:
            st.error(f"Ingestion failed: {exc}")
    st.markdown("---")
    st.caption("Financial controlling and regulatory research")

style = st.session_state.style
st.query_params["style"] = style
bg, surface, ink, accent, heading = styles[style]
st.markdown(f"""<style>
    .stApp, [data-testid="stHeader"] {{background: {bg}; color: {ink};}}
    [data-testid="stSidebar"] {{background: {surface};}}
    .stApp h1, .stApp h2, .stApp h3 {{font-family: {heading}; color: {ink};}}
    .stApp p, .stApp label, .stApp span {{color: {ink};}}
    .stButton button[kind="primary"] {{background: {accent}; color: {bg}; border: 0;}}
    .block-container {{max-width: 1250px; padding-top: 3rem;}}
    [data-testid="stExpander"] {{background: {surface};}}
    div[data-testid="stTextInput"] input {{background: {surface}; color: {ink};}}
</style>""", unsafe_allow_html=True)

samples = [
    "What is the mandatory timeline for Form 8-K disclosure under SEC Item 1.05 for material cybersecurity incidents?",
    "What are the differences between Scope 1, Scope 2, and Scope 3 emissions under IFRS S2 in 2026?",
    "What are the eligibility criteria and turnover thresholds for EU CSRD Wave 2 compliance in 2026?",
    "What is the Basel III Endgame capital output floor percentage for risk-weighted assets?",
    "What confidence level is required for Expected Shortfall under the FRTB market risk framework?",
]

st.title("Financial research, with sources")
st.write("Search financial controlling and regulatory documents.")
selected = st.selectbox("Sample questions", ["Choose a question"] + samples, key="sample")
if selected != "Choose a question" and selected != st.session_state.get("last_sample"):
    st.session_state.question = selected
    st.session_state.last_sample = selected
with st.form("search"):
    st.text_input("Your question", key="question", placeholder="Ask about a financial standard or policy")
    submitted = st.form_submit_button("Search documents", type="primary")

if submitted:
    question = st.session_state.question.strip()
    if not question:
        st.warning("Enter a question to search the documents.")
    else:
        try:
            with st.spinner("Searching documents and preparing an answer..."):
                st.session_state.result = get_pipeline().run(query=question, top_k_rerank=top_k)
                st.session_state.is_example = False
        except Exception as exc:
            st.error(f"Search failed: {exc}")

if st.button("Show example result"):
    st.session_state.result = {
        "answer": "A material cybersecurity incident is disclosed on Form 8-K within four business days after the materiality determination. [Source: financial_regulatory_standards_2026.json]",
        "sources": ["financial_regulatory_standards_2026.json"],
        "retrieved_child_chunks": [], "context_used": "Example preview.",
    }
    st.session_state.is_example = True

result = st.session_state.get("result")
if result:
    if st.session_state.get("is_example"):
        st.info("Example result for preview. Run a search for a live answer.")
    if style == "Compliance Brief":
        st.subheader("Answer")
        st.markdown(result["answer"])
        st.subheader("Sources")
        for number, source in enumerate(result.get("sources", []), 1):
            st.write(f"{number}. {source}")
    else:
        answer_col, source_col = st.columns([2.2, 1])
        with answer_col:
            st.subheader("Answer")
            st.markdown(result["answer"])
        with source_col:
            st.subheader("Sources" if style == "Research Desk" else "Evidence")
            for source in result.get("sources", []):
                st.write(source)
            if style == "Analyst Terminal":
                for rank, chunk in enumerate(result.get("retrieved_child_chunks", []), 1):
                    st.write(f"{rank}. {chunk.get('id', '')} · score {chunk.get('rerank_score', 0):.4f}")
    entities = result.get("entities", [])
    if entities:
        st.write("Recognized entities: " + ", ".join(f"{item['text']} ({item['label']})" for item in entities))
    if result.get("expanded_query") and result.get("expanded_query") != result.get("query"):
        st.info(f"Expanded query: {result['expanded_query']}")
    with st.expander("Retrieved chunks and scores"):
        for rank, chunk in enumerate(result.get("retrieved_child_chunks", []), 1):
            st.markdown(f"**Rank {rank} · {chunk['id']}**")
            st.write(f"Rerank score: {chunk.get('rerank_score', 0):.4f} · RRF score: {chunk.get('rrf_score', 0):.4f}")
            st.write(chunk["text"])
            st.caption(f"Parent: {chunk.get('parent_id')} · Metadata: {chunk.get('metadata')}")
    with st.expander("Full parent context"):
        st.code(result.get("context_used", ""), language="markdown")
