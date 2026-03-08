from langchain_ollama import ChatOllama
from datetime import datetime
import json
import time
import sys
from rag_engine import ingest_pdf, retrieve_context, ingest_docs_folder
from evaluate import evaluate_response

# Initialize model
llm = ChatOllama(model="llama3", temperature=0.5)


def save_to_json(data, filename="research_output.json"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    existing_data.append(data)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4)


def stream_response(prompt):
    full_response = ""

    for chunk in llm.stream(prompt):
        token = chunk.content
        full_response += token
        sys.stdout.write(token)
        sys.stdout.flush()

    return full_response


def main():

    print("\n🚀 Research Assistant FINAL VERSION")
    print("Features: Normal AI + Multi-PDF RAG + Streaming\n")

    print("📂 Checking 'docs' folder for PDFs...")
    docs_result = ingest_docs_folder()
    print(f"   {docs_result}\n")

    print("Commands:")
    print("  /loadpdf path_to_pdf")
    print("  exit\n")

    while True:

        query = input("Ask something: ")

        if query.lower() == "exit":
            print("Goodbye 👋")
            break

        # PDF Load Command
        if query.startswith("/loadpdf "):

            path = query.replace("/loadpdf ", "").strip()

            try:
                result = ingest_pdf(path)
                print(f"\n📚 {result}\n")
            except Exception as e:
                print("❌ Error loading PDF:", e)

            continue

        try:

            print("\n🔎 Retrieving relevant documents...\n")

            context, docs = retrieve_context(query)

            # 🔹 If context is too small → ignore it
            if not context or len(context.strip()) < 50:
                context = ""

            start_time = time.time()

            print("\n📄 Answer:\n")

            # 🔹 If relevant context exists → use RAG
            if context:

                prompt = f"""
You are an intelligent research assistant.

If the context contains useful information, use it to answer the user's question.
When you use information from the context, you MUST cite the source and page number in your answer (e.g., "[Source: document.pdf, Page: 5]").
If the context does not help answer the question, answer normally.

Context:
{context}

Question:
{query}

Provide a clear answer with citations where appropriate.
"""

                answer = stream_response(prompt)

            # 🔹 Otherwise answer normally
            else:

                print("(No useful PDF context — answering normally)\n")

                answer = stream_response(query)

            end_time = time.time()
            response_time = round(end_time - start_time, 2)

            print(f"\n\n⏱ Response Time: {response_time} seconds")
            print("\n" + "-" * 60 + "\n")

            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "query": query,
                "response": answer,
                "response_time_seconds": response_time,
                "context_used": bool(context.strip()),
                "retrieved_documents": [doc.metadata.get('source', 'Unknown') for doc in docs] if context.strip() else []
            }

            print("\n📊 Evaluating response quality...")
            eval_scores = evaluate_response(query, context, answer)
            log_data["evaluation_scores"] = eval_scores
            
            print(f"   Faithfulness: {eval_scores['faithfulness']}")
            print(f"   Answer Relevance: {eval_scores['answer_relevance']}")

            save_to_json(log_data)

        except Exception as e:
            print("❌ Error:", e)


if __name__ == "__main__":
    main()