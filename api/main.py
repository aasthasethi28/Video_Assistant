# ============================================================
# REELMIND - api/main.py
# ============================================================

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
# PROJECT IMPORTS
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
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
# CHAT REQUEST
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


def error_text(
    error: Exception
) -> str:

    text = str(
        error
    ).strip()

    if not text:

        text = (
            "Unknown error"
        )

    return text


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
# ANALYZE YOUTUBE / URL
# ============================================================

@app.post("/api/analyze")
async def analyze(
    request: Request
):

    # --------------------------------------------------------
    # READ REQUEST
    # --------------------------------------------------------

    try:

        payload = await request.json()

    except Exception as e:

        print(
            "JSON REQUEST ERROR:",
            repr(e)
        )

        raise HTTPException(

            status_code=400,

            detail=(
                "Invalid JSON request."
            ),

        )


    # --------------------------------------------------------
    # SOURCE + LANGUAGE
    # --------------------------------------------------------

    source, language = (
        extract_source_and_language(
            payload
        )
    )


    print()
    print("=" * 70)
    print("REELMIND ANALYZE REQUEST")
    print("Source:", source)
    print("Language:", language)
    print("=" * 70)
    print()


    if not source:

        raise HTTPException(

            status_code=400,

            detail=(
                "Please provide a YouTube URL."
            ),

        )


    session_id = str(
        uuid.uuid4()
    )


    # ========================================================
    # 1. PROCESS INPUT
    # ========================================================

    try:

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
            f"[1/6] OK - {len(chunks)} chunks"
        )

    except Exception as e:

        print()
        print(
            "!!! PROCESS INPUT ERROR !!!"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "processing_input",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

            "session_id":
                session_id,

        }


    # ========================================================
    # 2. TRANSCRIPTION
    # ========================================================

    try:

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
            "[2/6] OK - transcript length:",
            len(transcript)
        )

    except Exception as e:

        print()
        print(
            "!!! TRANSCRIPTION ERROR !!!"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "transcription",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

            "session_id":
                session_id,

        }


    # ========================================================
    # 3. TITLE + SUMMARY
    # ========================================================

    try:

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


        print(
            "[3/6] OK"
        )

    except Exception as e:

        print()
        print(
            "!!! SUMMARY ERROR !!!"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "summary",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

            "session_id":
                session_id,

        }


    # ========================================================
    # 4. EXTRACTION
    # ========================================================

    try:

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


        print(
            "[4/6] OK"
        )

    except Exception as e:

        print()
        print(
            "!!! EXTRACTION ERROR !!!"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "extraction",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

            "session_id":
                session_id,

        }


    # ========================================================
    # 5. RAG
    # ========================================================

    try:

        print(
            "[5/6] Building RAG index..."
        )


        rag_chain = build_rag_chain(

            transcript,

            session_id=session_id,

        )


        print(
            "[5/6] OK"
        )

    except Exception as e:

        print()
        print(
            "!!! RAG ERROR !!!"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "rag",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

            "session_id":
                session_id,

        }


    # ========================================================
    # SAVE SESSION
    # ========================================================

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


    # ========================================================
    # READY
    # ========================================================

    print()
    print("=" * 70)
    print("REELMIND READY")
    print(
        "Session:",
        session_id
    )
    print("=" * 70)
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
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()

        raise HTTPException(

            status_code=500,

            detail=(
                f"Upload failed: "
                f"{error_text(e)}"
            ),

        )


# ============================================================
# ANALYZE FILE
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

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )


        session_id = str(
            uuid.uuid4()
        )


        language = normalize_language(
            language
        )


        print(
            "FILE ANALYSIS:",
            file.filename,
            language
        )


        chunks = process_input(
            str(file_path)
        )


        if not chunks:

            raise RuntimeError(
                "No audio chunks were produced."
            )


        transcript = transcribe_all(

            chunks,

            language,

        )


        if not transcript:

            raise RuntimeError(
                "Transcription returned empty text."
            )


        title = generate_title(
            transcript
        )


        summary = summarize(
            transcript
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
            "FILE ANALYSIS ERROR:"
        )

        print(
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()


        return {

            "success":
                False,

            "error":
                True,

            "stage":
                "file_analysis",

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

        }


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
            "CHAT ERROR:",
            type(e).__name__,
            error_text(e)
        )

        traceback.print_exc()


        return {

            "success":
                False,

            "answer":
                (
                    "I couldn't answer that right now. "
                    "Please try again."
                ),

            "error_type":
                type(e).__name__,

            "error_message":
                error_text(e),

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