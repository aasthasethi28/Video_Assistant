/* ============================================================
   REELMIND FRONTEND
   ============================================================
   STT ROUTING:
   English  -> Hugging Face Whisper API
   Hinglish -> Sarvam Saaras v3 / codemix

   API keys are NEVER stored here.
   ============================================================ */

"use strict";


/* ============================================================
   CONFIG
============================================================ */

const API_BASE = (
    localStorage.getItem("reelmind_api_base")
    || "https://video-assistant-jzzm.onrender.com"
).replace(/\/$/, "");


/* ============================================================
   STATE
============================================================ */

const state = {

    sourceType: "url",

    language: "english",

    file: null,

    sessionId: null,

    transcript: "",

    analyzing: false,

    analyzed: false,

    history: [],
};


/* ============================================================
   DOM
============================================================ */

const $ = (id) =>
    document.getElementById(id);


const linkTab =
    $("linkTab");

const uploadTab =
    $("uploadTab");

const linkSource =
    $("linkSource");

const uploadSource =
    $("uploadSource");

const urlInput =
    $("urlInput");

const fileInput =
    $("fileInput");

const uploadBox =
    $("uploadBox");

const selectedFile =
    $("selectedFile");

const englishBtn =
    $("englishBtn");

const hinglishBtn =
    $("hinglishBtn");

const analyzeBtn =
    $("analyzeBtn");

const analyzeText =
    $("analyzeText");

const errorBox =
    $("errorBox");

const statusBadge =
    $("statusBadge");

const statusText =
    $("statusText");

const emptyState =
    $("emptyState");

const results =
    $("results");

const meetingTitle =
    $("meetingTitle");

const transcript =
    $("transcript");

const summary =
    $("summary");

const decisions =
    $("decisions");

const outcomes =
    $("outcomes");

const chatMessages =
    $("chatMessages");

const chatEmpty =
    $("chatEmpty");

const chatForm =
    $("chatForm");

const chatInput =
    $("chatInput");

const sendBtn =
    $("sendBtn");

const sessionLabel =
    $("sessionLabel");

const pipelineSteps =
    document.querySelectorAll(
        ".pipeline-step"
    );

const waveLoader =
    document.querySelector(
        ".wave-loader"
    );


/* ============================================================
   HTML HELPERS
============================================================ */

function escapeHTML(value) {

    return String(
        value ?? ""
    )
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatText(value) {

    return escapeHTML(
        value ?? ""
    ).replaceAll(
        "\n",
        "<br>"
    );
}


/* ============================================================
   STATUS
============================================================ */

function setStatus(
    mode,
    text
) {

    if (!statusBadge) {
        return;
    }

    statusBadge.classList.remove(
        "processing",
        "ready",
        "error"
    );

    if (mode) {

        statusBadge.classList.add(
            mode
        );
    }

    if (statusText) {

        statusText.textContent =
            text;
    }
}


/* ============================================================
   ERROR HANDLING
============================================================ */

function showError(
    message
) {

    console.error(
        message
    );

    if (errorBox) {

        errorBox.textContent =
            String(message);

        errorBox.classList.remove(
            "hidden"
        );

        errorBox.style.display =
            "block";
    }

    setStatus(
        "error",
        "ERROR"
    );
}


function clearError() {

    if (errorBox) {

        errorBox.textContent =
            "";

        errorBox.classList.add(
            "hidden"
        );

        errorBox.style.display =
            "none";
    }
}


async function readError(
    response
) {

    const text =
        await response.text();

    if (!text) {

        return (
            `Request failed (${response.status})`
        );
    }

    try {

        const data =
            JSON.parse(text);

        if (
            typeof data ===
            "string"
        ) {

            return data;
        }

        if (
            typeof data.detail ===
            "string"
        ) {

            return data.detail;
        }

        if (
            Array.isArray(
                data.detail
            )
        ) {

            return data.detail
                .map(
                    (item) => {

                        if (
                            typeof item ===
                            "string"
                        ) {

                            return item;
                        }

                        return (
                            item.msg
                            ||
                            JSON.stringify(
                                item
                            )
                        );
                    }
                )
                .join("\n");
        }

        if (data.message) {

            return data.message;
        }

        if (data.error) {

            return typeof data.error ===
                "string"
                ? data.error
                : JSON.stringify(
                    data.error
                );
        }

        return JSON.stringify(
            data,
            null,
            2
        );

    } catch {

        return text;
    }
}


/* ============================================================
   PIPELINE
============================================================ */

function setPipeline(
    currentStep,
    errorStep = null
) {

    pipelineSteps.forEach(
        (step) => {

            const number =
                Number(
                    step.dataset.step
                );

            step.classList.remove(
                "active",
                "done",
                "error"
            );

            if (
                errorStep &&
                number === errorStep
            ) {

                step.classList.add(
                    "error"
                );

                return;
            }

            if (
                number <
                currentStep
            ) {

                step.classList.add(
                    "done"
                );

            } else if (
                number ===
                currentStep
            ) {

                step.classList.add(
                    "active"
                );
            }
        }
    );
}


function finishPipeline() {

    pipelineSteps.forEach(
        (step) => {

            step.classList.remove(
                "active",
                "error"
            );

            step.classList.add(
                "done"
            );
        }
    );

    waveLoader?.classList.remove(
        "active"
    );
}


/* ============================================================
   SOURCE
============================================================ */

function setSource(
    type
) {

    state.sourceType =
        type;

    const isURL =
        type === "url";

    linkTab?.classList.toggle(
        "active",
        isURL
    );

    uploadTab?.classList.toggle(
        "active",
        !isURL
    );

    linkSource?.classList.toggle(
        "hidden",
        !isURL
    );

    uploadSource?.classList.toggle(
        "hidden",
        isURL
    );

    if (isURL) {

        state.file =
            null;

        if (fileInput) {

            fileInput.value =
                "";
        }

        selectedFile?.classList.add(
            "hidden"
        );
    }
}


/* ============================================================
   LANGUAGE
============================================================ */

function setLanguage(
    language
) {

    state.language =
        language;

    const isEnglish =
        language === "english";

    englishBtn?.classList.toggle(
        "active",
        isEnglish
    );

    hinglishBtn?.classList.toggle(
        "active",
        !isEnglish
    );

    console.log(
        "Selected language:",
        state.language
    );


    if (
        language ===
        "english"
    ) {

        console.log(
            "STT ENGINE: Hugging Face Whisper API"
        );

    } else {

        console.log(
            "STT ENGINE: Sarvam Saaras v3 / codemix"
        );
    }
}


/* ============================================================
   FILE
============================================================ */

function setFile(
    file
) {

    if (!file) {
        return;
    }

    const valid =
        file.type.startsWith(
            "audio/"
        )
        ||
        file.type.startsWith(
            "video/"
        );

    if (!valid) {

        showError(
            "Please select a valid audio or video file."
        );

        return;
    }

    state.file =
        file;

    clearError();

    if (selectedFile) {

        selectedFile.textContent =
            file.name;

        selectedFile.classList.remove(
            "hidden"
        );
    }

    console.log(
        "Selected file:",
        file.name
    );
}


/* ============================================================
   API - YOUTUBE
============================================================ */

async function analyzeURL() {

    const source =
        urlInput?.value?.trim();

    if (!source) {

        throw new Error(
            "Please enter a YouTube URL."
        );
    }

    if (
        !source.startsWith(
            "http://"
        )
        &&
        !source.startsWith(
            "https://"
        )
    ) {

        throw new Error(
            "Please enter a valid URL starting with http:// or https://."
        );
    }

    const payload = {

        source:
            source,

        language:
            state.language,

    };

    console.log(
        "ANALYZE PAYLOAD:",
        payload
    );


    const response =
        await fetch(
            `${API_BASE}/api/analyze`,
            {

                method:
                    "POST",

                headers: {

                    "Content-Type":
                        "application/json",

                    "Accept":
                        "application/json",

                },

                body:
                    JSON.stringify(
                        payload
                    ),

            }
        );


    if (!response.ok) {

        throw new Error(
            await readError(
                response
            )
        );
    }


    return response.json();
}


/* ============================================================
   API - FILE
============================================================ */

async function analyzeFile() {

    if (!state.file) {

        throw new Error(
            "Please choose an audio or video file."
        );
    }


    const form =
        new FormData();


    form.append(
        "file",
        state.file
    );


    form.append(
        "language",
        state.language
    );


    console.log(
        "FILE ANALYSIS"
    );

    console.log(
        "Language:",
        state.language
    );


    const response =
        await fetch(
            `${API_BASE}/api/analyze-file`,
            {

                method:
                    "POST",

                body:
                    form,

            }
        );


    if (!response.ok) {

        throw new Error(
            await readError(
                response
            )
        );
    }


    return response.json();
}


/* ============================================================
   RENDER RESULTS
============================================================ */

function renderResults(
    data
) {

    if (!data) {
        return;
    }


    const title =
        data.title
        ||
        data.video_title
        ||
        "Meeting Analysis";


    const transcriptText =
        data.transcript
        ||
        data.transcription
        ||
        data.text
        ||
        "";


    const summaryText =
        data.summary
        ||
        data.summarization
        ||
        data.overview
        ||
        "";


    const decisionsText =
        data.key_decisions
        ||
        data.decisions
        ||
        "";


    const outcomesText =
        data.action_items
        ||
        data.outcomes
        ||
        "";


    /* --------------------------------------------------------
       IMPORTANT:
       SAVE TRANSCRIPT FOR CHAT SESSION RECOVERY
    -------------------------------------------------------- */

    state.transcript =
        String(
            transcriptText
        );


    /* --------------------------------------------------------
       SHOW RESULTS
    -------------------------------------------------------- */

    emptyState?.classList.add(
        "hidden"
    );

    results?.classList.remove(
        "hidden"
    );


    /* --------------------------------------------------------
       TITLE
    -------------------------------------------------------- */

    if (meetingTitle) {

        meetingTitle.textContent =
            title;
    }


    /* --------------------------------------------------------
       TRANSCRIPT
    -------------------------------------------------------- */

    if (transcript) {

        transcript.innerHTML =
            formatText(
                transcriptText
            );
    }


    /* --------------------------------------------------------
       SUMMARY
    -------------------------------------------------------- */

    if (summary) {

        summary.innerHTML =
            formatText(
                summaryText
            );
    }


    /* --------------------------------------------------------
       DECISIONS
    -------------------------------------------------------- */

    if (decisions) {

        decisions.innerHTML =
            formatText(
                decisionsText
            );
    }


    /* --------------------------------------------------------
       OUTCOMES
    -------------------------------------------------------- */

    if (outcomes) {

        outcomes.innerHTML =
            formatText(
                outcomesText
            );
    }


    /* --------------------------------------------------------
       SESSION
    -------------------------------------------------------- */

    state.sessionId =
        data.session_id
        ||
        data.sessionId
        ||
        data.id
        ||
        null;


    if (sessionLabel) {

        sessionLabel.textContent =
            state.sessionId
                ? `Session: ${state.sessionId}`
                : "No active session";
    }


    state.history = [];


    enableChat();


    console.log(
        "Transcript saved for chat recovery:",
        state.transcript.length,
        "characters"
    );
}


/* ============================================================
   CHAT ENABLE
============================================================ */

function enableChat() {

    const enabled =
        Boolean(
            state.sessionId
        );


    if (chatInput) {

        chatInput.disabled =
            !enabled;
    }


    if (sendBtn) {

        sendBtn.disabled =
            !enabled;
    }
}


/* ============================================================
   CHAT MESSAGE
============================================================ */

function addChatMessage(
    role,
    message
) {

    if (!chatMessages) {
        return;
    }


    chatEmpty?.remove();


    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        role === "user"
            ? "message user-message"
            : "message assistant-message";


    wrapper.innerHTML = `
        <div class="message-content">
            ${formatText(message)}
        </div>
    `;


    chatMessages.appendChild(
        wrapper
    );


    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* ============================================================
   CHAT API
============================================================ */

async function askMeeting(
    question
) {

    if (!state.sessionId) {

        throw new Error(
            "Please analyze the recording first."
        );
    }


    /*
       IMPORTANT:

       transcript is now included.

       If Render restarts the backend and
       the in-memory session disappears,
       main.py can rebuild the RAG session
       using this transcript.
    */

    const payload = {

        session_id:
            state.sessionId,

        question:
            question,

        language:
            state.language,

        history:
            state.history,

        transcript:
            state.transcript,

    };


    console.log(
        "CHAT PAYLOAD:",
        payload
    );


    console.log(
        "CHAT SESSION:",
        state.sessionId
    );


    console.log(
        "CHAT TRANSCRIPT LENGTH:",
        state.transcript.length
    );


    const response =
        await fetch(
            `${API_BASE}/api/chat`,
            {

                method:
                    "POST",

                headers: {

                    "Content-Type":
                        "application/json",

                    "Accept":
                        "application/json",

                },

                body:
                    JSON.stringify(
                        payload
                    ),

            }
        );


    if (!response.ok) {

        throw new Error(
            await readError(
                response
            )
        );
    }


    return response.json();
}


/* ============================================================
   SEND CHAT
============================================================ */

async function sendChat() {

    if (!chatInput) {
        return;
    }


    const question =
        chatInput.value.trim();


    if (!question) {
        return;
    }


    if (!state.sessionId) {

        showError(
            "Analyze a recording before asking questions."
        );

        return;
    }


    clearError();


    chatInput.value =
        "";


    addChatMessage(
        "user",
        question
    );


    state.history.push({

        role:
            "user",

        content:
            question,

    });


    if (sendBtn) {

        sendBtn.disabled =
            true;
    }


    try {

        const result =
            await askMeeting(
                question
            );


        const answer =
            result.answer
            ||
            result.response
            ||
            result.message
            ||
            "I could not generate an answer.";


        addChatMessage(
            "assistant",
            answer
        );


        state.history.push({

            role:
                "assistant",

            content:
                answer,

        });


    } catch (error) {

        console.error(
            "CHAT ERROR:",
            error
        );


        addChatMessage(
            "assistant",
            error?.message
            ||
            "I couldn't answer that right now."
        );


        /*
           If backend reports an expired session,
           keep the transcript in state so the
           next attempt can rebuild it.
        */

        if (
            error?.message
                ?.toLowerCase()
                .includes(
                    "session"
                )
        ) {

            console.warn(
                "Chat session may have expired. Transcript is retained for recovery."
            );
        }


    } finally {

        enableChat();

        chatInput.focus();
    }
}


/* ============================================================
   MAIN ANALYSIS
============================================================ */

async function analyze() {

    if (state.analyzing) {
        return;
    }


    clearError();


    state.analyzing =
        true;


    state.analyzed =
        false;


    state.sessionId =
        null;


    state.transcript =
        "";


    state.history =
        [];


    if (analyzeBtn) {

        analyzeBtn.disabled =
            true;
    }


    if (analyzeText) {

        analyzeText.textContent =
            "ANALYZING...";
    }


    setStatus(
        "processing",
        "PROCESSING"
    );


    waveLoader?.classList.add(
        "active"
    );


    try {

        /* ----------------------------------------------------
           STEP 1
        ---------------------------------------------------- */

        setPipeline(
            1
        );


        let result;


        /* ----------------------------------------------------
           SOURCE
        ---------------------------------------------------- */

        if (
            state.sourceType ===
            "url"
        ) {

            console.log(
                "SOURCE: YouTube URL"
            );


            result =
                await analyzeURL();


        } else {

            console.log(
                "SOURCE: Uploaded file"
            );


            result =
                await analyzeFile();
        }


        /* ----------------------------------------------------
           CHECK BACKEND RESULT
        ---------------------------------------------------- */

        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.error_message
                ||
                result.message
                ||
                "Backend analysis failed."
            );
        }


        /* ----------------------------------------------------
           STEP 2
        ---------------------------------------------------- */

        setPipeline(
            2
        );


        /* ----------------------------------------------------
           STEP 3
        ---------------------------------------------------- */

        setPipeline(
            3
        );


        /* ----------------------------------------------------
           STEP 4
        ---------------------------------------------------- */

        setPipeline(
            4
        );


        /* ----------------------------------------------------
           STEP 5
        ---------------------------------------------------- */

        setPipeline(
            5
        );


        /* ----------------------------------------------------
           STEP 6
        ---------------------------------------------------- */

        setPipeline(
            6
        );


        /* ----------------------------------------------------
           RENDER
        ---------------------------------------------------- */

        renderResults(
            result
        );


        finishPipeline();


        state.analyzed =
            true;


        setStatus(
            "ready",
            "READY"
        );


        console.log(
            "======================================"
        );


        console.log(
            "ANALYSIS COMPLETE"
        );


        console.log(
            "Session:",
            state.sessionId
        );


        console.log(
            "Transcript:",
            state.transcript.length,
            "characters"
        );


        console.log(
            "======================================"
        );


    } catch (error) {

        console.error(
            "ANALYZE ERROR:",
            error
        );


        setPipeline(
            2,
            2
        );


        waveLoader?.classList.remove(
            "active"
        );


        showError(
            error?.message
            ||
            "Analysis failed."
        );


    } finally {

        state.analyzing =
            false;


        if (analyzeBtn) {

            analyzeBtn.disabled =
                false;
        }


        if (analyzeText) {

            analyzeText.textContent =
                "ANALYZE";
        }
    }
}


/* ============================================================
   BACKEND HEALTH
============================================================ */

async function checkBackend() {

    try {

        const response =
            await fetch(
                `${API_BASE}/api/health`
            );


        if (!response.ok) {

            throw new Error(
                "Backend unavailable"
            );
        }


        const data =
            await response.json();


        console.log(
            "✓ REELMIND backend connected",
            data
        );


        setStatus(
            null,
            "IDLE"
        );


    } catch (error) {

        console.warn(
            "Backend health check failed:",
            error
        );


        setStatus(
            "error",
            "OFFLINE"
        );
    }
}


/* ============================================================
   EVENT LISTENERS
============================================================ */

function setupEvents() {

    /* --------------------------------------------------------
       SOURCE TABS
    -------------------------------------------------------- */

    linkTab?.addEventListener(
        "click",
        () => {

            setSource(
                "url"
            );
        }
    );


    uploadTab?.addEventListener(
        "click",
        () => {

            setSource(
                "upload"
            );
        }
    );


    /* --------------------------------------------------------
       UPLOAD
    -------------------------------------------------------- */

    uploadBox?.addEventListener(
        "click",
        () => {

            fileInput?.click();
        }
    );


    fileInput?.addEventListener(
        "change",
        (event) => {

            const file =
                event.target
                    ?.files?.[0];


            setFile(
                file
            );
        }
    );


    /* --------------------------------------------------------
       LANGUAGE
    -------------------------------------------------------- */

    englishBtn?.addEventListener(
        "click",
        () => {

            setLanguage(
                "english"
            );
        }
    );


    hinglishBtn?.addEventListener(
        "click",
        () => {

            setLanguage(
                "hinglish"
            );
        }
    );


    /* --------------------------------------------------------
       ANALYZE
    -------------------------------------------------------- */

    analyzeBtn?.addEventListener(
        "click",
        () => {

            analyze();
        }
    );


    /* --------------------------------------------------------
       CHAT FORM
    -------------------------------------------------------- */

    chatForm?.addEventListener(
        "submit",
        (event) => {

            event.preventDefault();

            sendChat();
        }
    );


    /* --------------------------------------------------------
       ENTER TO SEND
    -------------------------------------------------------- */

    chatInput?.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key ===
                "Enter"
            ) {

                event.preventDefault();

                sendChat();
            }
        }
    );


    /* --------------------------------------------------------
       DRAG & DROP
    -------------------------------------------------------- */

    uploadBox?.addEventListener(
        "dragover",
        (event) => {

            event.preventDefault();

            uploadBox.classList.add(
                "dragging"
            );
        }
    );


    uploadBox?.addEventListener(
        "dragleave",
        () => {

            uploadBox.classList.remove(
                "dragging"
            );
        }
    );


    uploadBox?.addEventListener(
        "drop",
        (event) => {

            event.preventDefault();

            uploadBox.classList.remove(
                "dragging"
            );


            const file =
                event.dataTransfer
                    ?.files?.[0];


            setFile(
                file
            );
        }
    );
}


/* ============================================================
   INITIALIZATION
============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        /* ----------------------------------------------------
           DEFAULT SOURCE
        ---------------------------------------------------- */

        setSource(
            "url"
        );


        /* ----------------------------------------------------
           DEFAULT LANGUAGE
        ---------------------------------------------------- */

        setLanguage(
            "english"
        );


        /* ----------------------------------------------------
           CHAT DISABLED UNTIL ANALYSIS
        ---------------------------------------------------- */

        enableChat();


        /* ----------------------------------------------------
           EVENTS
        ---------------------------------------------------- */

        setupEvents();


        /* ----------------------------------------------------
           BACKEND
        ---------------------------------------------------- */

        checkBackend();


        /* ----------------------------------------------------
           DEBUG INFO
        ---------------------------------------------------- */

        console.log(
            "======================================"
        );


        console.log(
            "REELMIND FRONTEND READY"
        );


        console.log(
            "======================================"
        );


        console.log(
            "STT ROUTING:"
        );


        console.log(
            "English  -> Hugging Face Whisper API"
        );


        console.log(
            "Hinglish -> Sarvam Saaras v3 / codemix"
        );


        console.log(
            "API:",
            API_BASE
        );


        console.log(
            "======================================"
        );
    }
);