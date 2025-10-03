// static/loader.js - v2 (Complete and Self-Contained)
const CHATBOT_SERVER_URL = 'http://15.207.247.255:8000';
const widgetHTML = `
    <div id="chat-toggle-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    </div>

    <div id="chat-widget">
        <div class="widget-header">
            <div class="logo">
                <img src="${CHATBOT_SERVER_URL}/resources/download.png" alt="logo" style="height: 22px; width: 95px; " />
            </div>
           <div class="icon-buttons">
                <svg id="history-button" class="icon-button" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <title>History</title>
                    <path d="M12 8v4l3 3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                    <path d="M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10z" stroke-width="2"></path>
                </svg>
                <svg id="new-chat-button" class="icon-button" width="24" height="24" viewBox="0 0 36 36" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <title>New-Chat</title>
                    <path d="M28,30H6V8H19.22l2-2H6A2,2,0,0,0,4,8V30a2,2,0,0,0,2,2H28a2,2,0,0,0,2-2V15l-2,2Z"></path>
                    <path d="M33.53,5.84,30.16,2.47a1.61,1.61,0,0,0-2.28,0L14.17,16.26l-1.11,4.81A1.61,1.61,0,0,0,14.63,23,1.69,1.69,0,0,0,15,23l4.85-1.07L33.53,8.12A1.61,1.61,0,0,0,33.53,5.84ZM18.81,20.08l-3.66.81L16,17.26,26.32,6.87l2.82,2.82ZM30.27,8.56,27.45,5.74,29,4.16,31.84,7Z"></path>
                </svg>
                <svg id="minimize-button" class="icon-button" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <title>minimize-button</title>
                    <path d="M18 6L6 18" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                    <path d="M6 6L18 18" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                </svg>
            </div>
        </div>

        <div class="chat-view-container">
            <div id="chat-view">
                <div id="chat-box" class="chat-box"></div>
                <div id="welcome-view" class="main-welcome-section">
                    <div class="welcome-header-text" style="margin-bottom: 5px;">
                        <h1>What would you <strong>like</strong> to know?</h1>
                        <p>Use one of the frequently used prompts below or choose your own to begin.</p>
                    </div>
                    <div class="interactive-area">
                        <div class="pills-container"></div>
                         <div class="questions-panels-container"></div>
                    </div>
                </div>
            </div>
            <div id="suggestions-container" class="suggestions-container"></div>
            <div class="chat-input-area">
                <div class="input-box-container">
                    <textarea id="chat-input" placeholder="Describe what you want to know..." rows="1"></textarea>
                    <button id="send-button">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                    </button>
                </div>
            </div>

            <div id="history-view">
                <div class="history-header">
                    <svg id="back-to-chat-button" class="icon-button" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
                        <title>Back</title>
                        <path d="M19 12H5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                        <path d="M12 19L5 12L12 5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                    <h3>Chat History</h3>
                </div>
                <ul id="history-list"></ul>
                <div id="load-more-container" style="padding: 15px; text-align: center; display: none;">
                    <button id="load-more-button">Load More</button>
                </div>
            </div>
        </div>
    </div>
`;

const widgetCSS = `
    /* CSS with hardcoded colors and fixes */
    #chat-toggle-button {
        position: fixed; bottom: 25px; right: 25px; width: 60px; height: 60px;
        background-color: #007BFF; color: white; border: none; border-radius: 50%;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2); z-index: 999;
        transition: transform 0.2s ease, background-color 0.2s ease;
    }
    #chat-toggle-button:hover { background-color: #0056b3; transform: scale(1.1); }
    #chat-widget {
        position: fixed; bottom: 25px; right: 25px; width: 400px; max-width: calc(100% - 40px);
        height: 90vh; max-height: 750px; background-color: #fff; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15), 0 1px 4px rgba(0, 0, 0, 0.1);
        display: flex; flex-direction: column; overflow: hidden; z-index: 1000;
        transform: scale(0.95) translateY(20px); opacity: 0; visibility: hidden;
        transform-origin: bottom right;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease, visibility 0.2s;
        font-family: 'Poppins', sans-serif;
    }
    #chat-widget.open { transform: scale(1) translateY(0); opacity: 1; visibility: visible; }
    .widget-header { background: #fff; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e9ecef; border-radius: 12px 12px 0 0; }
    .widget-header .logo { display: flex; align-items: center; margin-left: 10px; }
    .widget-header .icon-buttons { display: flex; align-items: center; gap: 12px; }
    .widget-header .icon-button { color: #6b7280; cursor: pointer; transition: color 0.2s; }
    .widget-header .icon-button:hover { color: #333; }
    .chat-view-container { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; border-radius: 0 0 12px 12px; background-color: #fff; }
    #chat-view { overflow: hidden; flex-grow: 1; display: flex; flex-direction: column; }
    .chat-box { flex-grow: 1; padding: 20px; overflow-y: auto; background-color: #fdfdfd; height: 0; display: none; }
    .chat-box.active { display: block; }
    .chat-message { display: flex; margin-bottom: 16px; animation: fadeIn 0.4s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .user-message { justify-content: flex-end; }
    .bot-message { justify-content: flex-start; }
    .message-bubble { max-width: 80%; padding: 10px 15px; border-radius: 18px; font-size: 11px; line-height: 1.5; word-wrap: break-word; }
    .bot-message .message-bubble { position: relative; }
    .copy-btn { position: absolute; top: 8px; right: 8px; background: #e9ecef; border: none; border-radius: 4px; cursor: pointer; padding: 4px; display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s ease, background-color 0.2s ease; }
    .bot-message:hover .copy-btn { opacity: 1; }
    .copy-btn:hover { background: #d4dae0; }
    .copy-btn svg { width: 16px; height: 16px; color: #6c757d; }
    .bot-message .message-bubble h1, .bot-message .message-bubble h2, .bot-message .message-bubble h3 { margin-top: 0; margin-bottom: 8px; line-height: 1.3; }
    .bot-message .message-bubble p { margin: 0 0 8px 0; }
    .bot-message .message-bubble ul, .bot-message .message-bubble ol { padding-left: 20px; margin: 0 0 8px 0; }
    .bot-message .message-bubble li { margin-bottom: 4px; }
    .bot-message .message-bubble strong { font-weight: 600; }
    .bot-message .message-bubble a { color: #007BFF; text-decoration: none; }
    .bot-message .message-bubble a:hover { text-decoration: underline; }
    .user-message .message-bubble { background-color: #007BFF; color: #fff; border-bottom-right-radius: 4px; }
    .bot-message .message-bubble {
        background-color: #f1f3f5; /* FIXED COLOR: Light gray for bot messages */
        color: #333; /* Dark text for readability */
        border-bottom-left-radius: 4px;
    }
    .message-bubble.loading .message-content { display: flex; align-items: center; color: #666; font-size: 11px; line-height: 1; }
    .ellipsis-container { position: relative; display: inline-block; width: 1.5em; text-align: left; margin-left: 4px; }
    .ellipsis-container::after { content: '.'; position: absolute; left: 0; bottom: -3px; animation: ellipsis-dots 1.4s infinite; }
    @keyframes ellipsis-dots { 0% { content: '.'; } 33% { content: '..'; } 66%, 100% { content: '...'; } }
    .message-bubble.error { background-color: #dc3545; color: white; }
    .main-welcome-section { padding: 20px 30px 7px 30px; text-align: center; flex-grow: 1; display: flex; flex-direction: column; justify-content: flex-start; background-color: #fff; position: relative; margin-top: 10px; }
    .main-welcome-section h1 { font-family: 'ABeeZee', sans-serif; font-size: 20px; color: #1a202c; font-weight: 800; margin: 10px 0px 7px 0px; }
    .main-welcome-section h1 strong { color: #007bff; }
    .main-welcome-section > .welcome-header-text > p { font-size: 11px; color: #6b7280; margin: 0px; line-height: 1.4; margin-bottom: 5px; }
    .interactive-area { display: flex; flex-grow: 1; }
    .pills-container { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 10px 0; flex-grow: 1; }
    .prompt-row { display: flex; justify-content: center; gap: 10px; }
    .main-welcome-section.pills-stacked .pills-container { width: 120px; min-height: 0; flex-shrink: 0; flex-grow: 0; align-items: stretch; }
    .main-welcome-section.pills-stacked .prompt-row { display: contents; }
    .category-pill { display: flex; align-items: center; justify-content: space-between; padding: 6px 14px; background-color: #fff; border: 1px solid #0073ff; border-radius: 9999px; font-family: 'Poppins', sans-serif; font-size: 11px; font-weight: 600; color: #007BFF; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: transform 0.1s ease, box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease; will-change: transform; }
    .category-pill:hover { outline: none; border-color: #002040; box-shadow: 0 4px 12px rgba(0,0,0,0.1); background-color: #0073ff; color: white; }
    .category-pill:active { transform: scale(0.96); transition-duration: 0.05s; }
    .category-pill.active { border-color: #002040; background-color: #0073ff; font-weight: 600; color: white; }
    .category-pill .chevron { width: 18px; height: 18px; color: #9ca3af; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .category-pill .chevron:hover { color: white; }
    .category-pill.active .chevron { transform: rotate(270deg); color: white; }
    .main-welcome-section.pills-stacked .category-pill { position: relative; transform: none; width: 100%; margin-bottom: -2px; }
    .questions-panels-container { flex-grow: 1; position: relative; padding-left: 0px; opacity: 0; transform: translateX(-10px); transition: opacity 0.25s ease-in-out 0.1s, transform 0.25s ease-in-out 0.1s; }
    .main-welcome-section.pills-stacked .questions-panels-container { opacity: 1; transform: translateX(0); padding-left: 20px; }
    .questions-panel { display: none; flex-direction: column; gap: 8px; background-color: #f8faff; border-radius: 12px; padding: 12px; border: 1px solid #e9ecef; }
    .questions-panel.active { display: flex; }
    .question-link { font-size: 11px; color: #333; padding: 10px 12px; font-weight: 600; border-radius: 10px; cursor: pointer; transition: background-color 0.2s ease, color 0.2s ease; text-align: left; border: none; background-color: rgb(237, 237, 237); width: 100%; }
    .question-link:hover { background-color: #e6f2ff; color: #007BFF; }
    .chat-input-area { flex-shrink: 0; padding: 10px; display: flex; flex-direction: column; background-color: #fff; height: 100px; }
    .input-box-container { display: flex; align-items: center; border: 1px solid #007BFF; border-radius: 10px; padding: 5px; background-color: #f9fafb; box-shadow: 0px 8px 17px #00000026, 0px 0px 2px #0000001f; }
    #chat-input { font-family: 'Inter'; flex-grow: 1; border: none; outline: none; resize: none; font-size: 12px; background: transparent; padding: 8px; min-height: 60px; max-height: 60px; overflow-y: auto; line-height: 1; }
    #send-button { margin-left: 12px; background: none; border: none; color: #007bff; cursor: pointer; padding: 8px; display: flex; align-items: center; justify-content: center; transition: color 0.2s; }
    #send-button:disabled { color: #d1d5db; cursor: not-allowed; }
    .suggestion-message { justify-content: flex-end; }
    .suggestion-bubble { background-color: #ffffff; color: #007BFF; border: 1px solid #007BFF; border-bottom-right-radius: 4px; cursor: pointer; transition: background-color 0.2s ease-in-out; font-size: 10px; padding: 10px 10px; margin-bottom: -10px; }
    .suggestion-bubble:hover { background-color: #007bff97; color: white; }
    #history-view {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: #fff; z-index: 10;
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex; flex-direction: column;
}
#history-view.open { transform: translateX(0); }
.history-header {
    display: flex; align-items: center; padding: 12px 20px;
    border-bottom: 1px solid #e9ecef; flex-shrink: 0;
}
.history-header h3 { margin: 0; margin-left: 16px; font-size: 16px; font-weight: 600; }
#history-list {
    list-style: none; margin: 0; padding: 8px; flex-grow: 1; overflow-y: auto;
}
.history-item {
    padding: 12px 16px; border-bottom: 1px solid #f1f3f5; cursor: pointer;
    transition: background-color 0.2s;
}
.history-item:hover { background-color: #f8f9fa; }
.history-item-title {
    font-size: 14px; font-weight: 500; color: #333;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.history-item-date { font-size: 11px; color: #6b7280; margin-top: 4px; }
.history-item-none {
    text-align: center; color: #999; padding: 20px; font-size: 14px;
}
#load-more-button {
    padding: 8px 20px; border: 1px solid #007BFF;
    background-color: #fff; color: #007BFF;
    border-radius: 20px; cursor: pointer; font-weight: 600;
    transition: background-color 0.2s, color 0.2s;
}
#load-more-button:hover { background-color: #e6f2ff; }
`;

// --- INJECTION AND APPLICATION LOGIC ---
(() => {
    // Helper function to load external scripts and styles
    const loadScript = (src) => new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });

    const loadStyle = (href) => new Promise((resolve, reject) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
    });

    // An array of all external resources your widget needs
    const resources = [
        loadScript("https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
        loadScript("https://cdn.jsdelivr.net/npm/toastify-js"),
        loadStyle("https://cdn.jsdelivr.net/npm/toastify-js/src/toastify.min.css"),
        loadStyle("https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap"),
        loadStyle("https://fonts.googleapis.com/css2?family=ABeeZee:ital@0;1&display=swap"),
        loadStyle("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap")
    ];

    // Wait for all external resources to load before initializing the widget
    Promise.all(resources).then(() => {
        // Create a container on the WMS page for our widget
        const widgetHost = document.createElement('div');
        widgetHost.id = 'holibot-host';
        document.body.appendChild(widgetHost);

        // Use a Shadow DOM to prevent CSS conflicts with the WMS
        const shadowRoot = widgetHost.attachShadow({ mode: 'open' });

        // Inject the CSS into the Shadow DOM
        const style = document.createElement('style');
        style.textContent = widgetCSS;
        shadowRoot.appendChild(style);

        // Inject the HTML into the Shadow DOM
        const wrapper = document.createElement('div');
        wrapper.innerHTML = widgetHTML;
        shadowRoot.appendChild(wrapper);

        // ===================================================================
        // FULLY POPULATED CHATBOT JAVASCRIPT LOGIC (SHADOW DOM SAFE)
        // ===================================================================

        // --- DOM Elements ---
        const chatWidget = shadowRoot.querySelector('#chat-widget');
        const toggleButton = shadowRoot.querySelector('#chat-toggle-button');
        const minimizeButton = shadowRoot.querySelector('#minimize-button');
        const chatBox = shadowRoot.querySelector('#chat-box');
        const welcomeView = shadowRoot.querySelector('#welcome-view');
        const chatInput = shadowRoot.querySelector('#chat-input');
        const sendButton = shadowRoot.querySelector('#send-button');
        const newChatButton = shadowRoot.querySelector('#new-chat-button');
        const suggestionsContainer = shadowRoot.querySelector('#suggestions-container');
        const pillsContainer = welcomeView.querySelector('.pills-container');
        const questionPanelsContainer = welcomeView.querySelector('.questions-panels-container');
        const askedQuestions = new Set();
        const historyButton = shadowRoot.querySelector('#history-button');
        const historyView = shadowRoot.querySelector('#history-view');
        const backToChatButton = shadowRoot.querySelector('#back-to-chat-button');
        const historyList = shadowRoot.querySelector('#history-list');
        const loadMoreContainer = shadowRoot.querySelector('#load-more-container');
        const loadMoreButton = shadowRoot.querySelector('#load-more-button');

        // --- Pill Dropdown Data ---
        const categories = {
            inbound: { label: "Inbound", questions: ["What is a Purchase Order(PO)?", "What is an ASN?", "What is a GRN for?", "What is Putaway?"] },
            masters: { label: "Masters", questions: ["What is the SKU Master?", "What is the Customer Master?", "How do I create a vendor?", "How do I create a custom bin?"] },
            outbound: { label: "Outbound", questions: ["How are Sales Orders managed?", "What does the Shipping process handle?", "What is Picking?", "How do I pack an order on the web?"] },
            inventory: { label: "Inventory", questions: ["How do I view the full inventory?", "What is a cycle count?", "What is Replenishment?", "What is LPN Inventory Management for?"] },
            returns: { label: "Returns", questions: ["how do returns work?", "How do I process a sales return?", "What is the difference between a sales return and a purchase return?"] },
            admin: { label: "Admin", questions: ["How do I create a user?", "How do I create a role?", "How do I configure an automailer?", "explain the approval process"] }
        };

        // --- Config ---
        const API_URL = CHATBOT_SERVER_URL;
        const WMS_API_BASE_URL = 'http://api.your-wms.com';
        const userId = 'holisol_internal_user_01'; // Hardcoded user ID for now
        let historyPage = 1; // For pagination
        let sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        let currentMessages = [];
        const CLIENT_ID = "modicare";

        // --- Widget Visibility ---
        const toggleWidget = (forceOpen = null) => {
            const isOpen = chatWidget.classList.contains('open');
            if (forceOpen === true || (forceOpen === null && !isOpen)) {
                chatWidget.classList.add('open');
                toggleButton.style.display = 'none';
            } else {
                chatWidget.classList.remove('open');
                setTimeout(() => {
                    toggleButton.style.display = 'flex';
                }, 300);
            }
        };
        const fetchAndRenderHistory = async (page = 1) => {
            if (page === 1) {
                historyList.innerHTML = ''; // Clear list only when loading the first page
            }
            loadMoreButton.disabled = true;
            loadMoreButton.textContent = 'Loading...';

            try {
                const response = await fetch(`${API_URL}/history/user/${userId}?page=${page}&size=5`);
                if (!response.ok) throw new Error('Failed to fetch history');
                
                const data = await response.json();

                if (data.chats.length === 0 && page === 1) {
                    historyList.innerHTML = '<li class="history-item-none">No chat history found.</li>';
                }

                data.chats.forEach(chat => {
                    const item = document.createElement('li');
                    item.className = 'history-item';
                    item.dataset.sessionId = chat.session_id;
                    item.innerHTML = `
                        <div class="history-item-title">${chat.title}</div>
                        <div class="history-item-date">${new Date(chat.timestamp).toLocaleString()}</div>
                    `;
                    historyList.appendChild(item);
                });

                if (data.has_more) {
                    loadMoreContainer.style.display = 'block';
                } else {
                    loadMoreContainer.style.display = 'none';
                }
            } catch (e) {
                console.error("Failed to fetch or render chat history:", e);
                historyList.innerHTML = '<li class="history-item-none">Error loading history.</li>';
            } finally {
                loadMoreButton.disabled = false;
                loadMoreButton.textContent = 'Load More';
            }
        };

        const loadConversation = async (id) => {
            try {
                const response = await fetch(`${API_URL}/history/${id}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch chat history from server.");
                }
                const data = await response.json();
                
                if (!data || !data.messages) {
                    throw new Error("Conversation not found or is empty.");
                }

                sessionId = id;
                currentMessages = data.messages;

                chatBox.innerHTML = '';
                welcomeView.style.display = 'none';
                chatBox.classList.add('active');
                
                currentMessages.forEach(msg => {
                    const messageWrapper = appendMessage(msg.sender, msg.text, msg.type, false);
                    if (msg.sender === 'bot') {
                        const copyBtn = messageWrapper.querySelector('.copy-btn');
                        if (copyBtn) copyBtn.style.display = 'flex';
                    }
                });

                historyView.classList.remove('open');
            } catch (e) {
                console.error("Failed to load conversation:", e);
                Toastify({ text: e.message || "Error loading history.", duration: 3000, gravity: "bottom", position: "right", backgroundColor: "#dc3545" }).showToast();
            }
        };

        // --- Chat Functionality ---
        const sendMessage = async (queryOverride) => {
            shadowRoot.querySelectorAll('.suggestion-message').forEach(el => el.remove());
            const query = (queryOverride || chatInput.value).trim();
            if (!query) return;
            askedQuestions.add(query);
            welcomeView.style.display = 'none';
            suggestionsContainer.style.display = 'none';
            chatBox.classList.add('active');
            appendMessage('user', query);
            if (!queryOverride) { chatInput.value = ''; }
            autoResizeInput();
            chatInput.disabled = true;
            sendButton.disabled = true;
            const botMessageWrapper = appendMessage('bot', '', 'loading');
            const botBubble = botMessageWrapper.querySelector('.message-bubble');
            const botContent = botBubble.querySelector('.message-content');
            const copyBtn = botBubble.querySelector('.copy-btn');
            let fullResponse = "";
            try {
                const response = await fetch(`${API_URL}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, session_id: sessionId, client_id: CLIENT_ID, user_id: userId })
                });
                if (!response.ok) throw new Error((await response.json()).detail || 'An error occurred');
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                botBubble.classList.remove('loading');
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    const suggestionDelimiter = 'SUGGESTIONS::';
                    if (fullResponse.includes(suggestionDelimiter)) {
                        const parts = fullResponse.split(suggestionDelimiter);
                        const answerPart = parts[0];
                        const jsonPart = parts[1];
                        botContent.innerHTML = marked.parse(answerPart);
                        try {
                            const suggestions = JSON.parse(jsonPart);
                            renderSuggestions(suggestions.filter(q => !askedQuestions.has(q)));
                        } catch (e) { console.error("Failed to parse suggestions JSON:", e); }
                        fullResponse = answerPart;
                        break;
                    } else {
                        botContent.innerHTML = marked.parse(fullResponse);
                    }
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                if (fullResponse.trim() !== "" && copyBtn) { 
                    copyBtn.style.display = 'flex';
                    const lastMessage = currentMessages[currentMessages.length - 1];
                    if (lastMessage && lastMessage.sender === 'bot') {
                        lastMessage.text = fullResponse;
                        lastMessage.type = 'text';
                    }
                }
            } catch (error) {
                botBubble.classList.remove('loading');
                botBubble.classList.add('error');
                botContent.textContent = error.message;
                if(copyBtn) copyBtn.style.display = 'none';
            } finally {
                chatInput.disabled = false;
                sendButton.disabled = false;
                chatInput.focus();
            }
        };

        const appendMessage = (sender, text, type = 'text', shouldSave = true) => {
            if (shouldSave) {
                currentMessages.push({ sender, text, type });
            }
            const messageWrapper = document.createElement('div');
            messageWrapper.className = `chat-message ${sender}-message`;
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            if (sender === 'user') {
                bubble.textContent = text;
            } else {
                const copyButton = document.createElement('button');
                copyButton.className = 'copy-btn';
                copyButton.title = 'Copy text';
                copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
                bubble.appendChild(copyButton);
                const contentContainer = document.createElement('div');
                contentContainer.className = 'message-content';
                if (type === 'loading') {
                    bubble.classList.add('loading');
                    contentContainer.innerHTML = `<div class="typing-indicator"><span>Thinking</span><span class="ellipsis-container"></span></div>`;
                    copyButton.style.display = 'none';
                } else if (type === 'error') {
                    bubble.classList.add('error');
                    contentContainer.textContent = text;
                    copyButton.style.display = 'none';
                } else {
                    contentContainer.innerHTML = marked.parse(text);
                }
                bubble.appendChild(contentContainer);
            }
            messageWrapper.appendChild(bubble);
            chatBox.appendChild(messageWrapper);
            chatBox.scrollTop = chatBox.scrollHeight;
            return messageWrapper;
        };
        
        const startNewConversation = () => {
            historyView.classList.remove('open');
            sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            currentMessages = [];
            
            welcomeView.classList.remove('pills-stacked');
            shadowRoot.querySelectorAll('.category-pill.active, .questions-panel.active').forEach(el => el.classList.remove('active'));
            setTimeout(() => {
                chatBox.innerHTML = '';
                chatBox.classList.remove('active');
                welcomeView.style.display = 'flex';
                suggestionsContainer.innerHTML = '';
                askedQuestions.clear();
                chatInput.focus();
            }, 400);
        };
        
        const renderSuggestions = (questions) => {
            suggestionsContainer.innerHTML = '';
            if (!questions || questions.length === 0) return;
            const filteredQuestions = questions.filter(q => !askedQuestions.has(q));
            const groupId = `sg-${Date.now()}`;
            filteredQuestions.forEach(q => {
                const messageWrapper = document.createElement('div');
                messageWrapper.className = 'chat-message suggestion-message';
                const bubble = document.createElement('div');
                bubble.className = 'message-bubble suggestion-bubble';
                bubble.dataset.prompt = q;
                bubble.dataset.groupId = groupId;
                bubble.textContent = q;
                messageWrapper.appendChild(bubble);
                chatBox.appendChild(messageWrapper);
            });
        };

        const toggleSendButton = () => { sendButton.disabled = chatInput.value.trim() === ''; };
        
        const autoResizeInput = () => {
            chatInput.style.height = 'auto';
            let newHeight = chatInput.scrollHeight;
            const maxHeight = parseInt(getComputedStyle(chatInput).maxHeight);
            if (newHeight > maxHeight) {
                newHeight = maxHeight;
                chatInput.style.overflowY = 'auto';
            } else {
                chatInput.style.overflowY = 'hidden';
            }
            chatInput.style.height = newHeight + 'px';
        };

        const setupPills = () => {
            const layout = [
                ['inbound', 'masters', 'outbound'],
                ['inventory', 'returns'],
                ['admin']
            ];
            layout.forEach(rowItems => {
                const rowDiv = document.createElement('div');
                rowDiv.className = 'prompt-row';
                rowItems.forEach(key => {
                    const value = categories[key];
                    if (!value) return;
                    const pill = document.createElement('button');
                    pill.className = 'category-pill';
                    pill.dataset.category = key;
                    pill.innerHTML = `<span>${value.label}</span> <svg class="chevron" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`;
                    rowDiv.appendChild(pill);
                });
                pillsContainer.appendChild(rowDiv);
            });
            for (const [key, value] of Object.entries(categories)) {
                const panel = document.createElement('div');
                panel.className = 'questions-panel';
                panel.id = `panel-${key}`;
                value.questions.forEach(q => {
                    const questionBtn = document.createElement('button');
                    questionBtn.className = 'question-link';
                    questionBtn.textContent = q;
                    questionBtn.dataset.prompt = q;
                    panel.appendChild(questionBtn);
                });
                questionPanelsContainer.appendChild(panel);
            }
        };
        
        const handlePillClick = (e) => {
            const clickedPill = e.target.closest('.category-pill');
            if (!clickedPill) return;
            const wasActive = clickedPill.classList.contains('active');
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            const flipAnimate = () => {
                const pills = welcomeView.querySelectorAll('.category-pill');
                const first = Array.from(pills).map(p => p.getBoundingClientRect());
                if(wasActive) {
                    welcomeView.classList.remove('pills-stacked');
                } else {
                    welcomeView.classList.add('pills-stacked');
                }
                const last = Array.from(pills).map(p => p.getBoundingClientRect());
                pills.forEach((pill, i) => {
                    const dx = first[i].left - last[i].left;
                    const dy = first[i].top - last[i].top;
                    pill.style.transition = 'none';
                    pill.style.transform = `translate(${dx}px, ${dy}px)`;
                });
                requestAnimationFrame(() => {
                    pills.forEach(pill => {
                        pill.style.transition = `transform 300ms cubic-bezier(0.34, 1, 0.64, 1)`;
                        pill.style.transform = '';
                    });
                });
            };
            const manageActiveStates = () => {
                const category = clickedPill.dataset.category;
                const targetPanel = shadowRoot.querySelector(`#panel-${category}`);
                const currentlyActivePill = shadowRoot.querySelector('.category-pill.active');
                const currentlyActivePanel = shadowRoot.querySelector('.questions-panel.active');
                if (currentlyActivePill) currentlyActivePill.classList.remove('active');
                if (currentlyActivePanel) currentlyActivePanel.classList.remove('active');
                if(!wasActive) {
                    clickedPill.classList.add('active');
                    if (targetPanel) targetPanel.classList.add('active');
                }
            };
            if (!prefersReducedMotion) {
                flipAnimate();
            } else {
                if (wasActive) {
                    welcomeView.classList.remove('pills-stacked');
                } else {
                    welcomeView.classList.add('pills-stacked');
                }
            }
            manageActiveStates();
        };

        // --- Event Listeners ---
        toggleButton.addEventListener('click', () => toggleWidget(true));
        minimizeButton.addEventListener('click', () => toggleWidget(false));
        chatInput.addEventListener('input', () => { toggleSendButton(); autoResizeInput(); });
        chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendButton.click(); } });
        sendButton.addEventListener('click', () => sendMessage());             
        newChatButton.addEventListener('click', (e) => { e.stopPropagation(); startNewConversation(); });
        pillsContainer.addEventListener('click', handlePillClick);
        questionPanelsContainer.addEventListener('click', (e) => {
            const questionBtn = e.target.closest('.question-link');
            if (questionBtn) sendMessage(questionBtn.dataset.prompt);
        });
        chatWidget.addEventListener('click', (e) => {
            const historyItem = e.target.closest('.history-item');
            if (historyItem && historyItem.dataset.sessionId) {
                loadConversation(historyItem.dataset.sessionId);
                return;
            }
            const suggestionBtn = e.target.closest('.suggestion-bubble');
            const copyButton = e.target.closest('.copy-btn');
            if (suggestionBtn) {
                sendMessage(suggestionBtn.dataset.prompt);
                const groupId = suggestionBtn.dataset.groupId;
                if (groupId) {
                    shadowRoot.querySelectorAll(`.suggestion-bubble[data-group-id="${groupId}"]`).forEach(btn => btn.closest('.suggestion-message').remove());
                }
                return;
            }
            if (copyButton) {
                const contentToCopy = copyButton.closest('.message-bubble').querySelector('.message-content');
                if (contentToCopy) {
                    navigator.clipboard.writeText(contentToCopy.innerText).then(() => {
                        copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                        copyButton.title = 'Copied!';
                        setTimeout(() => {
                            copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
                            copyButton.title = 'Copy text';
                        }, 2000);
                    });
                }
            }
        });

        historyButton.addEventListener('click', () => {
            historyPage = 1;
            fetchAndRenderHistory(historyPage);
            historyView.classList.add('open');
        });

        backToChatButton.addEventListener('click', () => {
            historyView.classList.remove('open');
        });

        loadMoreButton.addEventListener('click', () => {
            historyPage++;
            fetchAndRenderHistory(historyPage);
        });
        
        // Proactive Network Error Listener
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const requestUrl = args[0].toString();
            if (requestUrl.startsWith(WMS_API_BASE_URL)) {
                try {
                    const response = await originalFetch(...args);
                    if (!response.ok) {
                        const responseClone = response.clone();
                        try {
                            const errorBody = await responseClone.json();
                            reportAndAnalyzeError({ endpoint: requestUrl, status_code: response.status, error_body: errorBody });
                        } catch (e) {
                            const errorText = await responseClone.text();
                            reportAndAnalyzeError({ endpoint: requestUrl, status_code: response.status, error_body: { detail: errorText } });
                        }
                    }
                    return response;
                } catch (error) {
                    reportAndAnalyzeError({ endpoint: requestUrl, status_code: 503, error_body: { detail: error.message } });
                    throw error;
                }
            }
            return originalFetch(...args);
        };

        // --- Initial Setup ---
        setupPills();

    }).catch(error => {
        console.error("Holibot failed to load a required resource:", error);
    });
})();