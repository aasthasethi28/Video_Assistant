import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


load_dotenv()


CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embeddings():

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={
            "device": "cpu"
        }
    )


def build_vector_store(
    transcript: str
) -> Chroma:

    if not transcript.strip():
        raise ValueError(
            "Cannot build vector store from an empty transcript."
        )

    print("Building vector store...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(
        transcript
    )

    print(
        f"Creating {len(chunks)} document chunks..."
    )

    documents = [
        Document(
            page_content=chunk,
            metadata={
                "chunk_index": i
            }
        )
        for i, chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR
    )

    print(
        "Vector store created successfully."
    )

    return vector_store


def load_vector_store() -> Chroma:

    if not os.path.exists(CHROMA_DIR):
        raise FileNotFoundError(
            f"Vector store directory not found: {CHROMA_DIR}"
        )

    embeddings = get_embeddings()

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )

    return vector_store


def get_retriever(
    vector_store: Chroma,
    k: int = 4
):

    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k
        }
    )