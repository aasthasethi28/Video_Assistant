import os

from dotenv import load_dotenv

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter


load_dotenv()


MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


if not MISTRAL_API_KEY:
    raise RuntimeError(
        "MISTRAL_API_KEY is not set. "
        "Add it to your .env file."
    )


def get_llm():

    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=MISTRAL_API_KEY,
        temperature=0.3,
    )


def split_transcript(
    transcript: str
) -> list:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200
    )

    return splitter.split_text(
        transcript
    )


def summarize(
    transcript: str
) -> str:

    if not transcript.strip():
        return "No transcript available."

    llm = get_llm()

    # -----------------------------------------
    # MAP STEP
    # -----------------------------------------

    map_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are an expert meeting summarizer.

Summarize the provided portion of a meeting
transcript concisely.

Include only information explicitly present
in the transcript.

Focus on:
- Main topics discussed
- Important points
- Decisions
- Problems or issues
- Important facts

Do not invent information.
Do not add opinions that are not present.
"""
        ),
        (
            "human",
            "{text}"
        ),
    ])

    map_chain = (
        map_prompt
        | llm
        | StrOutputParser()
    )

    chunks = split_transcript(
        transcript
    )

    chunk_summaries = []

    for i, chunk in enumerate(chunks):

        print(
            f"Summarizing transcript "
            f"chunk {i + 1}/{len(chunks)}..."
        )

        summary = map_chain.invoke({
            "text": chunk
        })

        chunk_summaries.append(
            summary
        )

    combined = "\n\n".join(
        chunk_summaries
    )

    # -----------------------------------------
    # REDUCE STEP
    # -----------------------------------------

    combined_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are an expert meeting summarizer.

Combine the partial summaries into one
professional meeting summary.

Organize the final summary into concise
bullet points.

Focus on:
- Main discussion topics
- Key points
- Important decisions
- Problems/issues
- Outcomes
- Important next steps

Do not invent information.
Use only information contained in the
provided partial summaries.
"""
        ),
        (
            "human",
            "{text}"
        ),
    ])

    combined_chain = (
        combined_prompt
        | llm
        | StrOutputParser()
    )

    return combined_chain.invoke({
        "text": combined
    })


def generate_title(
    transcript: str
) -> str:

    if not transcript.strip():
        return "Untitled Meeting"

    llm = get_llm()

    title_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
Based on the meeting transcript, generate
a short professional meeting title.

Requirements:
- Maximum 8 words
- Clearly represent the main topic
- Professional wording
- Do not use quotation marks
- Return ONLY the title
"""
        ),
        (
            "human",
            "{text}"
        ),
    ])

    title_chain = (
        title_prompt
        | llm
        | StrOutputParser()
    )

    return title_chain.invoke({
        "text": transcript[:2000]
    }).strip()