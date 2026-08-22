import os

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda


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
        temperature=0.2
    )


def build_chain(system_prompt: str):

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])

    return (
        RunnableLambda(
            lambda x: {"text": x}
        )
        | prompt
        | llm
        | StrOutputParser()
    )


def extract_action_items(transcript: str) -> str:

    chain = build_chain(
        """
You are an expert meeting analyst.

Analyze the meeting transcript and extract ONLY
action items that are explicitly stated or clearly
assigned during the meeting.

For each action item provide:

- Task description
- Owner
- Deadline

Rules:
- Never invent an owner.
- Never invent a deadline.
- If the owner is not mentioned, write "Not specified".
- If the deadline is not mentioned, write "Not specified".
- Do not include general discussion as an action item.

Format the result as a numbered list.

If no action items are found, return:
"No action items found."
"""
    )

    return chain.invoke(transcript)


def extract_key_decisions(transcript: str) -> str:

    chain = build_chain(
        """
You are an expert meeting analyst.

Analyze the meeting transcript and extract ONLY
decisions that were actually made during the meeting.

Do not include:
- Suggestions that were not accepted
- Opinions
- Topics merely discussed
- Possible future decisions

Format the result as a numbered list.

If no key decisions were made, return:
"No key decisions found."
"""
    )

    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:

    chain = build_chain(
        """
You are an expert meeting analyst.

Analyze the meeting transcript and extract:

- Unresolved questions
- Topics requiring clarification
- Issues requiring follow-up
- Information that is still missing

Do not include questions that were already answered
during the meeting.

Format the result as a numbered list.

If no open questions are found, return:
"No open questions found."
"""
    )

    return chain.invoke(transcript)