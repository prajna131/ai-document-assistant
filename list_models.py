"""
list_models.py
--------------
Prints every Gemini model your API key can access, and what each one supports.
Run once with:  python list_models.py

Use this to pick the correct names for LLM_MODEL and EMBEDDING_MODEL in config.py:
  - For LLM_MODEL       -> pick a model whose methods include 'generateContent'
  - For EMBEDDING_MODEL -> pick a model whose methods include 'embedContent'
"""

import config  # noqa: F401  (imported first so truststore + API key load)
import google.generativeai as genai

genai.configure(api_key=config.GOOGLE_API_KEY, transport="rest")

print("\n================ AVAILABLE MODELS ================\n")

embedding_models = []
chat_models = []

for m in genai.list_models():
    methods = list(m.supported_generation_methods)
    print(f"{m.name}")
    print(f"    supports: {methods}")
    if "embedContent" in methods:
        embedding_models.append(m.name)
    if "generateContent" in methods:
        chat_models.append(m.name)

print("\n================ SUMMARY ================\n")
print("EMBEDDING models (use one of these for EMBEDDING_MODEL):")
for name in embedding_models:
    print(f"    {name}")

print("\nCHAT/LLM models (use one of these for LLM_MODEL):")
for name in chat_models:
    print(f"    {name}")
print()
