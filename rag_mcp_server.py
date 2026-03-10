from typing import Final

import chromadb
from fastmcp import FastMCP
from llama_index.core import SimpleDirectoryReader
from llama_cloud_services import LlamaParse

from config import settings

LLAMA_CLOUD_API_KEY: Final[str] = settings.LLAMA_CLOUD_API_KEY
PERSISTENT_DIR: Final[str] = settings.PERSISTENT_DIR
DATA_DIR: Final[str] = settings.DATA_DIR
COLLECTION_NAME: Final[str] = settings.COLLECTION_NAME

mcp = FastMCP(name="RAG Server",
              instructions="A Model Context Protocol for accesing a chromadb knowledge base")

def init_chroma():
    """
    Initialize chroma client
    """
    client = get_chroma_client()
    
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def get_chroma_client():
    """
    Get the chroma client
    """
    return chromadb.PersistentClient(path=PERSISTENT_DIR)

def get_ingested_files(collection) -> set[str]:
    """Get the set of file names already stored in the collection."""
    if collection.count() == 0:
        return set()
    results = collection.get(include=["metadatas"])
    return {m.get("file_name") for m in results["metadatas"] if m.get("file_name")}


@mcp.tool
def ingest_data_dir():
    """Ingest and vectorize PDF files from the data directory into ChromaDB.

    Parses PDFs using LlamaParse, extracts text content, and stores document
    chunks in the vector database. Files already present in the collection
    are automatically skipped to avoid duplicates.

    Returns:
        str: Summary message with the number of new and total documents ingested.
    """
    collection = init_chroma()
    ingested_files = get_ingested_files(collection)

    parser = LlamaParse(api_key=LLAMA_CLOUD_API_KEY, result_type="text")
    file_extractor = {".pdf": parser}

    documents = SimpleDirectoryReader(DATA_DIR, file_extractor=file_extractor).load_data()

    new_count = 0
    for doc in documents:
        file_name = doc.metadata.get("file_name")
        if file_name in ingested_files:
            continue
        collection.add(
            documents=[doc.text],
            metadatas=[doc.metadata],
            ids=[doc.doc_id],
        )
        new_count += 1

    return "Ingested {new_count} new documents (total: {collection.count()})"


@mcp.tool
def query_documents(query: str, n_results: int = 2) -> str:
    """Search ingested documents using natural language queries.

    Performs semantic similarity search against the ChromaDB collection
    and returns the most relevant document chunks with source metadata
    and similarity scores.

    Args:
        query: Natural language search query.
        n_results: Maximum number of results to return (default: 2).

    Returns:
        str: Formatted search results including content, source file, and similarity score.
    """
    chroma_client = get_chroma_client()
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas", "documents", "distances"]
    )
    if len(results["documents"]) == 0 or not results["documents"][0]:
        return f"No documents found for query '{query}'"
    
    # Format results
    formatted_results = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
    distances = results["distances"][0] if results["distances"] else [{}] * len(documents)

    for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
        result_text = f"\n--- Result {i+1} ---\n"
        result_text += f"Content: {doc}\n"
        result_text += f"Source {metadata.get('file_name', 'Unknown')}\n"
        result_text += f"Similarity Score: {1 - distance:.3f}\n"
        formatted_results.append(result_text)

    response = f"Found {len(documents)} relevant documents for query: '{query}'\n"
    response += "\n".join(formatted_results)

    return response

@mcp.tool
def get_db_status() -> str:
    """
    Get the status of the vector database.
    """

    chroma_client = get_chroma_client()
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    count = collection.count()
    return f"Database status: {count} documents ingested"
