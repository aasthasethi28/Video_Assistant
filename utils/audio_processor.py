import os
import yt_dlp
from pydub import AudioSegment


DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def download_youtube_audio(url: str) -> str:
    """
    Download only the best available audio from a YouTube URL
    and convert it to WAV.
    """

    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(id)s.%(ext)s"
    )

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],

        "quiet": False,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        video_id = info["id"]

    wav_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.wav"
    )

    if not os.path.exists(wav_path):
        raise FileNotFoundError(
            f"Audio extraction completed but WAV file was not found: {wav_path}"
        )

    return wav_path


def convert_to_wav(input_path: str) -> str:
    """
    Convert any audio/video file to:
    - WAV
    - mono
    - 16 kHz
    """

    output_path = (
        os.path.splitext(input_path)[0]
        + "_converted.wav"
    )

    audio = AudioSegment.from_file(input_path)

    audio = (
        audio
        .set_channels(1)
        .set_frame_rate(16000)
    )

    audio.export(
        output_path,
        format="wav"
    )

    return output_path


def chunk_audio(
    wav_path: str,
    chunk_minutes: int = 10
) -> list:

    audio = AudioSegment.from_wav(wav_path)

    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []

    for i, start in enumerate(
        range(0, len(audio), chunk_ms)
    ):

        chunk = audio[
            start:start + chunk_ms
        ]

        chunk_path = (
            f"{os.path.splitext(wav_path)[0]}"
            f"_chunk_{i}.wav"
        )

        chunk.export(
            chunk_path,
            format="wav"
        )

        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:

    if (
        source.startswith("http://")
        or source.startswith("https://")
    ):

        print(
            "Detected YouTube URL."
        )

        print(
            "Extracting audio..."
        )

        wav_path = download_youtube_audio(
            source
        )

    else:

        print(
            "Detected local file."
        )

        print(
            "Converting to WAV..."
        )

        wav_path = convert_to_wav(
            source
        )

    print(
        f"Audio file: {wav_path}"
    )

    print(
        "Chunking audio..."
    )

    chunks = chunk_audio(
        wav_path,
        chunk_minutes=10
    )

    print(
        f"Audio ready — "
        f"{len(chunks)} chunk(s) created."
    )

    return chunks


if __name__ == "__main__":

    url = (
        "https://www.youtube.com/watch?v=818gGdKTB_U&list=PLxCzCOWd7aiEwaANNt3OqJPVIxwp2ebiT&index=28"
    )

    chunks = process_input(url)

    for chunk in chunks:
        print(chunk)
