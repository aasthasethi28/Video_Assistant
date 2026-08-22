import os
import json
import requests

from dotenv import load_dotenv
from pydub import AudioSegment


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

HF_TOKEN = os.getenv("HF_TOKEN")

HF_WHISPER_MODEL = os.getenv(
    "HF_WHISPER_MODEL",
    "openai/whisper-large-v3",
)

HF_WHISPER_URL = (
    "https://router.huggingface.co/"
    "hf-inference/models/"
    f"{HF_WHISPER_MODEL}"
)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

SARVAM_URL = (
    "https://api.sarvam.ai/speech-to-text"
)

SARVAM_MODEL = os.getenv(
    "SARVAM_MODEL",
    "saaras:v3",
)

# Sarvam REST accepts audio under 30 seconds.
SARVAM_PIECE_SECONDS = 25

# Network timeout for external STT calls.
API_TIMEOUT = int(
    os.getenv("STT_API_TIMEOUT", "180")
)


# ============================================================
# LANGUAGE NORMALIZATION
# ============================================================

def normalize_language(language: str) -> str:

    value = str(
        language or "english"
    ).strip().lower()

    if value in {
        "hinglish",
        "hindi",
        "hi",
        "hi-en",
        "codemix",
        "code-mix",
    }:
        return "hinglish"

    return "english"


# ============================================================
# HUGGING FACE WHISPER API
# ============================================================

def transcribe_chunk_whisper(
    chunk_path: str
) -> str:
    """
    Transcribe one audio chunk using the
    Hugging Face Inference API.

    IMPORTANT:
    This does NOT download Whisper locally.

    The audio is sent to Hugging Face and
    Whisper runs remotely.
    """

    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN is not configured in .env"
        )

    if not os.path.exists(chunk_path):
        raise FileNotFoundError(
            f"Audio chunk not found: {chunk_path}"
        )

    print()
    print("=" * 70)
    print("ENGINE: HUGGING FACE WHISPER API")
    print(f"MODEL: {HF_WHISPER_MODEL}")
    print(f"AUDIO: {chunk_path}")
    print("=" * 70)

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "audio/wav",
        "Accept": "application/json",
    }

    with open(chunk_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    print(
        f"Uploading to Hugging Face: "
        f"{len(audio_bytes) / 1024:.1f} KB"
    )

    response = requests.post(
        HF_WHISPER_URL,
        headers=headers,
        data=audio_bytes,
        timeout=API_TIMEOUT,
    )

    print(
        "Hugging Face status:",
        response.status_code,
    )

    if not response.ok:

        print()
        print("=" * 70)
        print("HUGGING FACE WHISPER API ERROR")
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
        print("=" * 70)

        try:
            detail = response.json()
        except Exception:
            detail = response.text

        raise RuntimeError(
            "Hugging Face Whisper API failed: "
            f"{detail}"
        )

    try:
        result = response.json()
    except Exception:
        raise RuntimeError(
            "Hugging Face returned a non-JSON response: "
            + response.text
        )

    if isinstance(result, dict):

        text = result.get("text")

        if text is None:
            raise RuntimeError(
                "Hugging Face Whisper response did not "
                "contain a 'text' field: "
                + json.dumps(result)
            )

        return str(text).strip()

    raise RuntimeError(
        "Unexpected Hugging Face response: "
        + str(result)
    )


# ============================================================
# SARVAM
# ============================================================

def _send_to_sarvam(
    piece_path: str
) -> str:
    """
    Send one <=25-second WAV piece to Sarvam.

    Hinglish uses Saaras v3 codemix mode so that
    Hindi + English remain naturally code-mixed.
    """

    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is not configured in .env"
        )

    if not os.path.exists(piece_path):
        raise FileNotFoundError(
            f"Sarvam audio piece not found: {piece_path}"
        )

    headers = {
        "api-subscription-key":
            SARVAM_API_KEY
    }

    data = {
        "model": SARVAM_MODEL,
        "mode": "codemix",
    }

    file_size = os.path.getsize(piece_path)

    print(
        f"Sarvam upload: "
        f"{file_size / 1024:.1f} KB"
    )

    with open(
        piece_path,
        "rb"
    ) as audio_file:

        files = {
            "file": (
                os.path.basename(piece_path),
                audio_file,
                "audio/wav",
            )
        }

        response = requests.post(
            SARVAM_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=API_TIMEOUT,
        )

    print(
        "Sarvam status:",
        response.status_code,
    )

    if not response.ok:

        print()
        print("=" * 70)
        print("SARVAM API ERROR")
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
        print("=" * 70)

        raise RuntimeError(
            "Sarvam STT failed "
            f"({response.status_code}): "
            f"{response.text}"
        )

    try:
        result = response.json()
    except Exception:
        raise RuntimeError(
            "Sarvam returned a non-JSON response: "
            + response.text
        )

    transcript = result.get("transcript")

    if transcript is None:
        raise RuntimeError(
            "Sarvam response did not contain "
            "'transcript': "
            + json.dumps(result)
        )

    return str(transcript).strip()


# ============================================================
# SARVAM CHUNKING
# ============================================================

def transcribe_chunk_sarvam(
    chunk_path: str
) -> str:
    """
    Split a chunk into <=25-second pieces and send
    every piece to Sarvam Saaras v3.
    """

    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is not configured in .env"
        )

    print()
    print("=" * 70)
    print("ENGINE: SARVAM AI")
    print("MODEL:", SARVAM_MODEL)
    print("MODE: CODEMIX")
    print(f"AUDIO: {chunk_path}")
    print("=" * 70)

    audio = AudioSegment.from_wav(
        chunk_path
    )

    piece_ms = (
        SARVAM_PIECE_SECONDS * 1000
    )

    total_pieces = (
        len(audio)
        + piece_ms
        - 1
    ) // piece_ms

    print(
        f"Duration: {len(audio) / 1000:.2f}s"
    )

    print(
        f"Sarvam pieces: {total_pieces}"
    )

    transcript_parts = []

    for i, start in enumerate(
        range(
            0,
            len(audio),
            piece_ms,
        )
    ):

        piece = audio[
            start:
            start + piece_ms
        ]

        piece_path = (
            f"{chunk_path}"
            f"_sarvam_{i}.wav"
        )

        piece.export(
            piece_path,
            format="wav",
        )

        try:

            print()
            print(
                f"Sarvam piece "
                f"{i + 1}/{total_pieces}"
            )

            text = _send_to_sarvam(
                piece_path
            )

            if text:
                transcript_parts.append(
                    text
                )
                print(
                    "✓ Sarvam piece complete"
                )
            else:
                print(
                    "⚠ Empty Sarvam result"
                )

        finally:

            if os.path.exists(
                piece_path
            ):
                os.remove(
                    piece_path
                )

    return " ".join(
        transcript_parts
    ).strip()


# ============================================================
# ROUTER
# ============================================================

def transcribe_chunk(
    chunk_path: str,
    language: str = "english",
) -> str:

    language = normalize_language(
        language
    )

    # --------------------------------------------------------
    # HINGLISH -> SARVAM
    # --------------------------------------------------------

    if language == "hinglish":

        return transcribe_chunk_sarvam(
            chunk_path
        )

    # --------------------------------------------------------
    # ENGLISH -> HUGGING FACE WHISPER
    # --------------------------------------------------------

    return transcribe_chunk_whisper(
        chunk_path
    )


# ============================================================
# ALL CHUNKS
# ============================================================

def transcribe_all(
    chunks: list,
    language: str = "english",
) -> str:

    if not chunks:
        print(
            "No audio chunks found."
        )
        return ""

    language = normalize_language(
        language
    )

    engine = (
        "Sarvam Saaras v3"
        if language == "hinglish"
        else "Hugging Face Whisper API"
    )

    print()
    print("=" * 70)
    print("REELMIND TRANSCRIPTION")
    print("LANGUAGE:", language)
    print("ENGINE:", engine)
    print("TOTAL CHUNKS:", len(chunks))
    print("=" * 70)
    print()

    transcript_parts = []

    for i, chunk in enumerate(chunks):

        print(
            f"[{i + 1}/{len(chunks)}] "
            f"Transcribing: {chunk}"
        )

        text = transcribe_chunk(
            chunk,
            language=language,
        )

        if text:

            transcript_parts.append(
                text
            )

            print(
                f"✓ Chunk {i + 1} complete"
            )

        else:

            print(
                f"⚠ Chunk {i + 1} returned empty text"
            )

    full_transcript = " ".join(
        transcript_parts
    ).strip()

    print()
    print("=" * 70)
    print("TRANSCRIPTION COMPLETE")
    print(
        "Characters:",
        len(full_transcript),
    )
    print("=" * 70)

    return full_transcript