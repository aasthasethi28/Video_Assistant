# ============================================================
# REELMIND - api/main.py
# ============================================================

import os
import uuid
import shutil
import tempfile
import traceback

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# IMPORT PROJECT MODULES
# ============================================================

from utils.audio_processor import process_input

from core.transcriber import transcribe_all

from core.summarizer import (
    summarize,
    generate_title,
)

from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)

from core.rag_engine import (
    build_rag_chain,
    ask_question,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="REELMIND API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Render frontend
        "https://video-assistant-1.onrender.com",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# SESSION STORAGE
# ============================================================

sessions: dict[str, dict[str, Any]] = {}


# ============================================================
# CHAT MODEL
# ============================================================

class ChatRequest(BaseModel):

    session_id: str

    question: str

    history: list = []


# ============================================================
# HELPERS
# ============================================================

def normalize_language(
    language: Any
) -> str:

    if language is None:
        return "english"

    language = str(
        language
    ).strip().lower()

    if language in {
        "hinglish",
        "hindi",
        "hi",
        "codemix",
        "code-mix",
    }:

        return "hinglish"

    return "english"


def extract_source_and_language(
    payload: Any
):

    """
    Accept several request shapes safely.

    Preferred:

        {
            "source": "...",
            "language": "hinglish"
        }

    Also accepts:

        {
            "url": "...",
            "language": "hinglish"
        }

    or a plain string.
    """

    if isinstance(
        payload,
        dict
    ):

        source = (
            payload.get("source")
            or payload.get("url")
            or payload.get("path")
            or payload.get("file")
        )

        language = (
            payload.get("language")
            or "english"
        )

    elif isinstance(
        payload,
        str
    ):

        source = payload

        language = "english"

    else:

        source = None

        language = "english"


    if source is not None:

        source = str(
            source
        ).strip()


    language = normalize_language(
        language
    )


    return (
        source,
        language
    )


def clean_error_message(
    error: Exception
) -> str:

    message = str(
        error
    ).strip()

    if not message:

        message = (
            "An unexpected error occurred."
        )

    return message


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {

        "name":
            "REELMIND",

        "status":
            "running",

        "api":
            "https://video-assistant-jzzm.onrender.com",

        "frontend":
            "https://video-assistant-1.onrender.com",

    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():

    return {

        "status":
            "ok",

        "service":
            "reelmind-api",

    }


# ============================================================
# ANALYZE YOUTUBE URL
# ============================================================

@app.post("/api/analyze")
async def analyze(
    request: Request
):

    # ========================================================
    # READ RAW REQUEST
    # ========================================================

    try:

        payload = await request.json()

    except Exception:

        raise HTTPException(

            status_code=400,

            detail=(
                "Invalid JSON request."
            ),

        )


    # ========================================================
    # NORMALIZE REQUEST
    # ========================================================

    source, language = (
        extract_source_and_language(
            payload
        )
    )


    # ========================================================
    # VALIDATE SOURCE
    # ========================================================

    if not source:

        raise HTTPException(

            status_code=400,

            detail=(
                "Please provide a YouTube URL "
                "or a local audio/video file path."
            ),

        )


    # ========================================================
    # SESSION
    # ========================================================

    session_id = str(
        uuid.uuid4()
    )


    print()
    print(
        "=" * 70
    )

    print(
        "REELMIND ANALYSIS STARTED"
    )

    print(
        "Session:",
        session_id
    )

    print(
        "Source:",
        source
    )

    print(
        "Language:",
        language
    )

    print(
        "=" * 70
    )

    print()


    try:

        # ====================================================
        # 1. PROCESS INPUT
        # ====================================================

        print(
            "[1/6] Processing input..."
        )

        chunks = process_input(
            source
        )


        if not chunks:

            raise RuntimeError(
                "No audio chunks were produced."
            )


        print(
            f"Audio chunks: {len(chunks)}"
        )


        # ====================================================
        # 2. TRANSCRIPTION
        # ====================================================

        print()
        print(
            "[2/6] Transcribing audio..."
        )


        transcript = transcribe_all(

            chunks,

            language,

        )


        if not transcript:

            raise RuntimeError(
                "Transcription returned empty text."
            )


        print(
            "Transcript length:",
            len(transcript)
        )


        # ====================================================
        # 3. TITLE + SUMMARY
        # ====================================================

        print()
        print(
            "[3/6] Generating title..."
        )


        title = generate_title(
            transcript
        )


        print(
            "[3/6] Generating summary..."
        )


        summary = summarize(
            transcript
        )


        # ====================================================
        # 4. EXTRACTION
        # ====================================================

        print()
        print(
            "[4/6] Extracting meeting information..."
        )


        action_items = (
            extract_action_items(
                transcript
            )
        )


        decisions = (
            extract_key_decisions(
                transcript
            )
        )


        questions = (
            extract_questions(
                transcript
            )
        )


        # ====================================================
        # 5. BUILD RAG
        # ====================================================

        print()
        print(
            "[5/6] Building RAG index..."
        )


        rag_chain = build_rag_chain(

            transcript,

            session_id=session_id,

        )


        # ====================================================
        # SAVE SESSION
        # ====================================================

        sessions[
            session_id
        ] = {

            "rag_chain":
                rag_chain,

            "transcript":
                transcript,

            "title":
                title,

            "summary":
                summary,

            "action_items":
                action_items,

            "key_decisions":
                decisions,

            "open_questions":
                questions,

            "language":
                language,

            "history":
                [],

        }


        # ====================================================
        # 6. READY
        # ====================================================

        print()
        print(
            "[6/6] REELMIND READY"
        )

        print(
            "Session:",
            session_id
        )

        print(
            "=" * 70
        )

        print()


        return {

            "success":
                True,

            "session_id":
                session_id,

            "title":
                title,

            "transcript":
                transcript,

            "summary":
                summary,

            "action_items":
                action_items,

            "key_decisions":
                decisions,

            "open_questions":
                questions,

        }


    except Exception as e:

        print()
        print(
            "=" * 70
        )

        print(
            "REELMIND ANALYZE ERROR"
        )

        print(
            "Type:",
            type(e).__name__
        )

        print(
            "Message:",
            clean_error_message(e)
        )

        print(
            "-" * 70
        )

        traceback.print_exc()

        print(
            "=" * 70
        )

        print()


        raise HTTPException(

            status_code=500,

            detail=(
                "Unable to analyze the recording. "
                "Please check the backend terminal for details."
            ),

        )


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    try:

        if not file.filename:

            raise HTTPException(

                status_code=400,

                detail=(
                    "No filename was provided."
                ),

            )


        suffix = (
            Path(
                file.filename
            ).suffix
            or ".tmp"
        )


        temp_dir = (
            Path(
                tempfile.gettempdir()
            )
            / "reelmind"
        )


        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        file_id = str(
            uuid.uuid4()
        )


        file_path = (
            temp_dir
            /
            f"{file_id}{suffix}"
        )


        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )


        print(
            "Uploaded:",
            file_path
        )


        return {

            "success":
                True,

            "path":
                str(file_path),

            "filename":
                file.filename,

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "UPLOAD ERROR:",
            repr(e)
        )


        raise HTTPException(

            status_code=500,

            detail=(
                "Unable to upload the file."
            ),

        )


# ============================================================
# ANALYZE UPLOADED FILE
# ============================================================

@app.post("/api/analyze-file")
async def analyze_file(

    file: UploadFile = File(...),

    language: str = "english",

):

    if not file.filename:

        raise HTTPException(

            status_code=400,

            detail=(
                "No file was provided."
            ),

        )


    temp_dir = (
        Path(
            tempfile.gettempdir()
        )
        / "reelmind"
    )


    temp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    suffix = (
        Path(
            file.filename
        ).suffix
        or ".tmp"
    )


    file_id = str(
        uuid.uuid4()
    )


    file_path = (
        temp_dir
        /
        f"{file_id}{suffix}"
    )


    try:

        # ----------------------------------------------------
        # SAVE UPLOAD
        # ----------------------------------------------------

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )


        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        session_id = str(
            uuid.uuid4()
        )


        language = normalize_language(
            language
        )


        print()
        print(
            "=" * 70
        )

        print(
            "REELMIND FILE ANALYSIS STARTED"
        )

        print(
            "Session:",
            session_id
        )

        print(
            "File:",
            file_path
        )

        print(
            "Language:",
            language
        )

        print(
            "=" * 70
        )

        print()


        # ----------------------------------------------------
        # 1. PROCESS
        # ----------------------------------------------------

        print(
            "[1/6] Processing input..."
        )


        chunks = process_input(
            str(file_path)
        )


        # ----------------------------------------------------
        # 2. TRANSCRIBE
        # ----------------------------------------------------

        print(
            "[2/6] Transcribing audio..."
        )


        transcript = transcribe_all(

            chunks,

            language,

        )


        if not transcript:

            raise RuntimeError(
                "Transcription returned empty text."
            )


        # ----------------------------------------------------
        # 3. TITLE + SUMMARY
        # ----------------------------------------------------

        print(
            "[3/6] Generating title..."
        )


        title = generate_title(
            transcript
        )


        print(
            "[3/6] Generating summary..."
        )


        summary = summarize(
            transcript
        )


        # ----------------------------------------------------
        # 4. EXTRACTION
        # ----------------------------------------------------

        print(
            "[4/6] Extracting information..."
        )


        action_items = (
            extract_action_items(
                transcript
            )
        )


        decisions = (
            extract_key_decisions(
                transcript
            )
        )


        questions = (
            extract_questions(
                transcript
            )
        )


        # ----------------------------------------------------
        # 5. RAG
        # ----------------------------------------------------

        print(
            "[5/6] Building RAG..."
        )


        rag_chain = build_rag_chain(

            transcript,

            session_id=session_id,

        )


        sessions[
            session_id
        ] = {

            "rag_chain":
                rag_chain,

            "transcript":
                transcript,

            "title":
                title,

            "summary":
                summary,

            "action_items":
                action_items,

            "key_decisions":
                decisions,

            "open_questions":
                questions,

            "language":
                language,

            "history":
                [],

        }


        print(
            "[6/6] REELMIND READY"
        )


        return {

            "success":
                True,

            "session_id":
                session_id,

            "title":
                title,

            "transcript":
                transcript,

            "summary":
                summary,

            "action_items":
                action_items,

            "key_decisions":
                decisions,

            "open_questions":
                questions,

        }


    except Exception as e:

        print()
        print(
            "=" * 70
        )

        print(
            "FILE ANALYSIS ERROR"
        )

        print(
            type(e).__name__,
            str(e)
        )

        traceback.print_exc()

        print(
            "=" * 70
        )


        raise HTTPException(

            status_code=500,

            detail=(
                "Unable to analyze the uploaded recording."
            ),

        )


    finally:

        try:

            if file_path.exists():

                file_path.unlink()

        except Exception:

            pass


# ============================================================
# CHAT
# ============================================================

@app.post("/api/chat")
async def chat(
    request: ChatRequest
):

    session = sessions.get(
        request.session_id
    )


    if not session:

        raise HTTPException(

            status_code=404,

            detail=(
                "This meeting session has expired. "
                "Please analyze the recording again."
            ),

        )


    question = (
        request.question
        or ""
    ).strip()


    if not question:

        return {

            "success":
                True,

            "answer":
                "Please ask me something.",

        }


    try:

        history = (
            request.history
            if isinstance(
                request.history,
                list
            )
            else []
        )


        print()
        print(
            "CHAT QUESTION:"
        )

        print(
            question
        )


        answer = ask_question(

            session[
                "rag_chain"
            ],

            question,

            history=history,

        )


        if answer is None:

            answer = (
                "I couldn't generate an answer."
            )


        answer = str(
            answer
        ).strip()


        # ----------------------------------------------------
        # SAVE HISTORY
        # ----------------------------------------------------

        session[
            "history"
        ].append({

            "role":
                "user",

            "content":
                question,

        })


        session[
            "history"
        ].append({

            "role":
                "assistant",

            "content":
                answer,

        })


        return {

            "success":
                True,

            "answer":
                answer,

        }


    except Exception as e:

        print()
        print(
            "=" * 70
        )

        print(
            "CHAT ERROR"
        )

        print(
            type(e).__name__,
            str(e)
        )

        traceback.print_exc()

        print(
            "=" * 70
        )


        return {

            "success":
                False,

            "answer":
                (
                    "I couldn't answer that right now. "
                    "Please try asking the question again."
                ),

        }


# ============================================================
# STATIC FRONTEND
# ============================================================

FRONTEND_DIR = (
    PROJECT_ROOT
    /
    "frontend"
)


if FRONTEND_DIR.exists():

    app.mount(

        "/frontend",

        StaticFiles(
            directory=FRONTEND_DIR
        ),

        name="frontend",

    )