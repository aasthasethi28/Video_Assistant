import uuid
import os
import re
import html
import shutil
import tempfile
import traceback

from pathlib import Path
from typing import Any, Optional

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

from utils.audio_processor import process_input, chunk_audio
import yt_dlp
from pydub import AudioSegment

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
# YOUTUBE / INPUT HELPERS
# ============================================================

YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


def _youtube_video_id(url: str) -> Optional[str]:
    match = YOUTUBE_URL_RE.search(str(url))
    return match.group(1) if match else None


def _youtube_is_auth_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = (
        "sign in to confirm",
        "you're not a bot",
        "you’re not a bot",
        "cookies-from-browser",
        "cookies for the authentication",
        "login_required",
    )
    return any(marker in message for marker in markers)


def _download_youtube_audio_api(url: str) -> str:
    """
    Server-side YouTube audio extraction.

    We deliberately keep this isolated from utils.audio_processor.py so
    the API can try safer yt-dlp clients without changing the rest of
    the application.
    """
    download_dir = PROJECT_ROOT / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    cookie_file = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
    cookie_file_path = Path(cookie_file) if cookie_file else None

    base_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(download_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
    }

    if cookie_file_path and cookie_file_path.exists():
        base_opts["cookiefile"] = str(cookie_file_path)
        print("YouTube cookies: enabled")
    else:
        print("YouTube cookies: not configured")

    # Keep the attempts conservative. If YouTube requires account
    # authentication/PO tokens, yt-dlp cannot manufacture those on Render.
    client_attempts = [
        ["android_vr"],
        ["web_embedded"],
        ["web_safari"],
    ]

    last_error = None

    for clients in client_attempts:
        opts = dict(base_opts)
        opts["extractor_args"] = {
            "youtube": {
                "player_client": clients,
            }
        }

        print(
            "YouTube extraction attempt:",
            ",".join(clients),
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            video_id = (info or {}).get("id")
            if not video_id:
                raise RuntimeError(
                    "YouTube did not return a video ID."
                )

            wav_path = download_dir / f"{video_id}.wav"

            if wav_path.exists():
                return str(wav_path)

            # Some yt-dlp/FFmpeg combinations can preserve another
            # extension. Convert it through pydub as a final local step.
            candidates = list(download_dir.glob(f"{video_id}.*"))
            candidates = [
                p for p in candidates
                if p.suffix.lower() not in {".part", ".ytdl", ".wav"}
            ]

            if candidates:
                converted = download_dir / f"{video_id}.wav"
                audio = AudioSegment.from_file(str(candidates[0]))
                audio.export(str(converted), format="wav")
                return str(converted)

            raise FileNotFoundError(
                "yt-dlp completed but no downloaded audio file was found."
            )

        except Exception as exc:
            last_error = exc
            print(
                "YouTube extraction attempt failed:",
                type(exc).__name__,
                str(exc),
            )

            if cookie_file_path and cookie_file_path.exists():
                # A supplied cookie file should be treated as the user's
                # intended authentication source; further client retries
                # are still attempted but the final error remains explicit.
                continue

    if last_error is None:
        raise RuntimeError("YouTube audio extraction failed.")

    raise last_error


def _download_public_youtube_transcript(
    url: str,
    preferred_language: str,
) -> Optional[str]:
    """
    Lightweight fallback using YouTube's public timed-text endpoint.

    This does not bypass authentication. It only helps when the video
    exposes a public caption track. If no public captions are available,
    None is returned and the normal audio error is preserved.
    """
    video_id = _youtube_video_id(url)

    if not video_id:
        return None

    import requests
    import xml.etree.ElementTree as ET

    language_candidates = (
        ["hi", "en"]
        if preferred_language == "hinglish"
        else ["en", "hi"]
    )

    for lang in language_candidates:
        urls = [
            (
                "https://www.youtube.com/api/timedtext"
                f"?v={video_id}&lang={lang}&fmt=srv3"
            ),
            (
                "https://video.google.com/timedtext"
                f"?v={video_id}&lang={lang}&fmt=srv3"
            ),
        ]

        for caption_url in urls:
            try:
                response = requests.get(
                    caption_url,
                    timeout=15,
                    headers={
                        "User-Agent":
                            "Mozilla/5.0"
                    },
                )

                if response.status_code != 200:
                    continue

                body = response.text.strip()

                if not body or "<text" not in body:
                    continue

                root = ET.fromstring(body)

                parts = []

                for node in root.findall(".//text"):
                    value = "".join(node.itertext()).strip()

                    if value:
                        value = html.unescape(value)
                        value = re.sub(
                            r"\s+",
                            " ",
                            value,
                        )
                        parts.append(value)

                transcript = " ".join(parts).strip()

                if transcript:
                    print(
                        "Public YouTube captions recovered:",
                        len(transcript),
                        "characters",
                    )
                    return transcript

            except Exception as exc:
                print(
                    "Caption fallback attempt failed:",
                    type(exc).__name__,
                    str(exc),
                )

    return None


def process_input_api(source: str) -> list:
    """
    API-specific input processing.

    Local files continue to use the project's existing processor.
    YouTube URLs first use resilient yt-dlp extraction.
    """
    source = str(source).strip()

    if not source.startswith(("http://", "https://")):
        return process_input(source)

    wav_path = _download_youtube_audio_api(source)

    print("Audio file:", wav_path)
    print("Chunking audio...")

    chunks = chunk_audio(
        wav_path,
        chunk_minutes=10,
    )

    if not chunks:
        raise RuntimeError(
            "YouTube audio was downloaded, but no audio chunks were created."
        )

    print(
        f"Audio ready — {len(chunks)} chunk(s) created."
    )

    return chunks


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

    # IMPORTANT:
    # Frontend can send the transcript so that
    # the backend can rebuild a lost RAG session.

    transcript: Optional[str] = None

    language: Optional[str] = "english"


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


# ============================================================

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


# ============================================================

def error_text(
    error: Exception
) -> str:

    text = str(
        error
    ).strip()


    if not text:

        text = "Unknown error"


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
            detail="Invalid JSON request.",
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
            detail="Please provide a YouTube URL.",
        )


    session_id = str(
        uuid.uuid4()
    )

    caption_transcript = None

    # ========================================================
    # 1. PROCESS INPUT
    # ========================================================

    try:

        print(
            "[1/6] Processing input..."
        )


        try:
            chunks = process_input_api(source)
        except Exception as input_error:
            # YouTube may temporarily require authentication/PO tokens.
            # If that happens, try public captions before failing.
            if (
                _youtube_video_id(source)
                and _youtube_is_auth_error(input_error)
            ):
                print(
                    "YouTube authentication challenge detected."
                )
                print(
                    "Trying public caption fallback..."
                )

                caption_transcript = (
                    _download_public_youtube_transcript(
                        source,
                        language,
                    )
                )

                if caption_transcript:
                    chunks = []
                else:
                    raise
            else:
                raise


        if not chunks and not caption_transcript:

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


        if (
            "caption_transcript" in locals()
            and caption_transcript
            and not chunks
        ):
            transcript = caption_transcript
            print(
                "[2/6] Using public YouTube captions."
            )
        else:
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


    print()
    print("=" * 70)
    print("REELMIND READY")
    print(
        "Session:",
        session_id
    )
    print("=" * 70)
    print()


    # ========================================================
    # RESPONSE
    # ========================================================

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
                detail="No filename was provided.",
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
            detail="No file was provided.",
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


        # ----------------------------------------------------
        # PROCESS
        # ----------------------------------------------------

        chunks = process_input(
            str(file_path)
        )


        if not chunks:

            raise RuntimeError(
                "No audio chunks were produced."
            )


        # ----------------------------------------------------
        # TRANSCRIBE
        # ----------------------------------------------------

        transcript = transcribe_all(

            chunks,

            language,

        )


        if not transcript:

            raise RuntimeError(
                "Transcription returned empty text."
            )


        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        title = generate_title(
            transcript
        )


        summary = summarize(
            transcript
        )


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

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
        # RAG
        # ----------------------------------------------------

        rag_chain = build_rag_chain(

            transcript,

            session_id=session_id,

        )


        # ----------------------------------------------------
        # SAVE SESSION
        # ----------------------------------------------------

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


        print()
        print("=" * 70)
        print("FILE ANALYSIS READY")
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

    print()
    print("=" * 70)
    print("REELMIND CHAT REQUEST")
    print("Session:", request.session_id)
    print("Question:", request.question)
    print("=" * 70)


    # ========================================================
    # FIND EXISTING SESSION
    # ========================================================

    session = sessions.get(
        request.session_id
    )


    if session:

        print(
            "CHAT: Existing session found."
        )


    # ========================================================
    # SESSION RECOVERY
    # ========================================================

    else:

        print(
            "CHAT: Session not found in memory."
        )


        # ----------------------------------------------------
        # RECOVER USING TRANSCRIPT
        # ----------------------------------------------------

        if request.transcript:

            print(
                "CHAT: Transcript supplied."
            )

            print(
                "CHAT: Rebuilding RAG chain..."
            )


            try:

                rag_chain = build_rag_chain(

                    request.transcript,

                    session_id=request.session_id,

                )


                session = {

                    "rag_chain":
                        rag_chain,

                    "transcript":
                        request.transcript,

                    "language":
                        normalize_language(
                            request.language
                        ),

                    "history":
                        [],

                }


                sessions[
                    request.session_id
                ] = session


                print(
                    "CHAT: Session successfully rebuilt."
                )


            except Exception as e:

                print()
                print(
                    "!!! CHAT SESSION RECOVERY ERROR !!!"
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
                        "chat_session_recovery",

                    "error_type":
                        type(e).__name__,

                    "error_message":
                        error_text(e),

                }


        # ----------------------------------------------------
        # NO TRANSCRIPT
        # ----------------------------------------------------

        else:

            print(
                "CHAT: No transcript available for recovery."
            )


            raise HTTPException(

                status_code=404,

                detail=(
                    "This meeting session has expired. "
                    "Please analyze the recording again."
                ),

            )


    # ========================================================
    # QUESTION
    # ========================================================

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


    # ========================================================
    # HISTORY
    # ========================================================

    history = (

        request.history

        if isinstance(
            request.history,
            list
        )

        else []

    )


    # ========================================================
    # ASK RAG
    # ========================================================

    try:

        print(
            "CHAT: Sending question to RAG..."
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

        if "history" not in session:

            session[
                "history"
            ] = []


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


        print(
            "CHAT: Answer generated successfully."
        )


        return {

            "success":
                True,

            "answer":
                answer,

        }


    except Exception as e:

        print()
        print(
            "!!! CHAT ERROR !!!"
        )

        print(
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