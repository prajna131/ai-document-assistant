"""
rag_engine.py
-------------
The heart of the project: the RAG (Retrieval-Augmented Generation) engine.

It does two big jobs:
  1) INGESTION  -> read a document, split it into chunks, turn chunks into
                   embeddings (vectors), and store them in a vector database.
  2) QUERYING   -> take a user question, find the most relevant chunks,
                   and ask the LLM to answer using ONLY those chunks.
"""

import os
import time

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
try:
    # Newer LangChain: text splitters live in their own package
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Older LangChain fallback
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

import config


class GeminiEmbeddings(Embeddings):
    """A small, dependency-light embeddings class for Google Gemini.

    We write our own instead of using LangChain's built-in one because the
    installed version calls the 'batchEmbedContents' API method, which the newer
    'gemini-embedding-001' model does not support. This class uses the supported
    'embedContent' method (one text at a time), which works reliably.
    """

    def __init__(self, model: str, api_key: str):
        # transport="rest" + truststore (loaded in config) => works behind
        # networks that inspect SSL. Configured once, globally.
        genai.configure(api_key=api_key, transport="rest")
        self.model = model

    def _embed_one(self, text: str, task_type: str, retries: int = 4):
        """Embed a single text, retrying on transient network errors."""
        last_error = None
        for attempt in range(retries):
            try:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type=task_type,
                )
                return result["embedding"]
            except Exception as e:  # e.g. dropped connection, rate limit
                last_error = e
                # Wait a bit longer after each failure (2s, 4s, 6s, ...)
                time.sleep(2 * (attempt + 1))
        # All retries failed
        raise last_error

    def embed_documents(self, texts):
        """Embed a list of document chunks (used during ingestion)."""
        return [self._embed_one(t, "retrieval_document") for t in texts]

    def embed_query(self, text):
        """Embed a single user question (used during search)."""
        return self._embed_one(text, "retrieval_query")


class RAGEngine:
    """Wraps the whole RAG pipeline in one easy-to-use class."""

    def __init__(self):
        # 1) Embeddings model: turns text into vectors (lists of numbers).
        #    Our custom class uses REST + the supported 'embedContent' method.
        self.embeddings = GeminiEmbeddings(
            model=config.EMBEDDING_MODEL,
            api_key=config.GOOGLE_API_KEY,
        )

        # 2) The LLM: the "brain" that writes the final answers
        self.llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.2,  # low = factual & focused, high = creative
            transport="rest",
        )

        # 3) Vector database: stores embeddings and lets us search by meaning
        self.vectorstore = Chroma(
            persist_directory=config.CHROMA_DIR,
            embedding_function=self.embeddings,
        )

        # 4) Text splitter: cuts documents into overlapping chunks
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )

    # ---------------------------------------------------------------- INGESTION
    def ingest_file(self, file_path: str) -> int:
        """Read one file, chunk it, embed it, and store it. Returns #chunks added."""
        ext = os.path.splitext(file_path)[1].lower()

        # Pick the right loader based on file type
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()               # raw text (per page for PDFs)
        chunks = self.splitter.split_documents(documents)  # small overlapping pieces

        # Drop empty / whitespace-only chunks (e.g. blank or image-only PDF
        # pages). These would create empty embeddings, which ChromaDB rejects.
        chunks = [c for c in chunks if c.page_content and c.page_content.strip()]

        # Tag each chunk with its source filename (used for citations later)
        for chunk in chunks:
            chunk.metadata["source_file"] = os.path.basename(file_path)

        if not chunks:
            return 0

        # Embed + store everything in the vector DB
        self.vectorstore.add_documents(chunks)
        return len(chunks)

    # ------------------------------------------------------------------- QUERY
    def _build_chain(self):
        """Builds the RAG chain: retrieve relevant chunks -> answer with the LLM.

        NOTE: To conserve the Gemini free-tier quota, this uses only ONE LLM
        call per question. We retrieve using the raw question (no extra
        "rephrase" LLM call), but still pass the chat history to the answer
        model so it understands follow-up context.
        """
        # MMR (Maximal Marginal Relevance) picks chunks that are both relevant
        # AND diverse, so answers can draw from MULTIPLE documents instead of
        # only the single most dominant one.
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": config.TOP_K,
                "fetch_k": config.FETCH_K,
                "lambda_mult": config.MMR_LAMBDA,
            },
        )

        # Answer the question using ONLY the retrieved context. The chat history
        # is included so the model can resolve follow-up questions on its own.
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a helpful assistant that answers questions using ONLY the "
             "context below, which comes from the user's own documents. "
             "If the answer is not in the context, honestly say you don't know. "
             "Be clear, concise, and accurate.\n\n"
             "Context:\n{context}"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)

        # Plain retriever (no LLM rephrasing) => 1 LLM call total per question.
        return create_retrieval_chain(retriever, question_answer_chain)

    def query(self, question: str, chat_history=None):
        """Ask a question. Returns (answer_text, list_of_source_documents)."""
        chat_history = chat_history or []

        # Convert simple (role, text) tuples into LangChain message objects
        lc_history = []
        for role, content in chat_history:
            if role == "user":
                lc_history.append(HumanMessage(content=content))
            else:
                lc_history.append(AIMessage(content=content))

        chain = self._build_chain()
        result = chain.invoke({"input": question, "chat_history": lc_history})
        return result["answer"], result.get("context", [])

    # ------------------------------------------------------------------ HELPERS
    def has_documents(self) -> bool:
        """True if there is at least one chunk stored in the vector DB."""
        try:
            return self.vectorstore._collection.count() > 0
        except Exception:
            return False

    def list_sources(self) -> list:
        """Return the distinct source filenames currently in the knowledge base."""
        try:
            data = self.vectorstore.get(include=["metadatas"])
            files = {
                (m or {}).get("source_file")
                for m in data.get("metadatas", [])
            }
            return sorted(f for f in files if f)
        except Exception:
            return []

    def clear(self):
        """Delete everything from the knowledge base."""
        try:
            self.vectorstore.delete_collection()
        except Exception:
            pass
