from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import (
    build_rag_chain,
    ask_question,
)


load_dotenv()


def run_pipeline(
    source: str,
    language: str = "english"
) -> dict:

    print("\n" + "=" * 60)
    print("STARTING AI VIDEO ASSISTANT")
    print("=" * 60)

    # --------------------------------------------------
    # STEP 1 — AUDIO PROCESSING
    # --------------------------------------------------

    print("\n[1/6] Processing input...")

    chunks = process_input(source)

    print(
        f"Created {len(chunks)} audio chunk(s)."
    )

    # --------------------------------------------------
    # STEP 2 — TRANSCRIPTION
    # --------------------------------------------------

    print("\n[2/6] Transcribing audio...")

    transcript = transcribe_all(
        chunks,
        language=language
    )

    if not transcript:
        raise RuntimeError(
            "Transcription returned empty text."
        )

    print(
        "\nRaw transcription "
        "(first 300 characters):"
    )

    print(transcript[:300])

    # --------------------------------------------------
    # STEP 3 — TITLE + SUMMARY
    # --------------------------------------------------

    print("\n[3/6] Generating title...")

    title = generate_title(
        transcript
    )

    print(
        f"Title generated: {title}"
    )

    print("\nGenerating summary...")

    summary = summarize(
        transcript
    )

    # --------------------------------------------------
    # STEP 4 — MEETING INFORMATION EXTRACTION
    # --------------------------------------------------

    print(
        "\n[4/6] Extracting meeting information..."
    )

    action_items = extract_action_items(
        transcript
    )

    decisions = extract_key_decisions(
        transcript
    )

    questions = extract_questions(
        transcript
    )

    # --------------------------------------------------
    # STEP 5 — BUILD RAG
    # --------------------------------------------------

    print(
        "\n[5/6] Building RAG vector store..."
    )

    rag_chain = build_rag_chain(
        transcript
    )

    print(
        "RAG system ready."
    )

    # --------------------------------------------------
    # STEP 6 — RETURN RESULTS
    # --------------------------------------------------

    print(
        "\n[6/6] Pipeline completed successfully."
    )

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


if __name__ == "__main__":

    # --------------------------------------------------
    # CLI INPUT
    # --------------------------------------------------

    source = input(
        "Enter YouTube URL or local file path: "
    ).strip()

    if not source:
        print("No input provided.")
        exit()

    language = input(
        "Language (english/hinglish): "
    ).strip().lower()

    if not language:
        language = "english"

    if language not in [
        "english",
        "hinglish"
    ]:
        print(
            "Invalid language. "
            "Using english."
        )
        language = "english"

    # --------------------------------------------------
    # RUN PIPELINE
    # --------------------------------------------------

    try:

        result = run_pipeline(
            source,
            language
        )

    except Exception as e:

        print(
            "\n❌ Pipeline failed:"
        )

        print(e)

        raise

    # --------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("AI VIDEO ASSISTANT RESULTS")
    print("=" * 60)

    print(
        f"\n📌 Title:\n"
        f"{result['title']}"
    )

    print(
        f"\n📋 Summary:\n"
        f"{result['summary']}"
    )

    print(
        f"\n✅ Action Items:\n"
        f"{result['action_items']}"
    )

    print(
        f"\n🔑 Key Decisions:\n"
        f"{result['key_decisions']}"
    )

    print(
        f"\n❓ Open Questions:\n"
        f"{result['open_questions']}"
    )

    print("\n" + "=" * 60)

    # --------------------------------------------------
    # RAG CHAT
    # --------------------------------------------------

    print(
        "\n💬 Chat with your meeting"
    )

    print(
        "Type 'exit' to quit.\n"
    )

    rag_chain = result["rag_chain"]

    while True:

        question = input(
            "You: "
        ).strip()

        if question.lower() in [
            "exit",
            "quit",
            "q"
        ]:

            print(
                "👋 Goodbye!"
            )

            break

        if not question:
            continue

        try:

            answer = ask_question(
                rag_chain,
                question
            )

            print(
                f"\n🤖 Assistant: "
                f"{answer}\n"
            )

        except Exception as e:

            print(
                f"\n❌ Could not answer "
                f"the question: {e}\n"
            )