# ============================================================
# REELMIND - LIGHTWEIGHT RAG ENGINE
# ============================================================

import os
from pathlib import Path
from typing import Optional

import requests

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_mistralai import ChatMistralAI


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


MISTRAL_API_KEY = os.getenv(
    "MISTRAL_API_KEY"
)

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "mistral-small-latest"
)

MISTRAL_EMBED_MODEL = os.getenv(
    "MISTRAL_EMBED_MODEL",
    "mistral-embed"
)

MISTRAL_EMBED_URL = (
    "https://api.mistral.ai/v1/embeddings"
)


if MISTRAL_API_KEY:

    print(
        "✓ Mistral API key loaded"
    )

else:

    print(
        "✗ MISTRAL_API_KEY not found"
    )


# ============================================================
# MISTRAL API EMBEDDINGS
# ============================================================

class MistralAPIEmbeddings:
    """
    Lightweight LangChain-compatible embeddings.

    IMPORTANT:
    This does NOT load a local embedding model.

    Embeddings are generated remotely by
    the Mistral API.

    This keeps deployment RAM very low.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-embed",
    ):

        if not api_key:

            raise RuntimeError(
                "MISTRAL_API_KEY is not configured."
            )

        self.api_key = api_key

        self.model = model

    # --------------------------------------------------------
    # EMBED DOCUMENTS
    # --------------------------------------------------------

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        headers = {

            "Authorization":
                f"Bearer {self.api_key}",

            "Content-Type":
                "application/json",

        }

        payload = {

            "model":
                self.model,

            "input":
                texts,

        }

        response = requests.post(

            MISTRAL_EMBED_URL,

            headers=headers,

            json=payload,

            timeout=120,

        )

        if not response.ok:

            print(
                "Mistral embeddings error:",
                response.status_code,
                response.text,
            )

            raise RuntimeError(
                "Mistral embeddings API failed: "
                f"{response.status_code}"
            )

        result = response.json()

        data = result.get(
            "data",
            []
        )

        # Mistral returns objects with
        # index + embedding.
        data = sorted(
            data,
            key=lambda item:
                item.get("index", 0)
        )

        return [
            item["embedding"]
            for item in data
        ]

    # --------------------------------------------------------
    # EMBED QUERY
    # --------------------------------------------------------

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        embeddings = self.embed_documents(
            [text]
        )

        if not embeddings:

            raise RuntimeError(
                "Mistral returned an empty embedding."
            )

        return embeddings[0]


# ============================================================
# EMBEDDINGS FACTORY
# ============================================================

def get_embeddings():

    return MistralAPIEmbeddings(

        api_key=MISTRAL_API_KEY,

        model=MISTRAL_EMBED_MODEL,

    )


# ============================================================
# LLM
# ============================================================

def get_llm(
    temperature: float = 0.3,
):

    if not MISTRAL_API_KEY:

        raise RuntimeError(
            "MISTRAL_API_KEY is not configured."
        )

    return ChatMistralAI(

        model=MISTRAL_MODEL,

        mistral_api_key=MISTRAL_API_KEY,

        temperature=temperature,

    )


# ============================================================
# TRANSCRIPT CHUNKING
# ============================================================

def create_documents(
    transcript: str,
):

    if not transcript or not transcript.strip():

        raise ValueError(
            "Transcript is empty."
        )

    splitter = RecursiveCharacterTextSplitter(

        chunk_size=1200,

        chunk_overlap=200,

        separators=[

            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            " ",

        ],

    )

    chunks = splitter.split_text(
        transcript
    )

    documents = []

    for index, chunk in enumerate(
        chunks
    ):

        if not chunk.strip():
            continue

        documents.append(

            Document(

                page_content=chunk,

                metadata={

                    "source":
                        "meeting_transcript",

                    "chunk_index":
                        index,

                },

            )

        )

    return documents


# ============================================================
# BUILD VECTOR STORE
# ============================================================

def build_vector_store(
    transcript: str,
    session_id: Optional[str] = None,
):

    documents = create_documents(
        transcript
    )

    collection_name = (

        f"reelmind_{session_id}"

        if session_id

        else "reelmind_default"

    )

    print()
    print(
        "Creating Mistral embeddings..."
    )

    embeddings = get_embeddings()

    vector_store = Chroma(

        collection_name=
            collection_name,

        embedding_function=
            embeddings,

    )

    vector_store.add_documents(
        documents
    )

    print(
        f"✓ RAG index created: "
        f"{len(documents)} chunks"
    )

    return vector_store


# ============================================================
# BUILD RAG CHAIN
# ============================================================

def build_rag_chain(
    transcript: str,
    session_id: Optional[str] = None,
):

    vector_store = build_vector_store(

        transcript,

        session_id=session_id,

    )

    return vector_store


# ============================================================
# RETRIEVE TRANSCRIPT CONTEXT
# ============================================================

def retrieve_context(
    vector_store,
    question: str,
    k: int = 5,
):

    try:

        documents = vector_store.similarity_search(

            question,

            k=k,

        )

        return documents

    except Exception as e:

        print(
            "RAG retrieval error:",
            repr(e)
        )

        return []


# ============================================================
# FORMAT CONTEXT
# ============================================================

def format_context(
    documents,
):

    if not documents:

        return ""

    return "\n\n---\n\n".join(

        doc.page_content

        for doc in documents

    )


# ============================================================
# CONVERSATION FORMAT
# ============================================================

def format_history(
    history,
):

    if not history:

        return (
            "No previous conversation."
        )

    lines = []

    for message in history[-8:]:

        role = message.get(
            "role",
            "user"
        )

        content = message.get(
            "content",
            ""
        )

        if not content:
            continue

        if role == "assistant":

            role_name = "Assistant"

        else:

            role_name = "User"

        lines.append(

            f"{role_name}: {content}"

        )

    return "\n".join(lines)


# ============================================================
# DETERMINE MEETING QUESTION
# ============================================================

def is_meeting_question(
    question: str,
    context: str,
    history: str,
):

    if not context.strip():

        return False

    llm = get_llm(
        temperature=0
    )

    prompt = f"""

You are deciding whether a user's question should be answered
using a meeting/video transcript or using general knowledge.

Return ONLY:

MEETING

or

GENERAL


MEETING examples:

- what did they decide?
- what was the outcome?
- video me kya explain kiya?
- meeting mein kisne ye bola?
- according to the video...
- what was discussed?
- iske baare mein video mein kya bola?


GENERAL examples:

- what is a linked list?
- explain binary trees
- what is recursion?
- how does a database work?
- python kya hai?


USER QUESTION:
{question}


MEETING CONTEXT:
{context}


RECENT HISTORY:
{history}

"""

    try:

        result = llm.invoke(
            prompt
        )

        decision = (
            result.content
            .strip()
            .upper()
        )

        print(
            "Question classification:",
            decision
        )

        return decision.startswith(
            "MEETING"
        )

    except Exception as e:

        print(
            "Intent classification error:",
            repr(e)
        )

        meeting_words = [

            "video",
            "meeting",
            "transcript",
            "recording",
            "discussed",
            "discuss",
            "decided",
            "decision",
            "outcome",
            "speaker",
            "said",
            "according to",
            "in the video",
            "video me",
            "meeting me",
            "meeting mein",
            "video mein",
            "video wale",

        ]

        question_lower = (
            question.lower()
        )

        return any(

            word in question_lower

            for word in meeting_words

        )


# ============================================================
# MEETING ANSWER
# ============================================================

def answer_from_meeting(
    question: str,
    context: str,
    history: str,
):

    llm = get_llm(
        temperature=0.3
    )

    prompt = f"""

You are REELMIND, an intelligent
meeting/video assistant.

Answer the user's question using
the meeting context.

MEETING CONTEXT:

{context}


RECENT CONVERSATION:

{history}


USER QUESTION:

{question}


RULES:

1. Use the meeting context as the
   factual source.

2. Understand Hindi, English,
   Hinglish and informal wording.

3. Do not require exact transcript
   wording.

4. Explain concepts clearly when
   requested.

5. Identify outcomes when asked.

6. Identify decisions when asked.

7. Explain reasons when asked.

8. Never invent information.

9. If the recording genuinely does
   not contain the answer, say:

"The recording doesn't provide enough
information about that."

10. Match the user's language.

11. Never mention internal RAG,
    embeddings or vector stores.

"""

    response = llm.invoke(
        prompt
    )

    return response.content.strip()


# ============================================================
# GENERAL ANSWER
# ============================================================

def answer_generally(
    question: str,
    history: str,
):

    llm = get_llm(
        temperature=0.5
    )

    prompt = f"""

You are REELMIND, a helpful
conversational AI assistant.

The user is asking a general
question rather than a question
requiring the meeting recording.

RECENT CONVERSATION:

{history}


USER QUESTION:

{question}


Requirements:

- Understand Hindi.
- Understand English.
- Understand Hinglish.
- Understand informal wording.
- Explain simply when requested.
- Match the user's language.
- Be helpful and natural.

"""

    response = llm.invoke(
        prompt
    )

    return response.content.strip()


# ============================================================
# MAIN ASK FUNCTION
# ============================================================

def ask_question(
    rag_chain,
    question: str,
    history=None,
):

    question = (
        question or ""
    ).strip()

    history = history or []

    if not question:

        return (
            "Please ask me something."
        )

    try:

        formatted_history = (
            format_history(history)
        )

        documents = retrieve_context(

            rag_chain,

            question,

            k=5,

        )

        context = format_context(
            documents
        )

        print(
            f"\nRetrieved "
            f"{len(documents)} "
            f"transcript chunks."
        )

        meeting_question = (
            is_meeting_question(

                question,

                context,

                formatted_history,

            )
        )

        if meeting_question:

            return answer_from_meeting(

                question,

                context,

                formatted_history,

            )

        return answer_generally(

            question,

            formatted_history,

        )

    except Exception as e:

        print(
            "\n================ RAG ERROR ================"
        )

        print(
            type(e).__name__,
            str(e)
        )

        print(
            "===========================================\n"
        )

        return (

            "I'm having trouble "
            "processing that right now. "
            "Please try again in a moment."

        )