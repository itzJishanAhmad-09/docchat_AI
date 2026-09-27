import os
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import JinaEmbeddings
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session
from .models import Document, Chunk

# Load environment variables from .env
load_dotenv()

# ─── Embedding Model (Jina AI) ─────────────────────────────────
embeddings_model = JinaEmbeddings(
    jina_api_key=os.getenv("JINA_API_KEY"),
    model_name="jina-embeddings-v3",
)

# ─── Chat Model (Groq) ─────────────────────────────────────────
# NOTE: llama-3.3-70b-versatile was retired on Aug 16, 2026.
# Using openai/gpt-oss-120b which is free on Groq's developer tier.
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

def process_pdf(file_path: str, filename: str, db: Session):
    """Extract text from a PDF, chunk it, embed each chunk, and store in Postgres."""
    # 1. Create Document record
    doc = Document(filename=filename)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 2. Extract text from all pages
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    # 3. Split into overlapping chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_text(text)

    # 4. Embed each chunk and store it
    for chunk_text in chunks:
        embedding = embeddings_model.embed_query(chunk_text)
        chunk = Chunk(
            document_id=doc.id,
            content=chunk_text,
            embedding=embedding,
        )
        db.add(chunk)

    db.commit()

    # 5. Clean up the temp file
    os.remove(file_path)
    return doc

def get_answer(question: str, document_id: int, db: Session):
    """Retrieve relevant chunks via vector similarity, then ask the LLM."""
    # 1. Embed the user's question
    query_embedding = embeddings_model.embed_query(question)

    # 2. Vector similarity search (top 3 closest chunks)
    results = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(3)
        .all()
    )

    # 3. Build context from retrieved chunks
    context = "\n\n".join([c.content for c in results])
    sources = [c.content for c in results]

    # 4. Build prompt and call the LLM
    prompt = f"""Answer the question based ONLY on the following context.
If the answer isn't in the context, say "I don't know based on the document."

Context:
{context}

Question: {question}
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content,
        "sources": sources,
    }