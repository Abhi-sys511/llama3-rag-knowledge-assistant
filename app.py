import streamlit as st
import time
from langchain_ollama import ChatOllama
from rag_engine import retrieve_context, ingest_pdf, ingest_docs_folder
from evaluate import evaluate_response
import os

st.set_page_config(page_title="RAG AI Research Assistant", page_icon="🚀")

# Initialize LLM
@st.cache_resource
def get_llm():
    return ChatOllama(model="llama3", temperature=0.5)

llm = get_llm()

st.title("🚀 RAG AI Research Assistant")
st.write("Features: Normal AI + Multi-PDF RAG + Streaming + Evaluation")

# Sidebar for PDF loading
with st.sidebar:
    st.header("📄 Knowledge Base")
    st.write("Upload a PDF to index it into the vector database.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file is not None:
        if st.button("Ingest PDF"):
            with st.spinner("Processing PDF..."):
                # Save to a temp folder first
                temp_dir = "docs"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Ingest
                result = ingest_pdf(temp_path)
                st.success(result)

    st.divider()
    if st.button("Load All PDFs from 'docs/'"):
        with st.spinner("Loading docs folder..."):
            res = ingest_docs_folder()
            st.success(res)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask something..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("🔎 Retrieving context..."):
            context, docs = retrieve_context(prompt)
        
        full_response = ""
        
        if context.strip():
            system_prompt = f"""
You are an intelligent research assistant.

If the context contains useful information, use it to answer the user's question.
When you use information from the context, you MUST cite the source and page number in your answer (e.g., "[Source: document.pdf, Page: 5]").
If the context does not help answer the question, answer normally.

Context:
{context}

Question:
{prompt}

Provide a clear answer with citations where appropriate.
"""
            # Stream the response
            for chunk in llm.stream(system_prompt):
                full_response += chunk.content
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
            # Show sources expander
            with st.expander("📚 Retrieved Sources & Evaluation"):
                for doc in docs:
                    st.write(f"- Source: {os.path.basename(doc.metadata.get('source', 'Unknown'))}, Page: {doc.metadata.get('page', 'N/A')}")
                
                st.write("\n**Evaluation Scores:**")
                with st.spinner("Grading response..."):
                    eval_scores = evaluate_response(prompt, context, full_response)
                st.write(f"- Faithfulness: {eval_scores['faithfulness']}")
                st.write(f"- Answer Relevance: {eval_scores['answer_relevance']}")
        else:
            for chunk in llm.stream(prompt):
                full_response += chunk.content
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
