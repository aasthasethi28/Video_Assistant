# 🎥 Video Assistant

An AI-powered Video Assistant that transforms long-form video content into structured, searchable, and interactive knowledge.

The application processes video/audio content, generates accurate transcripts, summarizes key information, extracts important decisions and insights, and enables users to interact with the content through an AI-powered conversational interface.

---

## 🚀 Overview

Video Assistant is designed to make long-form video content easier to understand, search, and analyze.

Instead of watching an entire video to find specific information, users can provide a video source and let the system:

- 🎙️ Transcribe the audio
- 📝 Generate an intelligent summary
- 🧠 Extract important insights and decisions
- 🔎 Build a searchable knowledge index
- 💬 Ask questions about the video
- 🌐 Support multilingual and Hinglish interactions
- ⚡ Process long-form content through audio chunking

The project combines **LLMs, speech recognition, RAG, vector databases, and agentic workflows** into a single AI application.

---

## ✨ Key Features

### 🎙️ AI-Powered Transcription

Converts video/audio content into text using modern speech-to-text models and APIs.

### 📝 Intelligent Summarization

Automatically generates concise summaries from lengthy video content while preserving the most important information.

### 🧠 Insight & Decision Extraction

Identifies meaningful:

- Decisions
- Key points
- Action items
- Important discussions
- Insights

from the processed content.

### 🔍 Semantic Search & RAG

The generated transcript is transformed into searchable knowledge using embeddings and vector databases.

Users can ask questions about the video and retrieve relevant information before generating an AI response.

### 💬 Conversational Video Q&A

Users can interact with the processed video through a chat-style interface.

Example:

> "What were the main topics discussed?"

> "What decision was made regarding the project?"

> "Explain the concept discussed in the third section."

### 🌐 Multilingual Support

The application is designed to support multiple speech and interaction languages, including:

- English
- Hinglish
- Indian languages

### 🎧 Long-Form Audio Processing

Long audio files are processed using chunking techniques to make transcription and downstream processing more manageable.

---

## 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │      User Input      │
                    │  Video / Audio URL   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Input Processing   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Audio Extraction │
                    │    & Conversion      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Audio Chunking     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Speech-to-Text    │
                    │      Pipeline        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Transcript Processing │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          ┌────────────┐ ┌────────────┐ ┌────────────┐
          │  Summary   │ │  Insights  │ │ Decisions  │
          └────────────┘ └────────────┘ └────────────┘
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Embedding Model    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Vector Database   │
                    │       / RAG          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Conversational AI  │
                    │       Assistant      │
                    └──────────────────────┘
🌐 **Live Demo:** https://video-assistant-1.onrender.com

📦 **GitHub Repository:** https://github.com/aasthasethi28/Video_Assistant
