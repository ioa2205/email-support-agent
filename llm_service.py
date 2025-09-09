import os
import re
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from transformers import pipeline
from langchain_community.vectorstores import FAISS

# --- Global variables for models to avoid reloading ---
_categorizer = None
_rag_retriever = None
_llm_qa = None

def _initialize_models():
    """Initializes all AI models on first use."""
    global _categorizer, _rag_retriever, _llm_qa

    if _categorizer is None:
        print("Loading categorization model...")
        _categorizer = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
    
    if _rag_retriever is None:
        print("Loading RAG embedding model and building vector store...")
        # Create knowledge base from faq.txt
        with open("knowledge_base/faq.txt", "r") as f:
            faq_text = f.read()
        
        # Split text into question-answer pairs
        qa_pairs = re.split(r'\n(?=Q:)', faq_text.strip())
        documents = []
        for pair in qa_pairs:
            if pair.strip():
                parts = pair.strip().split('\nA: ')
                question = parts[0][3:] # Remove "Q: "
                answer = parts[1]
                # Create a LangChain document
                doc = Document(page_content=answer, metadata={"source": "faq.txt", "question": question})
                documents.append(doc)
        
        # Load embeddings model and create FAISS vector store
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(documents, embeddings)
        _rag_retriever = vector_store.as_retriever()

    if _llm_qa is None:
        print("Loading Question-Answering model...")
        _llm_qa = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

def categorize_email(email_body: str) -> str:
    """Categorizes the email using a zero-shot classification model."""
    _initialize_models()
    
    candidate_labels = ["Question", "Refund Request", "Other"]
    result = _categorizer(email_body[:512], candidate_labels)
    
    # Simple logic to map the highest score to our categories
    top_label = result['labels'][0]
    if "Refund" in top_label:
        return "Refund"
    elif "Question" in top_label:
        return "Question"
    else:
        return "Other"

from typing import Optional

def get_rag_answer(question: str) -> Optional[str]:
    """Retrieves context from vector store and generates an answer."""
    _initialize_models()
    
    # 1. Retrieve relevant documents from the vector store
    docs = _rag_retriever.get_relevant_documents(question)
    
    if not docs:
        return None # No relevant information found
        
    context = " ".join([doc.page_content for doc in docs])
    
    truncated_question = question[:1000]
    
    result = _llm_qa(question=truncated_question, context=context) # Use the truncated question

    # Check if the answer is confident enough
    if result['score'] > 0.3: # Confidence threshold
        return result['answer']
    else:
        return None

def assess_importance(email_body: str) -> int:
    """A simple heuristic to assess importance for 'Other' emails."""
    body_lower = email_body.lower()
    if "urgent" in body_lower or "asap" in body_lower or "complaint" in body_lower:
        return 5
    if "help" in body_lower or "issue" in body_lower:
        return 4
    if "feedback" in body_lower or "suggestion" in body_lower:
        return 3
    if "spam" in body_lower or "subscribe" in body_lower:
        return 1
    return 2 # Default importance