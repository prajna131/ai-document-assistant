"""
app.py
------
The web app (UI) built with Streamlit.

Run it with:   streamlit run app.py

Features:
  - Upload PDF / TXT files in the sidebar
  - Process them into the vector database
  - Chat with your documents (with conversation memory)
  - See the exact source snippets each answer came from
"""

import os
import streamlit as st

import config
from rag_engine import RAGEngine

# --- Page setup ---
st.set_page_config(
    page_title="AI Document Assistant",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource
def get_engine() -> RAGEngine:
    """Create the RAG engine once and reuse it (cached across reruns)."""
    return RAGEngine()


def main():
    st.title("📚 AI Document Assistant")
    st.caption("Chat with your documents — powered by RAG + Google Gemini")

    # Stop early if the API key is missing
    if not config.GOOGLE_API_KEY:
        st.error(
            "⚠️ No GOOGLE_API_KEY found.\n\n"
            "Create a file named `.env` in the project folder and add:\n\n"
            "`GOOGLE_API_KEY=your_key_here`"
        )
        st.stop()

    engine = get_engine()

    # ------------------------------------------------------------- SIDEBAR
    with st.sidebar:
        st.header("📤 Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload PDF or TXT files",
            type=["pdf", "txt"],
            accept_multiple_files=True,
        )

        if st.button("⚙️ Process Documents", type="primary"):
            if not uploaded_files:
                st.warning("Please upload at least one file first.")
            else:
                with st.spinner("Reading, chunking, and embedding..."):
                    total_chunks = 0
                    for file in uploaded_files:
                        save_path = os.path.join(config.UPLOAD_DIR, file.name)
                        with open(save_path, "wb") as f:
                            f.write(file.getbuffer())
                        total_chunks += engine.ingest_file(save_path)
                st.success(f"✅ Done! Added {total_chunks} chunks to the knowledge base.")

        st.divider()
        # Show which documents are currently loaded in the knowledge base
        loaded = engine.list_sources()
        if loaded:
            st.subheader("📚 Loaded documents")
            for name in loaded:
                st.markdown(f"- {name}")
        else:
            st.info("No documents loaded yet.")

        st.divider()
        if st.button("🗑️ Clear knowledge base"):
            engine.clear()
            st.cache_resource.clear()          # force a fresh engine next run
            st.session_state.messages = []
            st.success("Knowledge base cleared.")
            st.rerun()

        st.divider()
        st.markdown(
            "**How it works**\n\n"
            "1. Upload docs → 2. They're split into chunks → "
            "3. Chunks become vectors → 4. Your question finds the closest "
            "chunks → 5. Gemini answers using them."
        )

    # -------------------------------------------------------------- CHAT AREA
    # Initialize chat history in the session
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Show past messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input box
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Show the user's message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and show the assistant's answer
        with st.chat_message("assistant"):
            if not engine.has_documents():
                answer = "📄 Please upload and process a document first."
                st.markdown(answer)
            else:
                with st.spinner("Thinking..."):
                    # Pass all previous messages (except the current one) as history
                    history = [
                        (m["role"], m["content"])
                        for m in st.session_state.messages[:-1]
                    ]
                    answer, sources = engine.query(prompt, history)

                st.markdown(answer)

                # Show the source snippets that grounded the answer
                if sources:
                    with st.expander("📎 Sources used for this answer"):
                        for i, doc in enumerate(sources, start=1):
                            src = doc.metadata.get("source_file", "unknown")
                            page = doc.metadata.get("page", "?")
                            st.markdown(f"**{i}. {src}** (page {page})")
                            st.caption(doc.page_content[:300] + "...")

            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )


if __name__ == "__main__":
    main()
