# 📚 AI Document Assistant (RAG Chatbot)

A web application that lets you **chat with your own documents**. Upload PDFs or text files and ask questions in natural language — the app answers using **only** the content of your documents and shows the exact source snippets behind every answer.

Built with **Retrieval-Augmented Generation (RAG)**, the same architecture used by tools like ChatPDF, Perplexity, and enterprise "chat with your data" products.

---

## ✨ Features
- 📤 Upload **multiple** PDF / TXT files (sidebar shows what's loaded)
- 🔎 Semantic search over document content (not just keywords)
- 🧭 **MMR retrieval** — pulls diverse chunks so answers span *multiple* documents
- 💬 Conversational chat that remembers previous questions
- 📎 Source citations for every answer (reduces hallucinations)
- ⚡ **1 API call per question** to conserve the free-tier quota
- 🆓 Runs on Google Gemini's free tier

---

## 🧠 AI Concepts Demonstrated

| Concept | Implementation |
|---|---|
| **LLMs** | Google Gemini generates the answers |
| **RAG** | Retrieve relevant chunks, then generate a grounded answer |
| **Embeddings** | Text converted to vectors via Gemini embeddings |
| **Vector Database** | ChromaDB stores and searches embeddings |
| **Semantic Search** | Finds text by meaning, not exact words |
| **MMR Retrieval** | Maximal Marginal Relevance for diverse, multi-doc results |
| **Prompt Engineering** | Custom system prompt for grounded answers |
| **Chunking** | RecursiveCharacterTextSplitter for smart splitting |
| **Conversational Memory** | Chat history passed to the answer model |
| **LangChain** | Orchestrates the full pipeline |

---

## 🏗️ Architecture

    INGESTION:  PDF -> Extract text -> Chunk -> Embed -> Store in ChromaDB
    QUERY:      Question -> Embed -> Search ChromaDB (MMR) -> Top chunks + Question -> LLM -> Answer + Sources

---

## 🛠️ Tech Stack
- Python **3.11 or 3.12** (avoid 3.13 — see note below)
- LangChain (0.3 series)
- Google Gemini (langchain-google-genai + google-generativeai)
- ChromaDB (vector database)
- Streamlit (web UI)
- truststore (lets Python use the OS certificate store — fixes SSL on inspected networks)

---

## ⚠️ Important: Python version
Use **Python 3.11 or 3.12**. Do **not** use Python 3.13 — some dependencies (numpy, chroma-hnswlib) don't yet ship prebuilt wheels for it and would try to compile from source, which fails without a C/C++ compiler.

Create the venv with a specific version:

    py -3.11 -m venv .venv

---

## 🚀 Setup & Run

**1. Create a virtual environment & install dependencies**

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt

On networks that inspect SSL (college/office/proxy Wi-Fi), if pip fails with CERTIFICATE_VERIFY_FAILED, use:

    pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

**2. Add your free Gemini API key**

Get one at https://aistudio.google.com/app/apikey (use "Create API key in a new project" for a fresh quota). Copy `.env.example` to `.env` and paste your key:

    GOOGLE_API_KEY=your_key_here

**3. Run the app**

    python -m streamlit run app.py

Then open the URL it prints (usually http://localhost:8501).

---

## 🤖 Models
Set in `config.py`:
- `LLM_MODEL = "gemini-flash-lite-latest"` — alias that always points to the current "lite" model (highest free-tier limits, never becomes "unavailable to new users")
- `EMBEDDING_MODEL = "models/gemini-embedding-001"`

Model availability changes over time. If you hit a "model not found / not available" error, list the models your API key supports and update `config.py`:

    python list_models.py

Pick a model that supports generateContent for LLM_MODEL, and one that supports embedContent for EMBEDDING_MODEL.

---

## 📂 Project Structure

    ai-document-assistant/
    |-- app.py               # Streamlit web UI
    |-- rag_engine.py        # Core RAG logic (custom embeddings, ingestion, query)
    |-- config.py            # Settings, paths, model names, SSL fix
    |-- list_models.py       # Helper: lists the Gemini models your key supports
    |-- export_chat.py       # Generates a .docx write-up of the project
    |-- requirements.txt     # Dependencies
    |-- sample_document.txt  # Test document with made-up facts
    |-- .env.example         # Template for your API key
    |-- .env                 # Your secret API key (not committed)
    |-- .gitignore
    `-- data/                # Uploaded files + vector database (auto-created)

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| No GOOGLE_API_KEY found | Ensure the file is named exactly `.env` (not `.env.txt`) and contains your key |
| pip SSL error | Use the `--trusted-host` install command above |
| Gemini API SSL handshake failed | Handled automatically by truststore + REST transport (already in the code) |
| numpy / chroma-hnswlib build error | You're on Python 3.13 — recreate the venv with Python 3.11 or 3.12 |
| model not found / not available to new users | Run `python list_models.py` and set a current model in `config.py` |
| 429 TooManyRequests / quota exceeded | Free-tier limit reached. Wait ~24h, use gemini-flash-lite-latest, or create a key in a new Google project |
| Chroma already exists with different settings | Fully stop (Ctrl+C) and re-run `python -m streamlit run app.py` |
| Uploaded PDF adds "0 chunks" | It's a scanned/image-only PDF (no selectable text). Use a text-based PDF, or OCR it first |

---

## 📝 License
MIT — free to use for learning and portfolio purposes.
