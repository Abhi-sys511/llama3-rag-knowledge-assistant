from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import PromptTemplate
import os

PERSIST_DIR = "./knowledge_db"

embeddings = OllamaEmbeddings(model="llama3")
llm_grader = ChatOllama(model="llama3", temperature=0)

grader_prompt = PromptTemplate(
    template="""You are a grader assessing relevance of a retrieved document to a user question.
Here is the retrieved document context:
{context}

Here is the user question:
{question}

If the document contains keywords or semantic meaning related to the user question, grade it as relevant.

Give a binary score 'yes' or 'no'.

Answer only 'yes' or 'no'.""",
    input_variables=["context", "question"],
)

def filter_relevant_docs(query, docs):
    filtered_docs = []
    chain = grader_prompt | llm_grader

    for doc in docs:
        score = chain.invoke(
            {"question": query, "context": doc.page_content}
        ).content.strip().lower()

        if "yes" in score:
            filtered_docs.append(doc)

    return filtered_docs


def load_vectorstore():
    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )


def ingest_pdf(pdf_path, chunk_size=1000, chunk_overlap=200):

    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    docs = text_splitter.split_documents(documents)

    vectorstore = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=PERSIST_DIR
    )

    vectorstore.persist()

    return f"Indexed {len(docs)} chunks from {os.path.basename(pdf_path)}."


def ingest_docs_folder(folder_path="docs", chunk_size=1000, chunk_overlap=200):

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return "Created 'docs' folder. Add PDFs there."

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

    if not pdf_files:
        return "No PDFs found in 'docs' folder."

    total_chunks = 0

    for pdf in pdf_files:

        pdf_path = os.path.join(folder_path, pdf)

        try:

            loader = PyPDFLoader(pdf_path)
            documents = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            docs = text_splitter.split_documents(documents)

            vectorstore = Chroma.from_documents(
                docs,
                embeddings,
                persist_directory=PERSIST_DIR
            )

            vectorstore.persist()

            total_chunks += len(docs)

        except Exception as e:
            print(f"Error loading {pdf}: {e}")

    return f"Indexed {total_chunks} chunks from {len(pdf_files)} PDFs."


def retrieve_context(query, k=4):

    vectorstore = load_vectorstore()

    db_data = vectorstore.get()

    if not db_data or not db_data.get("documents"):
        return "", []

    # 1️⃣ Vector search
    vector_docs = vectorstore.similarity_search(query, k=k)

    # 2️⃣ BM25 search
    bm25_retriever = BM25Retriever.from_texts(
        db_data["documents"],
        metadatas=db_data["metadatas"]
    )

    bm25_retriever.k = k
    bm25_docs = bm25_retriever.invoke(query)

    # 3️⃣ Merge results
    merged_docs = list({doc.page_content: doc for doc in vector_docs + bm25_docs}.values())

    # 4️⃣ Filter with LLM grader
    relevant_docs = filter_relevant_docs(query, merged_docs)

    if not relevant_docs:
        return "", []

    context = "\n\n".join(
        [
            f"[Source: {os.path.basename(doc.metadata.get('source','Unknown'))}, Page: {doc.metadata.get('page','N/A')}]\n{doc.page_content}"
            for doc in relevant_docs[:k]
        ]
    )

    return context, relevant_docs[:k]