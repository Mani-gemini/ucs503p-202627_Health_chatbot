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
    const emergencyCardsList = document.getElementById('emergencyCardsList');
    const triageButtons = document.querySelectorAll('.btn-triage');

    // Speech Recognition Setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
    }

    function startListening(btn) {
        if (!recognition) {
            alert('Speech recognition is not supported in this browser.');
            return;
        }
        btn.classList.add('listening');
        recognition.start();

        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            chatInput.value = transcript;
            sendBtn.disabled = false;
            btn.classList.remove('listening');
            
            // If it was the modal voice button, close modal and auto-send
            if (btn === modalVoiceBtn) {
                closeModal();
                handleUserMessage(transcript);
                chatInput.value = '';
                sendBtn.disabled = true;
            }
        };

        recognition.onerror = () => btn.classList.remove('listening');
        recognition.onend = () => btn.classList.remove('listening');
    }

    if (voiceBtn) voiceBtn.addEventListener('click', () => startListening(voiceBtn));
    if (modalVoiceBtn) modalVoiceBtn.addEventListener('click', () => startListening(modalVoiceBtn));

    // Emergency Keywords
    const emergencyKeywords = ['emergency', 'heart attack', 'suicide', 'bleeding', 'stroke', 'kill', 'chest pain', 'unconscious', 'poison', 'overdose'];

    // Mock Database for answers
    const mockDatabase = {
        'dengue': {
            text: 'Dengue is a mosquito-borne viral disease. Common symptoms include high fever, headache, body aches, nausea, and rash. It is prevented by avoiding mosquito bites, especially during the day.',
            source: 'WHO — Dengue and severe dengue'
        },
        'tb': {
            text: 'Tuberculosis (TB) is caused by bacteria (Mycobacterium tuberculosis) that most often affect the lungs. TB is spread from person to person through the air when people with lung TB cough, sneeze or spit.',
            source: 'WHO — Tuberculosis Fact Sheet'
        },
        'diabetes': {
            text: 'To help prevent type 2 diabetes and its complications, people should achieve and maintain a healthy body weight, be physically active, eat a healthy diet, and avoid tobacco use.',
            source: 'WHO — Diabetes Key Facts'
        },
        'covid': {
            text: 'COVID-19 is an infectious disease caused by the SARS-CoV-2 virus. Most people infected will experience mild to moderate respiratory illness. Prevention includes vaccination, wearing masks, and hand hygiene.',
            source: 'MoHFW — COVID-19 Guidelines'
        }
    };

    // Auto-resize / state handling for input
    chatInput.addEventListener('input', () => {
        sendBtn.disabled = chatInput.value.trim() === '';
    });

    // Handle suggested chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.textContent;
            handleUserMessage(query);
            // Hide chips after first interaction
            suggestedChipsContainer.style.display = 'none';
        });
    });

    // Handle Quick Service Cards
    document.querySelectorAll('.service-card[data-query]').forEach(card => {
        card.addEventListener('click', () => {
            chatInput.value = card.getAttribute('data-query');
            sendBtn.disabled = false;
            chatInput.focus();
            chatContainer.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // Handle form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (query) {
            handleUserMessage(query);
            chatInput.value = '';
            sendBtn.disabled = true;
            suggestedChipsContainer.style.display = 'none';
        }
    });

    // Modal Logic
    const openModal = () => {
        // Reset to triage view
        modalTriageView.style.display = 'block';
        modalContactsView.style.display = 'none';
        emergencyCardsList.classList.remove('has-highlight');
        document.querySelectorAll('.e-card').forEach(c => c.classList.remove('highlighted'));
        
        emergencyModal.classList.add('active');
    };
    
    const closeModal = () => emergencyModal.classList.remove('active');

    headerEmergencyBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    
    // Close modal on outside click
    emergencyModal.addEventListener('click', (e) => {
        if (e.target === emergencyModal) closeModal();
    });

    // Triage Option Click
    triageButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-type');
            
            // Hide triage, show contacts
            modalTriageView.style.display = 'none';
            modalContactsView.style.display = 'block';
            
            // Highlight relevant card
            emergencyCardsList.classList.add('has-highlight');
            const targetCard = document.getElementById(`card-${type}`);
            if (targetCard) {
                targetCard.classList.add('highlighted');
            }
        });
    });

    // Expose openModal to window so dynamically injected buttons can use it
    window.openEmergencyModal = openModal;

    function handleUserMessage(query) {
        // Append User Message
        appendMessage(query, 'user');
        
        // Check for emergency
        const lowerQuery = query.toLowerCase();
        const isEmergency = emergencyKeywords.some(keyword => lowerQuery.includes(keyword));

        if (isEmergency) {
            // Trigger escalation UI immediately
            appendEmergencyEscalation();
            return;
        }

        // Show typing indicator
        const typingId = appendTypingIndicator();

        // Simulate backend call
        sendMessageToBackend(query).then(response => {
            removeElement(typingId);
            
            if (response.isFallback) {
                appendFallbackMessage(response.text);
            } else {
                appendBotMessage(response.text, response.source);
            }
        });
    }

    // Mock API Call
    function sendMessageToBackend(query) {
        return new Promise((resolve) => {
            const delay = 1000 + Math.random() * 1000; // 1-2s delay
            
            setTimeout(() => {
                const lowerQuery = query.toLowerCase();
                let foundKey = Object.keys(mockDatabase).find(key => lowerQuery.includes(key));
                
                if (foundKey) {
                    resolve({
                        isFallback: false,
                        text: mockDatabase[foundKey].text,
                        source: mockDatabase[foundKey].source
                    });
                } else {
                    resolve({
                        isFallback: true,
                        text: "I could not find verified information regarding your query in my database. As this is a health-awareness tool and not a diagnostic service, I highly recommend consulting a certified doctor or healthcare professional."
                    });
                }
            }, delay);
        });
    }

    // UI Helpers
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

    function appendBotMessage(text, source) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <p>${escapeHTML(text)}</p>
                <div class="source-chip">
                    <i class="ph ph-check"></i>
                    Source: ${escapeHTML(source)}
                </div>
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendFallbackMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message fallback';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="fallback-card">
                    <p>${escapeHTML(text)}</p>
                    <button class="btn-consult-doctor" onclick="window.openEmergencyModal()">Consult a doctor</button>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendEmergencyEscalation() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="ph ph-heartbeat"></i></div>
            <div class="message-content">
                <div class="emergency-card">
                    <h3><i class="ph ph-warning-circle"></i> This sounds urgent</h3>
                    <p>It seems like you might be experiencing a medical emergency. Please seek immediate professional help.</p>
                    <button class="btn-open-emergency" onclick="window.openEmergencyModal()">
                        Open Emergency Help
                    </button>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
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
