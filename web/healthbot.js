// HealthBot chat page - API mode (v3). Talks to the FastAPI backend at /api/ask. No mock data.
document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const suggestedChipsContainer = document.getElementById('suggestedChips');
    
    const emergencyModal = document.getElementById('emergencyModal');
    const headerEmergencyBtn = document.getElementById('headerEmergencyBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    
    const voiceBtn = document.getElementById('voiceBtn');
    const modalVoiceBtn = document.getElementById('modalVoiceBtn');
    const modalTriageView = document.getElementById('modalTriageView');
    const modalContactsView = document.getElementById('modalContactsView');
    const modalBackBtn = document.getElementById('modalBackBtn');
    const emergencyCardsList = document.getElementById('emergencyCardsList');
    const triageButtons = document.querySelectorAll('.btn-triage');
    
    const quickServices = document.querySelector('.quick-services');
    const homeBtn = document.getElementById('homeBtn');

    // --- VIEW TOGGLE LOGIC ---
    function switchToChatView() {
        if (quickServices) quickServices.style.display = 'none';
        if (homeBtn) {
            homeBtn.style.visibility = 'visible';
            homeBtn.style.opacity = '1';
        }
    }

    function switchToHomeView() {
        if (quickServices) quickServices.style.display = 'grid'; 
        if (homeBtn) {
            homeBtn.style.visibility = 'hidden';
            homeBtn.style.opacity = '0';
        }
        // Smoothly scroll to top so the user sees the grid clearly
        chatContainer.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (homeBtn) {
        homeBtn.addEventListener('click', switchToHomeView);
    }
    // -------------------------

    // Speech Recognition Setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
    }

    // --- AUDIO MODE (Text-to-Speech + hands-free loop) ---
    let audioModeOn = false;

    // Priority list of pleasant, natural-sounding voices (browser/OS dependent).
    // The first match found in the system's voice list is used.
    const PREFERRED_VOICES = [
        'Google UK English Female',   // Chrome on Windows/Linux — warm British female
        'Samantha',                   // macOS / iOS — clear American female
        'Karen',                      // macOS — friendly Australian female
        'Moira',                      // macOS — Irish female
        'Tessa',                      // macOS — South African female
        'Google US English',          // Chrome fallback — American female
        'Microsoft Zira',             // Windows Edge — American female
        'Microsoft Hazel',            // Windows — British female
    ];

    let _chosenVoice = null;

    function _pickVoice() {
        if (_chosenVoice) return _chosenVoice;
        const voices = window.speechSynthesis.getVoices();
        if (!voices.length) return null;
        // Try preferred names first
        for (const name of PREFERRED_VOICES) {
            const v = voices.find(v => v.name === name);
            if (v) { _chosenVoice = v; return v; }
        }
        // Fall back to the first English-language female voice available
        const femaleEn = voices.find(v =>
            v.lang.startsWith('en') && /female|woman|girl/i.test(v.name)
        );
        if (femaleEn) { _chosenVoice = femaleEn; return femaleEn; }
        // Last resort: any English voice
        const anyEn = voices.find(v => v.lang.startsWith('en'));
        _chosenVoice = anyEn || null;
        return _chosenVoice;
    }

    // Voices load asynchronously on some browsers — reset cache when list changes
    window.speechSynthesis.onvoiceschanged = () => { _chosenVoice = null; };

    function speakText(text) {
        if (!audioModeOn || !window.speechSynthesis) return;
        window.speechSynthesis.cancel(); // stop any previous utterance
        // Strip markdown-style bold markers so they're not read aloud
        const clean = (text || '').replace(/\*\*(.*?)\*\*/g, '$1').trim();
        if (!clean) return;
        const utter = new SpeechSynthesisUtterance(clean);
        utter.lang  = 'en-US';
        utter.rate  = 0.88;   // slightly slower → calmer, easier to follow
        utter.pitch = 1.08;   // just above neutral → warm, approachable tone
        utter.volume = 1.0;
        const voice = _pickVoice();
        if (voice) utter.voice = voice;
        // After the bot finishes speaking, auto-listen so the conversation is hands-free
        utter.onend = () => {
            if (audioModeOn) startListening(voiceBtn);
        };
        window.speechSynthesis.speak(utter);
    }

    const audioModeBtn = document.getElementById('audioModeBtn');
    if (audioModeBtn) {
        audioModeBtn.addEventListener('click', () => {
            audioModeOn = !audioModeOn;
            // Swap icon and style
            const icon = audioModeBtn.querySelector('i');
            if (audioModeOn) {
                audioModeBtn.classList.add('active');
                audioModeBtn.title = 'Audio Mode ON — click to turn off';
                if (icon) { icon.className = 'ph ph-speaker-simple-high'; }
            } else {
                audioModeBtn.classList.remove('active');
                audioModeBtn.title = 'Audio Mode OFF';
                if (icon) { icon.className = 'ph ph-speaker-simple-none'; }
                window.speechSynthesis.cancel(); // stop any in-progress speech immediately
                if (isListening) abortListening(); // stop listening if active
            }
        });
    }

    // --- Voice Recording Toggle & Stop Support ---
    let isListening = false;
    let activeVoiceBtn = null;

    function setListeningState(listening, btn) {
        isListening = listening;
        if (listening) {
            activeVoiceBtn = btn || voiceBtn;
            if (activeVoiceBtn) {
                activeVoiceBtn.classList.add('listening');
                activeVoiceBtn.title = 'Recording... Click to stop (or press Esc)';
                const icon = activeVoiceBtn.querySelector('i');
                if (icon) icon.className = 'ph ph-stop';
            }
            chatInput.placeholder = 'Listening... Speak now, or click stop when done';
        } else {
            [voiceBtn, modalVoiceBtn].forEach(b => {
                if (b) {
                    b.classList.remove('listening');
                    b.title = 'Use Voice Input';
                    const icon = b.querySelector('i');
                    if (icon) icon.className = 'ph ph-microphone';
                }
            });
            chatInput.placeholder = 'Ask about a disease, symptom, or prevention...';
        }
    }

    function stopListening() {
        if (!recognition || !isListening) return;
        setListeningState(false);
        try {
            recognition.stop();
        } catch (e) {
            console.warn('Speech recognition stop warning:', e);
        }
    }

    function abortListening() {
        if (!recognition || !isListening) return;
        setListeningState(false);
        activeVoiceBtn = null;
        try {
            recognition.abort();
        } catch (e) {
            console.warn('Speech recognition abort warning:', e);
        }
    }

    function startListening(btn) {
        if (!recognition) {
            alert('Speech recognition is not supported in this browser.');
            return;
        }
        if (isListening) {
            stopListening();
            return;
        }
        setListeningState(true, btn);
        try {
            recognition.start();
        } catch (e) {
            console.warn('Speech recognition start error:', e);
            setListeningState(false);
            activeVoiceBtn = null;
        }
    }

    function toggleListening(btn) {
        if (isListening) {
            stopListening();
        } else {
            startListening(btn);
        }
    }

    if (recognition) {
        recognition.onresult = (e) => {
            const raw = e.results[0][0].transcript;
            const transcript = cleanVoiceTranscript(raw);
            chatInput.value = transcript;
            sendBtn.disabled = false;
            
            const wasModal = (activeVoiceBtn === modalVoiceBtn);
            setListeningState(false);
            activeVoiceBtn = null;

            // If it was the modal voice button, close modal and auto-send
            if (wasModal) {
                closeModal();
                switchToChatView();
                handleUserMessage(transcript);
                chatInput.value = '';
                sendBtn.disabled = true;
            }
        };

        recognition.onerror = (e) => {
            if (e.error !== 'no-speech' && e.error !== 'aborted') {
                console.warn('Speech recognition error:', e.error);
            }
            setListeningState(false);
            activeVoiceBtn = null;
        };

        recognition.onend = () => {
            setListeningState(false);
            activeVoiceBtn = null;
        };
    }

    if (voiceBtn) voiceBtn.addEventListener('click', () => toggleListening(voiceBtn));
    if (modalVoiceBtn) modalVoiceBtn.addEventListener('click', () => toggleListening(modalVoiceBtn));

    // Cancel recording anytime with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isListening) {
            abortListening();
        }
    });

    // Auto-resize / state handling for input
    chatInput.addEventListener('input', () => {
        sendBtn.disabled = chatInput.value.trim() === '';
    });

    // Handle suggested chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.textContent;
            switchToChatView();
            handleUserMessage(query);
            // Hide chips after first interaction
            suggestedChipsContainer.style.display = 'none';
        });
    });

    // Handle Quick Service Cards
    document.querySelectorAll('.service-card[data-query]').forEach(card => {
        card.addEventListener('click', () => {
            switchToChatView();
            chatInput.value = card.getAttribute('data-query');
            sendBtn.disabled = false;
            chatInput.focus();
            // NOTE: no scrollIntoView() here on purpose — the layout is fixed to the
            // viewport (see style.css), so the chat area is already on screen. Calling
            // scrollIntoView() would shift the outer page's scroll position via JS even
            // though the scrollbar itself is hidden, leaving the header impossible to
            // reach again by hand.
        });
    });

    // Handle Find Nearby Hospital card (uses Geolocation, not the AI pipeline)
    const findHospitalBtn = document.getElementById('findHospitalBtn');
    if (findHospitalBtn) {
        findHospitalBtn.addEventListener('click', handleFindHospital);
    }

    // Handle form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (query) {
            switchToChatView();
            handleUserMessage(query);
            chatInput.value = '';
            sendBtn.disabled = true;
            suggestedChipsContainer.style.display = 'none';
        }
    });

    // Modal Logic
    const showTriageStep = () => {
        modalTriageView.style.display = 'block';
        modalContactsView.style.display = 'none';
        emergencyCardsList.classList.remove('has-highlight');
        document.querySelectorAll('.e-card').forEach(c => c.classList.remove('highlighted'));

        // Triage is the first step of the modal, so there's nothing to go "back" to yet
        if (modalBackBtn) modalBackBtn.classList.remove('is-visible');
    };

    const showContactsStep = (type) => {
        // Hide triage, show contacts
        modalTriageView.style.display = 'none';
        modalContactsView.style.display = 'block';

        // Highlight relevant card
        emergencyCardsList.classList.add('has-highlight');
        const targetCard = document.getElementById(`card-${type}`);
        if (targetCard) {
            targetCard.classList.add('highlighted');
        }

        // Now that we're a step deep, reveal the back button
        if (modalBackBtn) modalBackBtn.classList.add('is-visible');
    };

    const openModal = () => {
        // Reset to triage view every time the modal is (re)opened
        showTriageStep();
        emergencyModal.classList.add('active');
    };
    
    const closeModal = () => emergencyModal.classList.remove('active');

    headerEmergencyBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    if (modalBackBtn) modalBackBtn.addEventListener('click', showTriageStep);
    
    // Close modal on outside click
    emergencyModal.addEventListener('click', (e) => {
        if (e.target === emergencyModal) closeModal();
    });

    // Triage Option Click
    triageButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-type');
            showContactsStep(type);
        });
    });

    // The "Emergency Help" service card (inline onclick removed from index.html)
    const emergencyHelpCard = document.getElementById('emergencyHelpCard');
    if (emergencyHelpCard) emergencyHelpCard.addEventListener('click', openModal);

    // Open the modal and jump straight to the right contact card
    const openEmergencyContacts = (type) => { openModal(); showContactsStep(type); };

    // Kept for backwards compatibility with any other code that calls it
    window.openEmergencyModal = openModal;

    // ---- Real backend call (FastAPI /api/ask). The SERVER decides emergency / answer / fallback. ----
    // Conversation history: last MAX_HISTORY messages kept for multi-turn context.
    const MAX_HISTORY = 6;  // 3 user + 3 assistant turns
    let conversationHistory = [];
    let busy = false;

    async function handleUserMessage(query) {
        if (busy) return;
        busy = true;
        sendBtn.disabled = true;
        appendMessage(query, 'user');
        const typingId = appendTypingIndicator();

        // Snapshot history BEFORE this turn (the current query is the 'question' field, not in history)
        const historySnapshot = conversationHistory.slice();

        try {
            const res = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: query, history: historySnapshot })
            });
            removeElement(typingId);

            if (res.status === 429) {
                const j = await res.json().catch(() => ({}));
                appendMessage(j.detail || 'Too many questions. Please wait a minute and try again.', 'bot');
            } else if (!res.ok) {
                appendMessage('Sorry, something went wrong. Please try again.', 'bot');
            } else {
                const data = await res.json();
                if (data.path === 'emergency') {
                    appendEmergencyEscalation(data.body, data.emergency_kind);
                    // Don't add emergency escalations to history — next question starts fresh
                } else if (data.path === 'fallback') {
                    appendFallbackMessage(data.body);
                    // Record fallback so the bot knows the last topic was out of scope
                    conversationHistory.push({ role: 'user', content: query });
                    conversationHistory.push({ role: 'assistant', content: data.body });
                } else if (data.path === 'answer') {
                    appendBotMessage(data.body, data.sources);
                    // Record successful exchange for follow-up context
                    conversationHistory.push({ role: 'user', content: query });
                    conversationHistory.push({ role: 'assistant', content: data.body });
                } else {
                    // 'error' or 'invalid': the server already wrote a polite message
                    appendMessage(data.body, 'bot');
                }
                // Keep history within the cap
                if (conversationHistory.length > MAX_HISTORY) {
                    conversationHistory = conversationHistory.slice(-MAX_HISTORY);
                }
            }
        } catch (err) {
            removeElement(typingId);
            appendMessage('Could not reach the server. Check that it is running and try again.', 'bot');
        } finally {
            busy = false;
            sendBtn.disabled = chatInput.value.trim() === '';
        }
    }

    // ---- Voice transcript cleanup (improvement #4) ----
    // STT engines often include spoken punctuation words and duplicate words.
    // This normalises the raw transcript before it reaches the AI pipeline.
    function cleanVoiceTranscript(text) {
        if (!text) return '';
        let t = text;

        // Replace spoken punctuation with actual symbols (or remove noise words)
        t = t.replace(/\bcomma\b/gi, ',')
             .replace(/\bfull stop\b/gi, '.')
             .replace(/\bperiod\b/gi, '.')
             .replace(/\bexclamation mark\b/gi, '!')
             .replace(/\bquestion mark\b/gi, '?')
             .replace(/\bnew line\b/gi, ' ')
             .replace(/\bnewline\b/gi, ' ')
             .replace(/\bopen (bracket|parenthesis)\b/gi, '')
             .replace(/\bclose (bracket|parenthesis)\b/gi, '');

        // Remove consecutive duplicate words e.g. "I I have have" → "I have"
        t = t.replace(/\b(\w+)(\s+\1)+\b/gi, '$1');

        // Collapse multiple spaces and trim
        t = t.replace(/\s+/g, ' ').trim();

        // Ensure the first character is capitalised
        if (t.length > 0) t = t.charAt(0).toUpperCase() + t.slice(1);

        return t;
    }

    // UI Helpers
    // Safe formatter for model output: paragraphs, bullet/numbered lists, **bold**. Uses textContent only.
    function addInline(parent, text) {
        text.split(/(\*\*[^*]+\*\*)/g).forEach(part => {
            if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
                const b = document.createElement('strong');
                b.textContent = part.slice(2, -2);
                parent.appendChild(b);
            } else if (part) {
                parent.appendChild(document.createTextNode(part));
            }
        });
    }

    function renderBody(container, text) {
        let list = null, listType = null;
        (text || '').split('\n').forEach(raw => {
            const line = raw.trim();
            if (!line) { list = null; return; }
            const bullet = line.match(/^[-*\u2022]\s+(.*)$/);
            const number = line.match(/^\d+[.)]\s+(.*)$/);
            if (bullet || number) {
                const type = bullet ? 'ul' : 'ol';
                if (!list || listType !== type) {
                    list = document.createElement(type);
                    listType = type;
                    container.appendChild(list);
                }
                const li = document.createElement('li');
                addInline(li, (bullet || number)[1]);
                list.appendChild(li);
            } else {
                list = null;
                const p = document.createElement('p');
                addInline(p, line);
                container.appendChild(p);
            }
        });
    }

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        
        const avatarIcon = sender === 'user' ? 'ph-user' : 'ph-heartbeat';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ${avatarIcon}"></i></div>
            <div class="message-content">
                <p>${escapeHTML(text)}</p>
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendBotMessage(text, sources) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';

        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="answer-bubble"></div>
            </div>
        `;
        const content = msgDiv.querySelector('.message-content');
        renderBody(msgDiv.querySelector('.answer-bubble'), text);

        // One chip per distinct source document (many chunks share one WHO/CDC page)
        const seen = new Set();
        (sources || []).forEach(s => {
            if (!s.source || seen.has(s.source) || seen.size >= 3) return;
            seen.add(s.source);
            const chip = document.createElement('div');
            chip.className = 'source-chip';
            chip.innerHTML = '<i class="ph ph-check"></i>';
            chip.appendChild(document.createTextNode(' Source: ' + s.source));
            content.appendChild(chip);
        });

        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        speakText(text);
    }

    function appendFallbackMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message fallback';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="fallback-card">
                    <p>${escapeHTML(text)}</p>
                    <button class="btn-consult-doctor">Consult a doctor</button>
                </div>
            </div>
        `;
        
        msgDiv.querySelector('.btn-consult-doctor').addEventListener('click', openModal);
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        speakText(text);
    }

    function appendEmergencyEscalation(body, kind) {
        const selfHarm = (kind === 'self_harm');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';

        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="emergency-card">
                    <h3><i class="ph ph-warning-circle"></i> <span class="e-title"></span></h3>
                    <div class="emergency-body"></div>
                    <button class="btn-open-emergency">
                        <span class="e-btn-label"></span>
                    </button>
                </div>
            </div>
        `;
        msgDiv.querySelector('.e-title').textContent = selfHarm ? 'You are not alone' : 'This sounds urgent';
        msgDiv.querySelector('.e-btn-label').textContent = selfHarm ? 'Open Mental Health Helpline' : 'Open Emergency Help';
        renderBody(msgDiv.querySelector('.emergency-body'), body);
        msgDiv.querySelector('.btn-open-emergency').addEventListener('click', () => {
            openEmergencyContacts(selfHarm ? 'mental' : 'ambulance');
        });

        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        speakText(body);
    }

    // ---- Find Nearby Hospital (Geolocation + Google Maps) ----
    function handleFindHospital() {
        switchToChatView();
        suggestedChipsContainer.style.display = 'none';
        appendMessage('Find a nearby hospital', 'user');

        if (!navigator.geolocation) {
            appendMessage(
                'Your browser does not support location access. Please search for hospitals manually on Google Maps.',
                'bot'
            );
            return;
        }

        const typingId = appendTypingIndicator();

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                removeElement(typingId);
                const { latitude, longitude } = pos.coords;
                const mapsUrl =
                    `https://www.google.com/maps/search/hospitals/@${latitude},${longitude},14z`;
                appendHospitalMessage(mapsUrl);
            },
            () => {
                removeElement(typingId);
                // User denied or location unavailable — open generic search
                const fallbackUrl = 'https://www.google.com/maps/search/hospitals+near+me';
                appendHospitalMessage(fallbackUrl, true);
            },
            { timeout: 10000, maximumAge: 60000 }
        );
    }

    function appendHospitalMessage(mapsUrl, isFallback = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';

        const introText = isFallback
            ? "I couldn't access your location. Tap below to search for hospitals near you."
            : 'I found your location! Tap the button below to see hospitals near you on Google Maps.';

        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="answer-bubble">
                    <p></p>
                </div>
                <a href="${mapsUrl}"
                   target="_blank"
                   rel="noopener noreferrer"
                   class="btn-open-emergency"
                   style="display:inline-flex;align-items:center;gap:6px;margin-top:10px;text-decoration:none;">
                    <i class="ph ph-map-pin"></i> Open Nearby Hospitals on Maps
                </a>
            </div>
        `;
        // Use textContent so intro text is safe from XSS
        msgDiv.querySelector('.answer-bubble p').textContent = introText;

        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        speakText(introText);
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';
        msgDiv.id = id;
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        return id;
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});