# core/rag_engine.py

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_mistralai import ChatMistralAI


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "mistral-small-latest"
)

if MISTRAL_API_KEY:
    print("✓ Mistral API key loaded")
else:
    print("✗ MISTRAL_API_KEY not found")


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
# EMBEDDINGS
# ============================================================

def get_embeddings():

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={
            "device": "cpu"
        },
        encode_kwargs={
            "normalize_embeddings": True
        },
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

    for index, chunk in enumerate(chunks):

        if not chunk.strip():
            continue

        documents.append(
            Document(
                page_content=chunk,
                metadata={
                    "source": "meeting_transcript",
                    "chunk_index": index,
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

    embeddings = get_embeddings()

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
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
        return "No previous conversation."

    lines = []

    # Only use recent conversation.
    # This prevents huge prompts.

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
# DETERMINE WHETHER QUESTION IS MEETING-SPECIFIC
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

MEETING TRANSCRIPT CONTEXT:
{context}

RECENT CONVERSATION:
{history}

CURRENT USER QUESTION:
{question}

Return ONLY one of:

MEETING
GENERAL

Choose MEETING when the user is referring to the recording,
meeting, transcript, discussion, speaker, decision, explanation,
example, outcome, or something that happened in the video.

Examples of MEETING:
- "what did they decide?"
- "what was the outcome?"
- "video me kya explain kiya?"
- "meeting mein kisne ye bola?"
- "according to the video..."
- "what was discussed about linked lists?"
- "iske baare mein video mein kya bola tha?"

Choose GENERAL when the user is simply asking for knowledge
or an explanation without referring to the recording.

Examples of GENERAL:
- "what is a linked list?"
- "explain binary trees"
- "what is recursion?"
- "how does a database work?"
- "python kya hai?"

If the user uses Hinglish, Hindi, informal language,
spelling mistakes, or short phrases, understand the meaning.

Do NOT classify a question as MEETING merely because the same
topic happens to appear in the transcript.
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

        # Safe fallback:
        # explicit meeting references are treated as meeting.

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

        question_lower = question.lower()

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
You are REELMIND, an intelligent meeting/video assistant.

Answer the user's question using the meeting context.

MEETING CONTEXT:
{context}

RECENT CONVERSATION:
{history}

USER QUESTION:
{question}

RULES:

1. Use the meeting context as the factual source for
   meeting-specific information.

2. Understand the meaning of the question even when it is:
   - Hindi
   - English
   - Hinglish
   - informal
   - grammatically incorrect
   - short

3. Do not require exact transcript wording.

4. If the user asks for an explanation, explain the concept
   clearly instead of simply copying the transcript.

5. If the user asks:
   "what was the outcome?"
   identify the outcome from the meeting.

6. If the user asks:
   "what did they decide?"
   identify the decision from the meeting.

7. If the user asks:
   "why?"
   explain the reason using the available context.

8. Never invent information.

9. If the meeting context genuinely does not contain the
   requested information, say:
   "The recording doesn't provide enough information about that."

10. Match the user's language naturally.

11. Do not mention RAG, embeddings, vector stores,
    retrieval, prompts, or internal implementation.

12. Do not output technical errors.
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
You are REELMIND, a helpful conversational AI assistant.

The user is asking a general question, not a question that
requires information from the meeting recording.

RECENT CONVERSATION:
{history}

USER QUESTION:
{question}

Answer naturally and helpfully.

Requirements:

- Understand Hindi, English and Hinglish.
- Understand informal wording and spelling mistakes.
- If the user asks for a simple explanation, explain simply.
- If the user asks for technical information, give a useful
  technical explanation.
- Do not mention the transcript unless necessary.
- Do not say that information is missing from the transcript.
- Match the user's language.
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

        # ----------------------------------------------------
        # Recent conversation
        # ----------------------------------------------------

        formatted_history = format_history(
            history
        )

        # ----------------------------------------------------
        # Retrieve transcript
        # ----------------------------------------------------

        documents = retrieve_context(
            rag_chain,
            question,
            k=5,
        )

        context = format_context(
            documents
        )

        print(
            f"\nRetrieved {len(documents)} transcript chunks."
        )

        # ----------------------------------------------------
        # Decide intent
        # ----------------------------------------------------

        meeting_question = is_meeting_question(
            question,
            context,
            formatted_history,
        )

        # ----------------------------------------------------
        # Meeting / RAG
        # ----------------------------------------------------

        if meeting_question:

            return answer_from_meeting(
                question,
                context,
                formatted_history,
            )

        # ----------------------------------------------------
        # General LLM
        # ----------------------------------------------------

        return answer_generally(
            question,
            formatted_history,
        )

    except Exception as e:

        # NEVER send technical details to the frontend.

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
            "I'm having trouble processing that right now. "
            "Please try again in a moment."
        )