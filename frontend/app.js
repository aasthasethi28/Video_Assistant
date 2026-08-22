(() => {
    "use strict";

    /* ============================================================
       REELMIND FRONTEND
       ============================================================
       Compatible with:
       - frontend/index.html
       - frontend/style.css
       - FastAPI backend on Render
    ============================================================ */


    /* ============================================================
       CONFIG
    ============================================================ */

    const API_BASE = (
        localStorage.getItem("reelmind_api_base") ||
        "https://video-assistant-jzzm.onrender.com"
    ).replace(/\/$/, "");


    /* ============================================================
       STATE
    ============================================================ */

    const state = {
        sourceMode: "url",
        language: "english",
        file: null,
        sessionId: null,
        busy: false,
        stepTimer: null
    };


    /* ============================================================
       HELPERS
    ============================================================ */

    const el = (id) =>
        document.getElementById(id);


    /* ============================================================
       DOM ELEMENTS
    ============================================================ */

    const settingsBtn =
        el("settingsBtn");

    const settingsDrawer =
        el("settingsDrawer");

    const apiBaseInput =
        el("apiBase");

    const saveApiBase =
        el("saveApiBase");

    const statusPill =
        el("statusPill");

    const statusText =
        el("statusText");

    const tabs =
        document.querySelectorAll(".tab");

    const panelUrl =
        el("panel-url");

    const panelFile =
        el("panel-file");

    const sourceUrlInput =
        el("sourceUrl");

    const dropzone =
        el("dropzone");

    const dropzoneText =
        el("dropzoneText");

    const fileInput =
        el("fileInput");

    const langBtns =
        document.querySelectorAll(".lang-btn");

    const runBtn =
        el("runBtn");

    const errorLine =
        el("errorLine");

    const stepsList =
        el("steps");

    const waveform =
        el("waveform");

    const emptyState =
        el("emptyState");

    const results =
        el("results");

    const resultTitle =
        el("resultTitle");

    const outSummary =
        el("outSummary");

    const outActions =
        el("outActions");

    const outDecisions =
        el("outDecisions");

    const outQuestions =
        el("outQuestions");

    const outTranscript =
        el("outTranscript");

    const resultTabs =
        document.querySelectorAll(".rtab");

    const chatDock =
        el("chatDock");

    const chatSession =
        el("chatSession");

    const chatLog =
        el("chatLog");

    const chatForm =
        el("chatForm");

    const chatInput =
        el("chatInput");

    const chatSend =
        el("chatSend");


    /* ============================================================
       INITIAL SETTINGS
    ============================================================ */

    if (apiBaseInput) {
        apiBaseInput.value = API_BASE;
    }


    /* ============================================================
       SETTINGS
    ============================================================ */

    settingsBtn?.addEventListener(
        "click",
        () => {

            const hidden =
                settingsDrawer.hasAttribute(
                    "hidden"
                );

            if (hidden) {
                settingsDrawer.removeAttribute(
                    "hidden"
                );
            } else {
                settingsDrawer.setAttribute(
                    "hidden",
                    ""
                );
            }

            settingsBtn.setAttribute(
                "aria-expanded",
                String(hidden)
            );
        }
    );


    saveApiBase?.addEventListener(
        "click",
        () => {

            const value =
                apiBaseInput.value
                    .trim()
                    .replace(/\/$/, "");

            if (!value) {
                return;
            }

            localStorage.setItem(
                "reelmind_api_base",
                value
            );

            apiBaseInput.value =
                value;

            setStatus(
                "ready",
                "API saved"
            );
        }
    );


    /* ============================================================
       SOURCE TABS
    ============================================================ */

    tabs.forEach(
        (button) => {

            button.addEventListener(
                "click",
                () => {

                    tabs.forEach(
                        (b) => {

                            b.classList.remove(
                                "active"
                            );

                            b.setAttribute(
                                "aria-selected",
                                "false"
                            );
                        }
                    );

                    button.classList.add(
                        "active"
                    );

                    button.setAttribute(
                        "aria-selected",
                        "true"
                    );

                    state.sourceMode =
                        button.dataset.tab;

                    if (panelUrl) {

                        panelUrl.hidden =
                            state.sourceMode !==
                            "url";
                    }

                    if (panelFile) {

                        panelFile.hidden =
                            state.sourceMode !==
                            "file";
                    }

                    clearError();
                }
            );
        }
    );


    /* ============================================================
       FILE INPUT
    ============================================================ */

    fileInput?.addEventListener(
        "change",
        () => {

            if (
                fileInput.files &&
                fileInput.files.length
            ) {

                setFile(
                    fileInput.files[0]
                );
            }
        }
    );


    /* ============================================================
       FILE DROPZONE
    ============================================================ */

    ["dragover", "dragenter"].forEach(
        (eventName) => {

            dropzone?.addEventListener(
                eventName,
                (event) => {

                    event.preventDefault();

                    dropzone.classList.add(
                        "dragover"
                    );
                }
            );
        }
    );


    ["dragleave", "dragend"].forEach(
        (eventName) => {

            dropzone?.addEventListener(
                eventName,
                () => {

                    dropzone.classList.remove(
                        "dragover"
                    );
                }
            );
        }
    );


    dropzone?.addEventListener(
        "drop",
        (event) => {

            event.preventDefault();

            dropzone.classList.remove(
                "dragover"
            );

            const file =
                event.dataTransfer
                    ?.files?.[0];

            if (file) {
                setFile(file);
            }
        }
    );


    /* ============================================================
       FILE HANDLING
    ============================================================ */

    function setFile(file) {

        if (!file) {
            return;
        }

        const valid =
            file.type.startsWith("audio/") ||
            file.type.startsWith("video/");

        if (!valid) {

            showError(
                "Please select a valid audio or video file."
            );

            return;
        }

        state.file =
            file;

        if (dropzoneText) {

            dropzoneText.textContent =
                file.name;
        }

        clearError();

        console.log(
            "Selected file:",
            file.name
        );
    }


    /* ============================================================
       LANGUAGE
    ============================================================ */

    langBtns.forEach(
        (button) => {

            button.addEventListener(
                "click",
                () => {

                    langBtns.forEach(
                        (b) => {

                            b.classList.remove(
                                "active"
                            );

                            b.setAttribute(
                                "aria-checked",
                                "false"
                            );
                        }
                    );

                    button.classList.add(
                        "active"
                    );

                    button.setAttribute(
                        "aria-checked",
                        "true"
                    );

                    state.language =
                        button.dataset.lang ||
                        "english";

                    clearError();

                    console.log(
                        "Language:",
                        state.language
                    );
                }
            );
        }
    );


    /* ============================================================
       STATUS
    ============================================================ */

    function setStatus(
        mode,
        text
    ) {

        if (statusPill) {

            statusPill.classList.remove(
                "busy",
                "ready",
                "err",
                "error"
            );

            if (mode) {

                statusPill.classList.add(
                    mode
                );
            }
        }

        if (statusText) {

            statusText.textContent =
                text;
        }
    }


    /* ============================================================
       ERROR
    ============================================================ */

    function showError(
        message
    ) {

        console.error(
            message
        );

        if (errorLine) {

            errorLine.textContent =
                message;

            errorLine.hidden =
                false;
        }
    }


    function clearError() {

        if (errorLine) {

            errorLine.hidden =
                true;

            errorLine.textContent =
                "";
        }
    }


    /* ============================================================
       PIPELINE
    ============================================================ */

    const STEP_DURATIONS = [
        1200,
        2200,
        1600,
        1600,
        1600,
        1200
    ];


    function resetSteps() {

        if (!stepsList) {
            return;
        }

        stepsList
            .querySelectorAll(".step")
            .forEach(
                (step) => {

                    step.classList.remove(
                        "active",
                        "done",
                        "error"
                    );
                }
            );
    }


    function runStepAnimation() {

        if (!stepsList) {
            return;
        }

        resetSteps();

        waveform?.classList.add(
            "live"
        );

        let current =
            1;

        const advance =
            () => {

                if (
                    current >
                    6
                ) {
                    return;
                }

                const previous =
                    stepsList.querySelector(
                        `.step[data-step="${current - 1}"]`
                    );

                if (previous) {

                    previous.classList.remove(
                        "active"
                    );

                    previous.classList.add(
                        "done"
                    );
                }

                const step =
                    stepsList.querySelector(
                        `.step[data-step="${current}"]`
                    );

                if (step) {

                    step.classList.add(
                        "active"
                    );
                }

                state.stepTimer =
                    setTimeout(
                        () => {

                            current +=
                                1;

                            advance();
                        },
                        STEP_DURATIONS[
                            current - 1
                        ] || 1200
                    );
            };

        advance();
    }


    function finishStepAnimation(
        success
    ) {

        clearTimeout(
            state.stepTimer
        );

        waveform?.classList.remove(
            "live"
        );

        if (!stepsList) {
            return;
        }

        stepsList
            .querySelectorAll(".step")
            .forEach(
                (step) => {

                    step.classList.remove(
                        "active",
                        "error"
                    );

                    if (success) {

                        step.classList.add(
                            "done"
                        );
                    }
                }
            );
    }


    /* ============================================================
       ANALYZE
    ============================================================ */

    runBtn?.addEventListener(
        "click",
        async () => {

            if (state.busy) {
                return;
            }

            clearError();

            let endpoint;
            let options;

            /* -----------------------------------------------
               YOUTUBE / URL
            ----------------------------------------------- */

            if (
                state.sourceMode ===
                "url"
            ) {

                const source =
                    sourceUrlInput
                        ?.value
                        ?.trim();

                if (!source) {

                    showError(
                        "Enter a YouTube URL."
                    );

                    return;
                }

                if (
                    !source.startsWith(
                        "http://"
                    ) &&
                    !source.startsWith(
                        "https://"
                    )
                ) {

                    showError(
                        "Please enter a valid URL starting with http:// or https://."
                    );

                    return;
                }

                endpoint =
                    "/api/analyze";

                options = {

                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                        "Accept":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            source:
                                source,

                            language:
                                state.language
                        })
                };
            }

            /* -----------------------------------------------
               FILE
            ----------------------------------------------- */

            else {

                if (!state.file) {

                    showError(
                        "Choose an audio or video file."
                    );

                    return;
                }

                endpoint =
                    "/api/analyze-file";

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

                options = {

                    method:
                        "POST",

                    body:
                        form
                };
            }


            /* -----------------------------------------------
               START
            ----------------------------------------------- */

            state.busy =
                true;

            runBtn.disabled =
                true;

            runBtn.querySelector(
                ".run-btn-label"
            ).textContent =
                "analyzing…";

            setStatus(
                "busy",
                "processing"
            );

            runStepAnimation();


            try {

                console.log(
                    "REELMIND REQUEST:",
                    API_BASE + endpoint
                );


                const response =
                    await fetch(
                        API_BASE +
                        endpoint,
                        options
                    );


                const data =
                    await response
                        .json()
                        .catch(
                            () => null
                        );


                if (!response.ok) {

                    const detail =
                        data?.detail ||
                        `Request failed (${response.status}).`;

                    throw new Error(
                        detail
                    );
                }


                console.log(
                    "REELMIND RESPONSE:",
                    data
                );


                finishStepAnimation(
                    true
                );


                renderResults(
                    data
                );


                state.sessionId =
                    data.session_id ||
                    null;


                setStatus(
                    "ready",
                    "ready"
                );


            } catch (error) {

                console.error(
                    "ANALYZE ERROR:",
                    error
                );

                finishStepAnimation(
                    false
                );

                setStatus(
                    "error",
                    "error"
                );

                showError(
                    error?.message ||
                    "Unable to analyze the recording."
                );


            } finally {

                state.busy =
                    false;

                runBtn.disabled =
                    false;

                runBtn.querySelector(
                    ".run-btn-label"
                ).textContent =
                    "analyze";
            }
        }
    );


    /* ============================================================
       RESULTS
    ============================================================ */

    function renderResults(
        data
    ) {

        if (emptyState) {

            emptyState.hidden =
                true;
        }

        if (results) {

            results.hidden =
                false;
        }

        if (resultTitle) {

            resultTitle.textContent =
                data.title ||
                "Untitled meeting";
        }

        if (outSummary) {

            outSummary.textContent =
                data.summary ||
                "No summary returned.";
        }

        if (outTranscript) {

            outTranscript.textContent =
                data.transcript ||
                "";
        }

        fillList(
            outActions,
            data.action_items,
            "No action items found."
        );

        fillList(
            outDecisions,
            data.key_decisions,
            "No key decisions found."
        );

        fillList(
            outQuestions,
            data.open_questions,
            "No open questions found."
        );


        state.sessionId =
            data.session_id ||
            null;


        if (state.sessionId) {

            if (chatDock) {

                chatDock.hidden =
                    false;
            }

            if (chatSession) {

                chatSession.textContent =
                    "session · " +
                    state.sessionId
                        .slice(0, 8);
            }

            if (chatInput) {

                chatInput.disabled =
                    false;
            }

            if (chatSend) {

                chatSend.disabled =
                    false;
            }
        }


        /* Result tabs */

        resultTabs.forEach(
            (tab) => {

                tab.addEventListener(
                    "click",
                    () => {

                        resultTabs.forEach(
                            (t) =>
                                t.classList.remove(
                                    "active"
                                )
                        );

                        tab.classList.add(
                            "active"
                        );
                    }
                );
            }
        );
    }


    function fillList(
        container,
        value,
        emptyMessage
    ) {

        if (!container) {
            return;
        }

        container.innerHTML =
            "";

        let items =
            [];

        if (
            Array.isArray(
                value
            )
        ) {

            items =
                value
                    .map(
                        String
                    )
                    .map(
                        (item) =>
                            item.trim()
                    )
                    .filter(
                        Boolean
                    );

        } else if (
            typeof value ===
            "string"
        ) {

            items =
                value
                    .split(
                        /\r?\n/
                    )
                    .map(
                        (item) =>
                            item
                                .replace(
                                    /^[\s\-•*]+/,
                                    ""
                                )
                                .trim()
                    )
                    .filter(
                        Boolean
                    );
        }


        if (!items.length) {

            const li =
                document.createElement(
                    "li"
                );

            li.textContent =
                emptyMessage;

            container.appendChild(
                li
            );

            return;
        }


        items.forEach(
            (item) => {

                const li =
                    document.createElement(
                        "li"
                    );

                li.textContent =
                    item;

                container.appendChild(
                    li
                );
            }
        );
    }


    /* ============================================================
       CHAT
    ============================================================ */

    chatForm?.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            await sendChat();
        }
    );


    chatInput?.addEventListener(
        "keydown",
        async (event) => {

            if (
                event.key ===
                "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                await sendChat();
            }
        }
    );


    chatSend?.addEventListener(
        "click",
        async () => {

            await sendChat();
        }
    );


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

        chatInput.value =
            "";

        addChatMessage(
            "user",
            question
        );

        chatSend &&
            (chatSend.disabled =
                true);


        try {

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
                                "application/json"
                        },

                        body:
                            JSON.stringify({

                                session_id:
                                    state.sessionId,

                                question:
                                    question,

                                language:
                                    state.language,

                                history:
                                    []
                            })
                    }
                );


            const data =
                await response
                    .json()
                    .catch(
                        () => null
                    );


            if (!response.ok) {

                throw new Error(
                    data?.detail ||
                    `Chat failed (${response.status}).`
                );
            }


            addChatMessage(
                "assistant",
                data?.answer ||
                data?.response ||
                data?.message ||
                "I could not generate an answer."
            );


        } catch (error) {

            console.error(
                "CHAT ERROR:",
                error
            );

            addChatMessage(
                "assistant",
                "I couldn't answer that right now. Please try again."
            );

        } finally {

            if (chatSend) {

                chatSend.disabled =
                    false;
            }

            chatInput.focus();
        }
    }


    function addChatMessage(
        role,
        message
    ) {

        if (!chatLog) {
            return;
        }

        const div =
            document.createElement(
                "div"
            );

        div.className =
            role === "user"
                ? "chat-message user-message"
                : "chat-message assistant-message";

        div.textContent =
            message;

        chatLog.appendChild(
            div
        );

        chatLog.scrollTop =
            chatLog.scrollHeight;
    }


    /* ============================================================
       BACKEND HEALTH CHECK
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

            console.log(
                "✓ REELMIND backend connected"
            );

            setStatus(
                null,
                "idle"
            );

        } catch (error) {

            console.warn(
                "Backend health check failed:",
                error
            );

            /*
             * Do not block the UI.
             * Render free instances can sleep.
             */
            setStatus(
                null,
                "idle"
            );
        }
    }


    /* ============================================================
       INITIALIZATION
    ============================================================ */

    document.addEventListener(
        "DOMContentLoaded",
        () => {

            console.log(
                "================================"
            );

            console.log(
                "REELMIND FRONTEND READY"
            );

            console.log(
                "API:",
                API_BASE
            );

            console.log(
                "================================"
            );


            /* Default source */

            if (panelUrl) {
                panelUrl.hidden =
                    false;
            }

            if (panelFile) {
                panelFile.hidden =
                    true;
            }


            /* Default language */

            langBtns.forEach(
                (button) => {

                    if (
                        button.dataset.lang ===
                        "english"
                    ) {

                        button.classList.add(
                            "active"
                        );

                        button.setAttribute(
                            "aria-checked",
                            "true"
                        );
                    }
                }
            );


            /* Chat disabled */

            if (chatInput) {
                chatInput.disabled =
                    true;
            }

            if (chatSend) {
                chatSend.disabled =
                    true;
            }


            /* Backend */

            checkBackend();
        }
    );

})();