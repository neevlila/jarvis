document.addEventListener('DOMContentLoaded', () => {
    const apiBase = window.location.origin;
    
    // --- J.A.R.V.I.S. Audio Sonification Engine (Web Audio API) ---
    let audioCtx = null;
    function initAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
    }
    function playTransmissionSweep() {
        try {
            initAudio();
            if (!audioCtx) return;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.type = 'sine';
            const now = audioCtx.currentTime;
            osc.frequency.setValueAtTime(150, now);
            osc.frequency.exponentialRampToValueAtTime(1200, now + 0.3);
            gain.gain.setValueAtTime(0.1, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
            osc.start(now);
            osc.stop(now + 0.3);
        } catch (e) {}
    }
    function playCompletionChirp() {
        try {
            initAudio();
            if (!audioCtx) return;
            const now = audioCtx.currentTime;
            
            const osc1 = audioCtx.createOscillator();
            const gain1 = audioCtx.createGain();
            osc1.connect(gain1);
            gain1.connect(audioCtx.destination);
            osc1.type = 'triangle';
            osc1.frequency.setValueAtTime(880, now);
            osc1.frequency.exponentialRampToValueAtTime(1320, now + 0.08);
            gain1.gain.setValueAtTime(0.05, now);
            gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
            osc1.start(now);
            osc1.stop(now + 0.08);
            
            const osc2 = audioCtx.createOscillator();
            const gain2 = audioCtx.createGain();
            osc2.connect(gain2);
            gain2.connect(audioCtx.destination);
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(1200, now + 0.08);
            osc2.frequency.exponentialRampToValueAtTime(1800, now + 0.16);
            gain2.gain.setValueAtTime(0.05, now + 0.08);
            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
            osc2.start(now + 0.08);
            osc2.stop(now + 0.16);
        } catch (e) {}
    }
    function playErrorBeep() {
        try {
            initAudio();
            if (!audioCtx) return;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.type = 'sawtooth';
            const now = audioCtx.currentTime;
            osc.frequency.setValueAtTime(180, now);
            osc.frequency.linearRampToValueAtTime(90, now + 0.2);
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
            osc.start(now);
            osc.stop(now + 0.2);
        } catch (e) {}
    }
    function playClickBeep() {
        try {
            initAudio();
            if (!audioCtx) return;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.type = 'sine';
            const now = audioCtx.currentTime;
            osc.frequency.setValueAtTime(900, now);
            gain.gain.setValueAtTime(0.02, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
            osc.start(now);
            osc.stop(now + 0.04);
        } catch (e) {}
    }
    // Setup click sonification for all dashboard buttons
    document.addEventListener('click', (e) => {
        if (e.target && (e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.classList.contains('nav-btn'))) {
            playClickBeep();
        }
    });

    // DOM Elements
    const cpuValue = document.getElementById('cpu-value');
    const cpuFill = document.getElementById('cpu-fill');
    const ramValue = document.getElementById('ram-value');
    const ramFill = document.getElementById('ram-fill');
    
    const arcReactorContainer = document.querySelector('.arc-reactor-container');
    const brandArcReactor = document.getElementById('brand-arc-reactor');
    const statusMode = document.getElementById('status-mode');
    const voiceIndicator = document.getElementById('voice-indicator');
    const launchQrBtn = document.getElementById('launch-qr-btn');
    const launchPptBtn = document.getElementById('launch-ppt-btn');
    const voiceStatusTxt = document.getElementById('voice-status-txt');
    const toggleVoiceBtn = document.getElementById('toggle-voice-btn');
    
    // Initialize 3D Global Intelligence Globe
    let jarvisGlobeInstance = null;
    try {
        if (typeof JarvisGlobalGlobe !== 'undefined' && document.getElementById('globe-viewport-3d')) {
            jarvisGlobeInstance = new JarvisGlobalGlobe('globe-viewport-3d');
            window.jarvisGlobe = jarvisGlobeInstance;
        }
    } catch (e) {
        console.error('[App] Failed to initialize JarvisGlobalGlobe:', e);
    }
    
    const weatherCity = document.getElementById('weather-city');
    const weatherTemp = document.getElementById('weather-temp');
    const weatherDesc = document.getElementById('weather-desc');
    const weatherHumidity = document.getElementById('weather-humidity');
    const weatherWind = document.getElementById('weather-wind');
    
    const weatherSearchInput = document.getElementById('weather-search-input');
    const weatherSearchBtn = document.getElementById('weather-search-btn');
    
    const newsFeedList = document.getElementById('news-feed-list');
    const consoleLogs = document.getElementById('console-logs');
    const commandInput = document.getElementById('command-input');
    const btnSend = document.getElementById('btn-send');
    
    let isTogglingVoice = false;
    let lastLogEntry = { sender: '', text: '', time: 0 };

    // Append log to terminal (with duplicate suppression for rapid double events)
    function appendLog(sender, text, type = 'system-log') {
        const now = Date.now();
        if (lastLogEntry.sender === sender && lastLogEntry.text === text && (now - lastLogEntry.time) < 2000) {
            return;
        }
        lastLogEntry = { sender, text, time: now };

        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        line.innerText = `[${timestamp}] [${sender}] ${text}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Poll System Status
    async function pollStatus() {
        try {
            const res = await fetch(`${apiBase}/api/status`);
            if (!res.ok) throw new Error('Status poll failed');
            const data = await res.json();
            
            // Update resource values if DOM elements exist
            if (cpuValue && data.cpu !== undefined) cpuValue.innerText = `${Math.round(data.cpu)}%`;
            if (cpuFill && data.cpu !== undefined) cpuFill.style.width = `${data.cpu}%`;
            
            if (ramValue && data.ram !== undefined) ramValue.innerText = `${Math.round(data.ram)}%`;
            if (ramFill && data.ram !== undefined) ramFill.style.width = `${data.ram}%`;
            
            // Update drives dynamically
            const drivesContainer = document.getElementById('drives-container');
            if (drivesContainer && data.drives) {
                drivesContainer.innerHTML = '';
                data.drives.forEach(drive => {
                    const driveItem = document.createElement('div');
                    driveItem.className = 'stat-item';
                    driveItem.innerHTML = `
                        <div class="stat-label">
                            <span>DRIVE STABILITY (${drive.device})</span>
                            <span>${Math.round(drive.percent)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${drive.percent}%"></div>
                        </div>
                    `;
                    drivesContainer.appendChild(driveItem);
                });
            }
            
            if (data.paused) {
                if (voiceStatusTxt) voiceStatusTxt.innerText = 'Voice Input Paused';
                if (toggleVoiceBtn) {
                    toggleVoiceBtn.innerText = 'Resume Voice';
                    toggleVoiceBtn.classList.remove('btn-secondary');
                }
                if (voiceIndicator) {
                    voiceIndicator.innerText = 'VOICE RECOGNITION PAUSED';
                    voiceIndicator.className = 'status-indicator offline';
                }
                if (arcReactorContainer) arcReactorContainer.classList.remove('listening');
            } else {
                if (voiceStatusTxt) voiceStatusTxt.innerText = 'Voice Input Active';
                if (toggleVoiceBtn) {
                    toggleVoiceBtn.innerText = 'Pause Voice';
                    toggleVoiceBtn.classList.add('btn-secondary');
                }
                if (voiceIndicator) {
                    voiceIndicator.innerText = 'VOICE RECOGNITION ACTIVE';
                    voiceIndicator.className = 'status-indicator active';
                }
                if (arcReactorContainer && !arcReactorContainer.classList.contains('speaking')) {
                    arcReactorContainer.classList.add('listening');
                }
            }
            
            // Append background notifications to log window
            if (data.notifications && data.notifications.length > 0) {
                data.notifications.forEach(notification => {
                    appendLog('JARVIS', notification, 'assistant-log');
                });
            }
        } catch (err) {
            console.error('Error polling status:', err);
        }
    }

    // Send Command to API
    async function sendCommand(commandText) {
        if (!commandText.trim()) return;
        
        playTransmissionSweep();
        appendLog('USER', commandText, 'user-log');
        commandInput.value = '';
        
        if (arcReactorContainer) {
            arcReactorContainer.classList.remove('listening');
            arcReactorContainer.classList.add('speaking');
        }
        if (statusMode) {
            statusMode.innerText = 'PROCESSING...';
            statusMode.className = 'status-indicator active';
        }
        
        try {
            const res = await fetch(`${apiBase}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: commandText })
            });
            const data = await res.json();
            
            if (data.success) {
                playCompletionChirp();
                appendLog('JARVIS', data.response, 'assistant-log');

                // Handle 3D Global Intelligence Globe location target
                if (data.location_target) {
                    if (jarvisGlobeInstance) {
                        if (data.location_target.action === 'reset') {
                            jarvisGlobeInstance.resetToIdle();
                        } else {
                            jarvisGlobeInstance.locateTarget(data.location_target);
                        }
                    }
                    window.dispatchEvent(new CustomEvent('JARVIS_LOCATION_RESOLVED', { detail: data.location_target }));
                }
                
                // Handle clear/reset chat redirect
                if (data.action === "clear_chat") {
                    setTimeout(() => {
                        location.reload();
                    }, 800);
                }
                
                // Handle redirection to Code Assistant
                if (data.action === "redirect_code_assistant") {
                    setTimeout(() => {
                        if (btnCodeAssistant) {
                            btnCodeAssistant.click();
                            
                            if (data.language && codeLangSelect) {
                                let lang = data.language.toLowerCase().trim();
                                const validLangs = ['python', 'javascript', 'html', 'css', 'cpp', 'java', 'csharp', 'go', 'typescript', 'sql', 'rust'];
                                if (validLangs.includes(lang)) {
                                    codeLangSelect.value = lang;
                                    codeLangSelect.dispatchEvent(new Event('change'));
                                }
                            }
                            
                            if (codeChatInput && data.prompt) {
                                codeChatInput.value = data.prompt;
                                sendCodePrompt();
                            }
                        }
                    }, 500);
                }
                


                // Handle redirection to PPT Creator Modal
                if (data.action === "redirect_ppt_creator") {
                    setTimeout(() => {
                        if (launchPptBtn) {
                            launchPptBtn.click();
                            if (data.topic && pptTopicInput) {
                                pptTopicInput.value = data.topic;
                            }
                        }
                    }, 500);
                }
                
                // Handle redirection to QR Generator Modal
                if (data.action === "redirect_qr_generator") {
                    setTimeout(() => {
                        if (launchQrBtn) {
                            launchQrBtn.click();
                            if (data.text && qrTextInput) {
                                qrTextInput.value = data.text;
                            }
                        }
                    }, 500);
                }
                
                // Handle redirection to Email Assistant Modal
                if (data.action === "redirect_email_assistant") {
                    setTimeout(() => {
                        if (launchEmailBtn) {
                            launchEmailBtn.click();
                            if (data.to && emailToInput) {
                                emailToInput.value = data.to;
                            }
                            if (data.purpose && emailAboutInput) {
                                emailAboutInput.value = data.purpose;
                            }
                        }
                    }, 500);
                }

                if (commandText.toLowerCase().includes('news')) {
                    fetchNews();
                }
                if (commandText.toLowerCase().includes('weather')) {
                    const match = commandText.match(/weather in\s*([a-zA-Z\s]+)/i) || commandText.match(/weather of\s*([a-zA-Z\s]+)/i);
                    if (match) fetchWeather(match[1]);
                }
            } else {
                playErrorBeep();
                appendLog('SYSTEM ERROR', data.error || 'Failed to process command', 'error-log');
            }
        } catch (err) {
            playErrorBeep();
            appendLog('SYSTEM', 'Network connection to mainframe lost.', 'error-log');
            console.error(err);
        } finally {
            setTimeout(() => {
                if (arcReactorContainer) arcReactorContainer.classList.remove('speaking');
                if (statusMode) {
                    statusMode.innerText = 'SECURE MODE';
                    statusMode.className = 'status-indicator online';
                }
                pollStatus();
            }, 1000);
        }
    }

    // Toggle Voice Recognition
    async function toggleVoice() {
        if (isTogglingVoice) return;
        isTogglingVoice = true;
        try {
            const res = await fetch(`${apiBase}/api/toggle_pause`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                appendLog('SYSTEM', data.paused ? 'Voice recognition paused.' : 'Voice recognition resumed.', 'system-log');
            }
        } catch (err) {
            appendLog('SYSTEM', 'Failed to toggle voice state.', 'error-log');
        } finally {
            isTogglingVoice = false;
            pollStatus();
        }
    }

    // Weather widget search and fetch
    async function fetchWeather(city, logSuccess = true) {
        try {
            const res = await fetch(`${apiBase}/api/weather?city=${encodeURIComponent(city)}`);
            if (!res.ok) throw new Error('Weather fetch failed');
            const data = await res.json();
            
            weatherCity.innerText = data.name.toUpperCase();
            weatherTemp.innerText = `${Math.round(data.main.temp)}°C`;
            weatherDesc.innerText = data.weather[0].description.toUpperCase();
            weatherHumidity.innerText = `${data.main.humidity}%`;
            weatherWind.innerText = `${data.wind.speed} m/s`;
            
            localStorage.setItem('last_weather_city', data.name);
            if (logSuccess) {
                appendLog('SYSTEM', `Atmospheric telemetry updated for ${data.name}.`, 'system-log');
            }
        } catch (err) {
            console.error(err);
            if (logSuccess) {
                appendLog('SYSTEM ERROR', `Could not update weather for "${city}".`, 'error-log');
            }
        }
    }

    weatherSearchBtn.addEventListener('click', () => {
        const city = weatherSearchInput.value.trim();
        if (city) {
            fetchWeather(city);
            weatherSearchInput.value = '';
        }
    });

    weatherSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const city = weatherSearchInput.value.trim();
            if (city) {
                fetchWeather(city);
                weatherSearchInput.value = '';
            }
        }
    });

    // News headlines list and overlay details
    let newsArticles = [];
    const newsCategorySelect = document.getElementById('news-category-select');

    async function fetchNews(category = 'general') {
        try {
            newsFeedList.innerHTML = '<div class="news-item-loading">Retrieving latest news headlines...</div>';
            const res = await fetch(`${apiBase}/api/news?category=${encodeURIComponent(category)}`);
            if (!res.ok) throw new Error('News fetch failed');
            const data = await res.json();
            
            if (data.articles && data.articles.length > 0) {
                newsArticles = data.articles;
                newsFeedList.innerHTML = '';
                
                newsArticles.slice(0, 6).forEach((article, index) => {
                    const item = document.createElement('div');
                    item.className = 'news-item';
                    item.style.cursor = 'pointer';
                    item.addEventListener('click', () => showNewsDetail(index));
                    
                    const tNode = document.createElement('span');
                    tNode.className = 'news-title';
                    tNode.innerText = article.title;
                    
                    const sNode = document.createElement('span');
                    sNode.className = 'news-source';
                    sNode.innerText = article.source.name.toUpperCase();
                    
                    item.appendChild(tNode);
                    item.appendChild(sNode);
                    newsFeedList.appendChild(item);
                });
            } else {
                newsFeedList.innerHTML = '<div class="news-item-loading">No active headlines.</div>';
            }
        } catch (err) {
            console.error(err);
            newsFeedList.innerHTML = '<div class="news-item-loading">Failed to load news feed.</div>';
        }
    }

    if (newsCategorySelect) {
        newsCategorySelect.addEventListener('change', (e) => {
            fetchNews(e.target.value);
        });
    }

    const newsModal = document.getElementById('news-modal');
    const newsModalCloseX = document.getElementById('news-modal-close-x');
    const newsModalSource = document.getElementById('news-modal-source');
    const newsModalTitle = document.getElementById('news-modal-title');
    const newsModalDate = document.getElementById('news-modal-date');
    const newsModalDesc = document.getElementById('news-modal-desc');
    const newsModalUrl = document.getElementById('news-modal-url');

    async function showNewsDetail(index) {
        const article = newsArticles[index];
        if (!article) return;
        
        newsModalSource.innerText = article.source.name.toUpperCase();
        newsModalTitle.innerText = article.title;
        newsModalDate.innerText = new Date(article.publishedAt).toLocaleString();
        
        // Show loading summary
        newsModalDesc.innerText = "J.A.R.V.I.S. is compiling news summary...";
        newsModalUrl.href = article.url;
        
        newsModal.classList.add('open');

        try {
            const res = await fetch(`${apiBase}/api/news_summary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: article.title,
                    content: article.description || article.content || ""
                })
            });
            const data = await res.json();
            if (data.success) {
                newsModalDesc.innerText = data.summary;
            } else {
                newsModalDesc.innerText = article.description || article.content || "No details available. Use the source link below to read the full story.";
            }
        } catch (err) {
            console.error(err);
            newsModalDesc.innerText = article.description || article.content || "No details available. Use the source link below to read the full story.";
        }
    }

    newsModalCloseX.addEventListener('click', () => newsModal.classList.remove('open'));
    newsModal.addEventListener('click', (e) => {
        if (e.target === newsModal) newsModal.classList.remove('open');
    });

    // PPT modal controls
    const pptModal = document.getElementById('ppt-modal');
    const pptModalCloseX = document.getElementById('ppt-modal-close-x');
    const pptTopicInput = document.getElementById('ppt-topic-input');
    const pptSlidesInput = document.getElementById('ppt-slides-input');
    const pptThemeSelect = document.getElementById('ppt-theme-select');
    const pptCustomTitlesCheckbox = document.getElementById('ppt-custom-titles');
    const pptTitlesInputs = document.getElementById('ppt-titles-inputs');
    const pptGenerateBtn = document.getElementById('ppt-generate-btn');
    const pptInputGroup = document.getElementById('ppt-input-group');
    const pptResultGroup = document.getElementById('ppt-result-group');
    const pptSavedPath = document.getElementById('ppt-saved-path');
    const pptDownloadBtn = document.getElementById('ppt-download-btn');
    const pptOpenBtn = document.getElementById('ppt-open-btn');
    const pptResetBtn = document.getElementById('ppt-reset-btn');
    let generatedPptPath = '';
    let generatedPptFilename = '';

    const btnPptCard = document.getElementById('btn-ppt');
    if (btnPptCard) {
        btnPptCard.addEventListener('click', () => launchPptBtn.click());
    }

    launchPptBtn.addEventListener('click', (e) => {
        if (e) e.stopPropagation();
        pptTopicInput.value = '';
        pptSlidesInput.value = '6';
        pptThemeSelect.value = 'cyberpunk';
        pptCustomTitlesCheckbox.checked = false;
        pptTitlesInputs.style.display = 'none';
        pptTitlesInputs.innerHTML = '';
        pptInputGroup.style.display = 'flex';
        pptResultGroup.style.display = 'none';
        pptModal.classList.add('open');
        pptTopicInput.focus();
    });

    const closePptModal = () => {
        pptModal.classList.remove('open');
    };

    pptModalCloseX.addEventListener('click', closePptModal);
    pptModal.addEventListener('click', (e) => {
        if (e.target === pptModal) closePptModal();
    });

    function rebuildTitleInputs() {
        pptTitlesInputs.innerHTML = '';
        if (!pptCustomTitlesCheckbox.checked) {
            pptTitlesInputs.style.display = 'none';
            return;
        }
        
        const count = parseInt(pptSlidesInput.value) || 6;
        for (let i = 0; i < count; i++) {
            const div = document.createElement('div');
            div.style.display = 'flex';
            div.style.flexDirection = 'column';
            div.style.gap = '4px';
            div.innerHTML = `
                <span style="font-size: 0.65rem; color: var(--text-secondary);">SLIDE ${i+1} SUBTITLE</span>
                <input type="text" class="ppt-custom-slide-title" placeholder="Slide Title ${i+1}" style="width: 100%; background: rgba(0, 20, 30, 0.4); border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px; border-radius: 6px; outline: none; font-size: 0.8rem;">
            `;
            pptTitlesInputs.appendChild(div);
        }
        pptTitlesInputs.style.display = 'flex';
    }

    pptCustomTitlesCheckbox.addEventListener('change', rebuildTitleInputs);
    pptSlidesInput.addEventListener('change', rebuildTitleInputs);

    pptGenerateBtn.addEventListener('click', async () => {
        const topic = pptTopicInput.value.trim();
        if (!topic) {
            alert('Please enter a presentation topic');
            return;
        }
        
        pptGenerateBtn.disabled = true;
        pptGenerateBtn.innerText = 'GENERATING SLIDES...';
        
        const slideTitles = [];
        if (pptCustomTitlesCheckbox.checked) {
            const inputs = document.querySelectorAll('.ppt-custom-slide-title');
            inputs.forEach((input, index) => {
                slideTitles.push(input.value.trim() || `Slide ${index+1}`);
            });
        }
        
        try {
            const res = await fetch(`${apiBase}/api/generate_ppt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: topic,
                    slide_count: parseInt(pptSlidesInput.value) || 6,
                    theme_name: pptThemeSelect.value,
                    slide_titles: slideTitles
                })
            });
            const data = await res.json();
            
            if (data.success) {
                generatedPptPath = data.path;
                generatedPptFilename = data.filename;
                pptSavedPath.innerText = `Deck Ready: ${data.filename}`;
                pptInputGroup.style.display = 'none';
                pptResultGroup.style.display = 'flex';
                appendLog('JARVIS', `PowerPoint deck successfully generated: ${data.filename}`, 'assistant-log');
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            console.error(err);
            alert('Failed to generate PowerPoint presentation.');
        } finally {
            pptGenerateBtn.disabled = false;
            pptGenerateBtn.innerText = 'GENERATE PRESENTATION';
        }
    });

    if (pptDownloadBtn) {
        pptDownloadBtn.addEventListener('click', () => {
            if (!generatedPptFilename) return;
            window.location.href = `${apiBase}/api/download_file?filename=${encodeURIComponent(generatedPptFilename)}`;
        });
    }

    pptOpenBtn.addEventListener('click', async () => {
        if (!generatedPptPath) return;
        try {
            const res = await fetch(`${apiBase}/api/open_file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: generatedPptPath })
            });
            const d = await res.json();
            if (!d.success && d.error) {
                alert(d.error);
            }
        } catch (e) {
            console.error(e);
        }
    });

    pptResetBtn.addEventListener('click', () => {
        pptTopicInput.value = '';
        pptSlidesInput.value = '6';
        pptThemeSelect.value = 'cyberpunk';
        pptCustomTitlesCheckbox.checked = false;
        pptTitlesInputs.style.display = 'none';
        pptTitlesInputs.innerHTML = '';
        pptInputGroup.style.display = 'flex';
        pptResultGroup.style.display = 'none';
        pptTopicInput.focus();
    });

    // QR Modal Controls
    const qrModal = document.getElementById('qr-modal');
    const qrModalCloseX = document.getElementById('qr-modal-close-x');
    const qrTextInput = document.getElementById('qr-text-input');
    const qrGenerateBtn = document.getElementById('qr-generate-btn');
    const qrInputGroup = document.getElementById('qr-input-group');
    const qrResultGroup = document.getElementById('qr-result-group');
    const qrImgPreview = document.getElementById('qr-img-preview');
    const qrSavedPath = document.getElementById('qr-saved-path');
    const qrDownloadBtn = document.getElementById('qr-download-btn');
    const qrResetBtn = document.getElementById('qr-reset-btn');
    let qrImageData = '';
    let qrFilename = '';

    const btnQrCard = document.getElementById('btn-qr');
    if (btnQrCard) {
        btnQrCard.addEventListener('click', () => launchQrBtn.click());
    }

    launchQrBtn.addEventListener('click', (e) => {
        if (e) e.stopPropagation();
        qrTextInput.value = '';
        qrInputGroup.style.display = 'block';
        qrResultGroup.style.display = 'none';
        qrModal.classList.add('open');
        qrTextInput.focus();
    });

    const closeQrModal = () => {
        qrModal.classList.remove('open');
    };

    qrModalCloseX.addEventListener('click', closeQrModal);
    qrModal.addEventListener('click', (e) => {
        if (e.target === qrModal) closeQrModal();
    });

    qrGenerateBtn.addEventListener('click', async () => {
        const text = qrTextInput.value.trim();
        if (!text) {
            alert('Please enter text or URL');
            return;
        }
        
        qrGenerateBtn.disabled = true;
        qrGenerateBtn.innerText = 'GENERATING...';
        
        try {
            const res = await fetch(`${apiBase}/api/generate_qr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            const data = await res.json();
            
            if (data.success) {
                qrImageData = data.image;
                qrFilename = data.filename;
                qrImgPreview.src = data.image;
                qrSavedPath.innerText = ''; // Don't show saved path yet
                
                qrInputGroup.style.display = 'none';
                qrResultGroup.style.display = 'block';
                appendLog('JARVIS', 'QR Code successfully generated.', 'assistant-log');
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            console.error(err);
            alert('Failed to generate QR Code.');
        } finally {
            qrGenerateBtn.disabled = false;
            qrGenerateBtn.innerText = 'GENERATE QR CODE';
        }
    });

    qrDownloadBtn.addEventListener('click', async () => {
        if (!qrImageData) return;
        
        // Save locally on server
        try {
            const res = await fetch(`${apiBase}/api/save_qr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: qrImageData, filename: qrFilename })
            });
            const data = await res.json();
            if (data.success) {
                qrSavedPath.innerText = `Saved locally: ${qrFilename}`;
                appendLog('JARVIS', `QR Code successfully saved as ${qrFilename}`, 'assistant-log');
            } else {
                console.error("Failed to save QR code on server:", data.error);
            }
        } catch (err) {
            console.error("Error calling save_qr API:", err);
        }

        // Trigger browser download
        const link = document.createElement('a');
        link.href = qrImageData;
        link.download = qrFilename || 'qr_code.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    qrResetBtn.addEventListener('click', () => {
        qrTextInput.value = '';
        qrInputGroup.style.display = 'block';
        qrResultGroup.style.display = 'none';
        qrTextInput.focus();
    });

    // ── Mic Button – browser Web Speech API ──────────────────────────────────
    const btnMic = document.getElementById('btn-mic');
    if (btnMic) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            btnMic.title = 'Voice input not supported in this browser. Please use Chrome or Edge.';
            btnMic.style.opacity = '0.4';
            btnMic.addEventListener('click', () => {
                appendLog('SYSTEM', 'Voice input requires Web Speech API (supported in Google Chrome & Microsoft Edge).', 'error-log');
            });
        } else {
            let recognition = null;
            let micActive = false;
            let spokenFinalCommand = '';

            const initRecognition = () => {
                const rec = new SpeechRecognition();
                rec.lang = navigator.language || (navigator.languages && navigator.languages[0]) || 'en-US';
                rec.continuous = false;
                rec.interimResults = true;
                rec.maxAlternatives = 1;

                rec.onstart = () => {
                    micActive = true;
                    spokenFinalCommand = '';
                    btnMic.classList.add('listening');
                    if (commandInput) {
                        commandInput.placeholder = '🎙️ Listening to your voice... Speak now';
                    }
                    const sidebarVoiceStatus = document.getElementById('sidebar-voice-status');
                    if (sidebarVoiceStatus) {
                        sidebarVoiceStatus.innerText = 'RECORDING...';
                        sidebarVoiceStatus.style.color = 'var(--accent-color)';
                    }
                    appendLog('SYSTEM', '🎙️ Microphone engaged. Listening for instructions…', 'system-log');
                };

                rec.onresult = (event) => {
                    let accumulatedTranscript = '';
                    for (let i = 0; i < event.results.length; i++) {
                        const res = event.results[i];
                        if (res && res[0] && res[0].transcript) {
                            accumulatedTranscript += res[0].transcript;
                        }
                    }
                    accumulatedTranscript = accumulatedTranscript.trim();
                    if (accumulatedTranscript && commandInput) {
                        commandInput.value = accumulatedTranscript;
                    }

                    // Check for final recognition flag
                    for (let i = 0; i < event.results.length; i++) {
                        if (event.results[i].isFinal) {
                            spokenFinalCommand = accumulatedTranscript;
                            break;
                        }
                    }
                };

                rec.onerror = (event) => {
                    let msg = 'Voice recognition error.';
                    if (event.error === 'no-speech') {
                        msg = 'No speech detected. Please speak closer to your microphone.';
                    } else if (event.error === 'audio-capture') {
                        msg = 'Microphone hardware not detected. Please verify your microphone settings.';
                    } else if (event.error === 'not-allowed') {
                        msg = 'Microphone access denied. Please allow microphone permission in your browser URL bar.';
                    } else if (event.error === 'network') {
                        msg = 'Network connection issue contacting speech recognition services.';
                    } else {
                        msg = `Voice recognition error: ${event.error}`;
                    }
                    appendLog('SYSTEM', `[MIC] ${msg}`, 'error-log');
                };

                rec.onend = () => {
                    micActive = false;
                    btnMic.classList.remove('listening');
                    if (commandInput) {
                        commandInput.placeholder = 'Transmit instruction code to JARVIS...';
                    }
                    const sidebarVoiceStatus = document.getElementById('sidebar-voice-status');
                    if (sidebarVoiceStatus) {
                        sidebarVoiceStatus.innerText = 'ONLINE // READY';
                        sidebarVoiceStatus.style.color = 'var(--success-color)';
                    }

                    const commandToExecute = spokenFinalCommand || (commandInput ? commandInput.value.trim() : '');
                    spokenFinalCommand = '';
                    if (commandToExecute) {
                        sendCommand(commandToExecute);
                    }
                };

                return rec;
            };

            btnMic.addEventListener('click', async () => {
                if (micActive) {
                    if (recognition) {
                        recognition.stop();
                    }
                    return;
                }

                try {
                    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                        // Request audio stream permission gracefully
                        await navigator.mediaDevices.getUserMedia({ audio: true });
                    }
                    recognition = initRecognition();
                    recognition.start();
                } catch (err) {
                    console.error('Microphone error:', err);
                    appendLog('SYSTEM', 'Microphone access was blocked or unavailable. Please permit microphone access in your browser.', 'error-log');
                    micActive = false;
                    btnMic.classList.remove('listening');
                }
            });
        }
    }


    // Email Modal Controls
    const emailModal = document.getElementById('email-modal');
    const emailModalCloseX = document.getElementById('email-modal-close-x');
    const launchEmailBtn = document.getElementById('launch-email-btn');
    const emailToInput = document.getElementById('email-to-input');
    const emailRoleSelect = document.getElementById('email-role-select');
    const emailCustomRoleContainer = document.getElementById('email-custom-role-container');
    const emailCustomRoleInput = document.getElementById('email-custom-role-input');
    const emailFormatSelect = document.getElementById('email-format-select');
    const emailSenderName = document.getElementById('email-sender-name');
    const emailSenderDept = document.getElementById('email-sender-dept');
    const emailStartDate = document.getElementById('email-start-date');
    const emailEndDate = document.getElementById('email-end-date');
    const emailAboutInput = document.getElementById('email-about-input');
    const emailGenerateBtn = document.getElementById('email-generate-btn');
    
    const emailFormInputs = document.getElementById('email-form-inputs');
    const emailOutputGroup = document.getElementById('email-output-group');
    const emailSubjectOutput = document.getElementById('email-subject-output');
    const emailBodyOutput = document.getElementById('email-body-output');
    const emailCopyBtn = document.getElementById('email-copy-btn');
    const emailRegenerateBtn = document.getElementById('email-regenerate-btn');

    const btnEmailCard = document.getElementById('btn-email-assistant');
    if (btnEmailCard) {
        btnEmailCard.addEventListener('click', () => {
            if (launchEmailBtn) launchEmailBtn.click();
        });
    }

    if (launchEmailBtn) {
        launchEmailBtn.addEventListener('click', (e) => {
            if (e) e.stopPropagation();
            resetEmailForm();
            emailModal.classList.add('open');
            emailToInput.focus();
        });
    }

    const closeEmailModal = () => {
        emailModal.classList.remove('open');
    };

    if (emailModalCloseX) emailModalCloseX.addEventListener('click', closeEmailModal);
    emailModal.addEventListener('click', (e) => {
        if (e.target === emailModal) closeEmailModal();
    });

    if (emailRoleSelect) {
        emailRoleSelect.addEventListener('change', () => {
            if (emailRoleSelect.value === 'Custom') {
                emailCustomRoleContainer.style.display = 'block';
                emailCustomRoleInput.focus();
            } else {
                emailCustomRoleContainer.style.display = 'none';
            }
        });
    }

    if (emailStartDate && emailEndDate) {
        emailStartDate.addEventListener('change', () => {
            if (emailStartDate.value) {
                emailEndDate.min = emailStartDate.value;
                if (emailEndDate.value && emailEndDate.value < emailStartDate.value) {
                    emailEndDate.value = '';
                }
            } else {
                emailEndDate.removeAttribute('min');
            }
        });

        emailEndDate.addEventListener('change', () => {
            if (emailEndDate.value) {
                emailStartDate.max = emailEndDate.value;
                if (emailStartDate.value && emailStartDate.value > emailEndDate.value) {
                    emailStartDate.value = '';
                }
            } else {
                emailStartDate.removeAttribute('max');
            }
        });
    }

    if (emailGenerateBtn) {
        emailGenerateBtn.addEventListener('click', async () => {
            const toVal = emailToInput.value.trim();
            const aboutVal = emailAboutInput.value.trim();
            const roleVal = emailRoleSelect.value;
            const customRoleVal = emailCustomRoleInput.value.trim();
            const formatVal = emailFormatSelect ? emailFormatSelect.value : 'Formal';

            if (!toVal) {
                alert('Please enter recipient email.');
                return;
            }
            if (!aboutVal) {
                alert('Please describe what this email is about.');
                return;
            }
            if (roleVal === 'Custom' && !customRoleVal) {
                alert('Please specify the custom recipient role.');
                return;
            }

            emailGenerateBtn.disabled = true;
            emailGenerateBtn.innerText = 'GENERATING DRAFT...';

            try {
                const res = await fetch(`${apiBase}/api/generate_email`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        to: toVal,
                        role: roleVal,
                        custom_role: customRoleVal,
                        about: aboutVal,
                        sender_name: emailSenderName ? emailSenderName.value.trim() : '',
                        sender_dept: emailSenderDept ? emailSenderDept.value.trim() : '',
                        start_date: emailStartDate ? emailStartDate.value : '',
                        end_date: emailEndDate ? emailEndDate.value : '',
                        format: formatVal
                    })
                });
                const data = await res.json();
                if (data.success) {
                    emailSubjectOutput.value = data.subject;
                    emailBodyOutput.value = data.body;
                    
                    // In-place UI swap: Hide form inputs, show output pane
                    if (emailFormInputs) emailFormInputs.style.display = 'none';
                    if (emailOutputGroup) emailOutputGroup.style.display = 'flex';
                    
                    appendLog('JARVIS', `Email draft generated successfully in ${formatVal} format.`, 'assistant-log');
                } else {
                    alert(`Error: ${data.error}`);
                }
            } catch (err) {
                console.error(err);
                alert('Failed to connect to the email assistant.');
            } finally {
                emailGenerateBtn.disabled = false;
                emailGenerateBtn.innerText = 'GENERATE EMAIL DRAFT';
            }
        });
    }

    if (emailCopyBtn) {
        emailCopyBtn.addEventListener('click', () => {
            const subject = emailSubjectOutput.value.trim();
            const body = emailBodyOutput.value.trim();
            const emailText = `Subject: ${subject}\n\n${body}`;

            navigator.clipboard.writeText(emailText)
                .then(() => {
                    const originalText = emailCopyBtn.innerText;
                    emailCopyBtn.innerText = 'COPIED!';
                    emailCopyBtn.style.borderColor = 'var(--success-color)';
                    emailCopyBtn.style.color = 'var(--success-color)';
                    appendLog('SYSTEM', 'Email copied to clipboard.', 'system-log');
                    setTimeout(() => {
                        emailCopyBtn.innerText = originalText;
                        emailCopyBtn.style.borderColor = '';
                        emailCopyBtn.style.color = '';
                    }, 1500);
                })
                .catch(err => {
                    alert('Failed to copy email: ' + err);
                });
        });
    }

    if (emailRegenerateBtn) {
        emailRegenerateBtn.addEventListener('click', () => {
            // Swap back: show form inputs, hide output pane
            if (emailFormInputs) emailFormInputs.style.display = 'flex';
            if (emailOutputGroup) emailOutputGroup.style.display = 'none';
        });
    }

    function resetEmailForm() {
        emailToInput.value = '';
        emailRoleSelect.value = 'HOD';
        emailCustomRoleContainer.style.display = 'none';
        emailCustomRoleInput.value = '';
        if (emailFormatSelect) emailFormatSelect.value = 'Formal';
        
        // Sync custom UI dropdowns if they exist
        const wrapperRole = document.getElementById('wrapper-email-role-select');
        if (wrapperRole) {
            const roleSelectTrigger = wrapperRole.querySelector('.custom-select-trigger span');
            if (roleSelectTrigger) roleSelectTrigger.innerText = 'HOD';
            wrapperRole.querySelectorAll('.custom-option').forEach(opt => {
                if (opt.dataset.value === 'HOD') opt.classList.add('selected');
                else opt.classList.remove('selected');
            });
        }
        
        const wrapperFormat = document.getElementById('wrapper-email-format-select');
        if (wrapperFormat) {
            const formatSelectTrigger = wrapperFormat.querySelector('.custom-select-trigger span');
            if (formatSelectTrigger) formatSelectTrigger.innerText = 'Formal';
            wrapperFormat.querySelectorAll('.custom-option').forEach(opt => {
                if (opt.dataset.value === 'Formal') opt.classList.add('selected');
                else opt.classList.remove('selected');
            });
        }

        if (emailSenderName) emailSenderName.value = '';
        if (emailSenderDept) emailSenderDept.value = '';
        if (emailStartDate) {
            emailStartDate.value = '';
            emailStartDate.removeAttribute('min');
            emailStartDate.removeAttribute('max');
        }
        if (emailEndDate) {
            emailEndDate.value = '';
            emailEndDate.removeAttribute('min');
            emailEndDate.removeAttribute('max');
        }
        emailAboutInput.value = '';
        emailSubjectOutput.value = '';
        emailBodyOutput.value = '';
        
        // Restore initial form state
        if (emailFormInputs) emailFormInputs.style.display = 'flex';
        if (emailOutputGroup) emailOutputGroup.style.display = 'none';
    }

    // Sidebar Navigation View Switcher (Dashboard / Code Assistant / Idea Engine / Intelligence Hub)
    const btnDashboard = document.getElementById('btn-dashboard');
    const btnCodeAssistant = document.getElementById('btn-code-assistant');
    const btnIdeaEngine = document.getElementById('btn-idea-engine');
    const btnIntelligence = document.getElementById('btn-intelligence');
    const btnSecurity = document.getElementById('btn-security');
    const launchIdeaEngineBtn = document.getElementById('launch-idea-engine-btn');
    const viewDashboard = document.getElementById('view-dashboard');
    const viewCodeAssistant = document.getElementById('view-code-assistant');
    const viewIdeaEngine = document.getElementById('view-idea-engine');
    const viewIntelligence = document.getElementById('view-intelligence');
    const viewSecurity = document.getElementById('view-security');

    function deactivateAllNavs() {
        if (btnDashboard) btnDashboard.classList.remove('active');
        if (btnCodeAssistant) btnCodeAssistant.classList.remove('active');
        if (btnIdeaEngine) btnIdeaEngine.classList.remove('active');
        if (btnIntelligence) btnIntelligence.classList.remove('active');
        if (btnSecurity) btnSecurity.classList.remove('active');
        if (viewDashboard) viewDashboard.style.display = 'none';
        if (viewCodeAssistant) {
            viewCodeAssistant.style.display = 'none';
        }
        if (viewIdeaEngine) viewIdeaEngine.style.display = 'none';
        if (viewIntelligence) viewIntelligence.style.display = 'none';
        if (viewSecurity) viewSecurity.style.display = 'none';
    }

    if (btnDashboard) {
        btnDashboard.addEventListener('click', () => {
            deactivateAllNavs();
            btnDashboard.classList.add('active');
            viewDashboard.style.display = 'flex';
            
            // Restore right panel and console footer
            const rightPanel = document.querySelector('.right-panel');
            if (rightPanel) rightPanel.style.display = 'flex';
            const consoleFooter = document.querySelector('.console-footer');
            if (consoleFooter) consoleFooter.style.display = 'flex';
            const dashboardContainer = document.querySelector('.dashboard-container');
            if (dashboardContainer) {
                dashboardContainer.style.gridTemplateColumns = window.innerWidth <= 960 ? '1fr' : '280px 1fr 340px';
            }
        });
    }

    if (btnCodeAssistant) {
        btnCodeAssistant.addEventListener('click', () => {
            deactivateAllNavs();
            btnCodeAssistant.classList.add('active');
            const isMobile = window.innerWidth <= 960;
            viewCodeAssistant.style.display = isMobile ? 'flex' : 'grid';
            viewCodeAssistant.style.gridTemplateColumns = isMobile ? '' : '360px minmax(0, 1fr)';
            viewCodeAssistant.style.flexDirection = 'column';
            viewCodeAssistant.style.gap = isMobile ? '16px' : '20px';
            viewCodeAssistant.style.height = isMobile ? 'auto' : '100%';
            viewCodeAssistant.style.overflowY = isMobile ? 'auto' : 'hidden';
            viewCodeAssistant.style.minHeight = '0';
            viewCodeAssistant.style.width = '100%';
            
            // Hide right panel and console footer
            const rightPanel = document.querySelector('.right-panel');
            if (rightPanel) rightPanel.style.display = 'none';
            const consoleFooter = document.querySelector('.console-footer');
            if (consoleFooter) consoleFooter.style.display = 'none';
            const dashboardContainer = document.querySelector('.dashboard-container');
            if (dashboardContainer) {
                dashboardContainer.style.gridTemplateColumns = (window.innerWidth <= 960) ? '1fr' : '280px 1fr';
            }
        });
    }

    function openIdeaEngineView() {
        deactivateAllNavs();
        if (btnIdeaEngine) btnIdeaEngine.classList.add('active');
        if (viewIdeaEngine) viewIdeaEngine.style.display = 'grid';
        
        // Hide right panel and console footer to give Idea Engine full workspace height
        document.querySelector('.right-panel').style.display = 'none';
        document.querySelector('.console-footer').style.display = 'none';
        document.querySelector('.dashboard-container').style.gridTemplateColumns = '280px 1fr';
    }

    if (btnIdeaEngine) {
        btnIdeaEngine.addEventListener('click', openIdeaEngineView);
    }
    if (launchIdeaEngineBtn) {
        launchIdeaEngineBtn.addEventListener('click', openIdeaEngineView);
    }

    function openIntelligenceView() {
        deactivateAllNavs();
        if (btnIntelligence) btnIntelligence.classList.add('active');
        if (viewIntelligence) viewIntelligence.style.display = 'flex';
        
        // Hide right panel and console footer to give Intelligence Hub full workspace height
        document.querySelector('.right-panel').style.display = 'none';
        document.querySelector('.console-footer').style.display = 'none';
        document.querySelector('.dashboard-container').style.gridTemplateColumns = '280px 1fr';

        loadCurrentIntelTab();
    }

    if (btnIntelligence) {
        btnIntelligence.addEventListener('click', openIntelligenceView);
    }

    function openSecurityView() {
        deactivateAllNavs();
        if (btnSecurity) btnSecurity.classList.add('active');
        if (viewSecurity) viewSecurity.style.display = 'flex';
        
        const rightPanel = document.querySelector('.right-panel');
        if (rightPanel) rightPanel.style.display = 'none';
        const consoleFooter = document.querySelector('.console-footer');
        if (consoleFooter) consoleFooter.style.display = 'none';
        const dashboardContainer = document.querySelector('.dashboard-container');
        if (dashboardContainer) dashboardContainer.style.gridTemplateColumns = '280px 1fr';

        loadSecurityOverview();
    }

    if (btnSecurity) {
        btnSecurity.addEventListener('click', openSecurityView);
    }

    // Code Assistant Actions
    const codeChatMessages = document.getElementById('code-chat-messages');
    const codeChatInput = document.getElementById('code-chat-input');
    const codeChatSendBtn = document.getElementById('code-chat-send-btn');
    const codeDisplay = document.getElementById('code-display');
    const codeCopyBtn = document.getElementById('code-copy-btn');
    const codeDownloadBtn = document.getElementById('code-download-btn');
    const codeLangSelect = document.getElementById('code-lang-select');
    const codeRunBtn = document.getElementById('code-run-btn');
    const codeClearConsoleBtn = document.getElementById('code-clear-console-btn');
    const codeConsoleOutput = document.getElementById('code-console-output');
    const codeDebugAiBtn = document.getElementById('code-debug-ai-btn');
    const codeConsoleAiInput = document.getElementById('code-console-ai-input');
    const codeConsoleAiSendBtn = document.getElementById('code-console-ai-send-btn');
    const codeConsoleAiPrefix = document.getElementById('code-console-ai-prefix');

    
    let currentInputMode = 'ai';

    function appendCodeLog(sender, text, type) {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        const timestamp = new Date().toLocaleTimeString();
        line.innerText = `[${timestamp}] [${sender}] ${text}`;
        codeChatMessages.appendChild(line);
        codeChatMessages.scrollTop = codeChatMessages.scrollHeight;
    }

    async function sendCodePrompt() {
        const prompt = codeChatInput.value.trim();
        if (!prompt) return;
        
        appendCodeLog('USER', prompt, 'user-log');
        codeChatInput.value = '';
        
        const loader = document.createElement('div');
        loader.className = 'log-line system-log';
        loader.innerText = '[J.A.R.V.I.S] Compiling algorithm details... Please wait.';
        codeChatMessages.appendChild(loader);
        codeChatMessages.scrollTop = codeChatMessages.scrollHeight;
        
        const selectedLang = codeLangSelect ? codeLangSelect.value : 'python';
        const langName = codeLangSelect ? codeLangSelect.options[codeLangSelect.selectedIndex].text.split(' ')[0] : 'Code';

        try {
            const res = await fetch(`${apiBase}/api/code_assistant`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: prompt,
                    language: selectedLang
                })
            });
            const data = await res.json();
            
            codeChatMessages.removeChild(loader);
            
            if (data.success) {
                appendCodeLog('JARVIS', `${langName} code generated successfully.`, 'assistant-log');
                let codeStr = data.code || '';
                if (codeStr.includes('\\n') && !codeStr.includes('\n')) {
                    codeStr = codeStr.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '    ');
                }
                codeDisplay.innerText = codeStr.trim();
                updateLineNumbers();
            } else {
                appendCodeLog('SYSTEM ERROR', data.error || 'Failed to compile script', 'error-log');
            }
        } catch (err) {
            if (loader.parentNode) codeChatMessages.removeChild(loader);
            appendCodeLog('SYSTEM', 'Network connection to compiler lost.', 'error-log');
            console.error(err);
        }
    }

    codeChatSendBtn.addEventListener('click', sendCodePrompt);
    codeChatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendCodePrompt();
    });

    codeCopyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(codeDisplay.innerText)
            .then(() => {
                const originalText = codeCopyBtn.innerText;
                codeCopyBtn.innerText = 'COPIED!';
                codeCopyBtn.style.borderColor = 'var(--success-color)';
                codeCopyBtn.style.color = 'var(--success-color)';
                setTimeout(() => {
                    codeCopyBtn.innerText = originalText;
                    codeCopyBtn.style.borderColor = '';
                    codeCopyBtn.style.color = '';
                }, 1500);
            })
            .catch(err => alert('Failed to copy code: ' + err));
    });

    codeDownloadBtn.addEventListener('click', () => {
        const code = codeDisplay.innerText;
        const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
        const link = document.createElement('a');
        
        const langExts = {
            python: 'py',
            javascript: 'js',
            html: 'html',
            css: 'css',
            cpp: 'cpp',
            java: 'java',
            csharp: 'cs',
            go: 'go',
            typescript: 'ts',
            sql: 'sql',
            rust: 'rs'
        };
        const selectedLang = codeLangSelect ? codeLangSelect.value : 'python';
        const ext = langExts[selectedLang] || 'txt';
        
        link.href = URL.createObjectURL(blob);
        link.download = `jarvis_generated_code.${ext}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    if (codeRunBtn) {
        codeRunBtn.addEventListener('click', async () => {
            const code = codeDisplay.innerText;
            const selectedLang = codeLangSelect ? codeLangSelect.value : 'python';
            
            codeConsoleOutput.innerText = "Running code... Please wait.\n";
            codeConsoleOutput.style.color = 'var(--accent-color)';
            if (codeDebugAiBtn) codeDebugAiBtn.style.display = 'none';
            
            const originalText = codeRunBtn.innerText;
            codeRunBtn.innerText = 'RUNNING...';
            codeRunBtn.style.borderColor = 'var(--accent-color)';
            codeRunBtn.style.color = 'var(--accent-color)';
            codeRunBtn.disabled = true;

            let eventSource = null;

            try {
                const res = await fetch(`${apiBase}/api/run_code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        code: code,
                        language: selectedLang
                    })
                });
                const data = await res.json();
                
                if (data.success) {
                    if (data.started) {
                        // Clear wait message and open event stream
                        codeConsoleOutput.innerText = "";
                        setConsoleInputMode('input');
                        
                        eventSource = new EventSource(`${apiBase}/api/console_stream`);
                        
                        eventSource.onmessage = (event) => {
                            const payload = JSON.parse(event.data);
                            if (payload.type === 'stdout') {
                                codeConsoleOutput.innerText += payload.text;
                                codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
                            } else if (payload.type === 'stderr') {
                                codeConsoleOutput.innerText += payload.text;
                                codeConsoleOutput.style.color = '#ff0055';
                                codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
                            } else if (payload.type === 'exit') {
                                eventSource.close();
                                
                                // Reset button
                                codeRunBtn.innerText = originalText;
                                codeRunBtn.style.borderColor = '';
                                codeRunBtn.style.color = '';
                                codeRunBtn.disabled = false;
                                
                                setConsoleInputMode('ai');
                                
                                codeConsoleOutput.innerText += `\n\n[Process finished with exit code ${payload.exit_code}]`;
                                codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
                                
                                if (payload.exit_code !== 0) {
                                    if (codeDebugAiBtn) codeDebugAiBtn.style.display = 'inline-block';
                                }
                            }
                        };
                        
                        eventSource.onerror = (err) => {
                            console.error("EventSource error:", err);
                            eventSource.close();
                            
                            codeRunBtn.innerText = originalText;
                            codeRunBtn.style.borderColor = '';
                            codeRunBtn.style.color = '';
                            codeRunBtn.disabled = false;
                            
                            setConsoleInputMode('ai');
                        };
                        
                        // Early return to prevent button reset below
                        return;
                    } else {
                        // Started is false, meaning compilation failed immediately
                        let outputStr = "";
                        if (data.stdout) outputStr += data.stdout;
                        if (data.stderr) outputStr += (outputStr ? "\n" : "") + data.stderr;
                        codeConsoleOutput.innerText = outputStr || "Compilation failed.";
                        codeConsoleOutput.style.color = '#ff0055';
                        if (codeDebugAiBtn) codeDebugAiBtn.style.display = 'inline-block';
                    }
                } else {
                    codeConsoleOutput.innerText = `Error: ${data.error || 'Failed to start code execution'}`;
                    codeConsoleOutput.style.color = '#ff0055';
                    if (codeDebugAiBtn) codeDebugAiBtn.style.display = 'inline-block';
                }
            } catch (err) {
                codeConsoleOutput.innerText = `Network Error: Could not connect to runner service.`;
                codeConsoleOutput.style.color = '#ff0055';
                console.error(err);
            }
            
            // Re-enable button ONLY if process did not start
            codeRunBtn.innerText = originalText;
            codeRunBtn.style.borderColor = '';
            codeRunBtn.style.color = '';
            codeRunBtn.disabled = false;
        });
    }

    if (codeClearConsoleBtn) {
        codeClearConsoleBtn.addEventListener('click', () => {
            codeConsoleOutput.innerText = "Console idle. Click Run Code to execute.";
            codeConsoleOutput.style.color = '#e0e0e0';
            if (codeDebugAiBtn) codeDebugAiBtn.style.display = 'none';
        });
    }



    function parseConsoleMarkdown(text) {
        if (!text) return "";
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/`(.*?)`/g, '<code style="background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.25); padding: 1px 4px; border-radius: 4px; font-family: var(--font-mono); color: var(--accent-color); font-size: 0.7rem;">$1</code>');
        html = html.replace(/^###\s+(.*?)$/gm, '<h4 style="color: var(--accent-color); margin: 10px 0 6px 0; font-size: 0.8rem; letter-spacing: 0.5px;">$1</h4>');
        html = html.replace(/^##\s+(.*?)$/gm, '<h3 style="color: var(--accent-color); margin: 12px 0 8px 0; font-size: 0.85rem; letter-spacing: 0.5px;">$1</h3>');
        html = html.replace(/^#\s+(.*?)$/gm, '<h2 style="color: var(--accent-color); margin: 14px 0 10px 0; font-size: 0.9rem; letter-spacing: 0.5px;">$1</h2>');
        html = html.replace(/^-\s+(.*?)$/gm, '<div style="padding-left: 10px; position: relative; margin-bottom: 4px;"><span style="color: var(--accent-color); position: absolute; left: 0;">•</span>$1</div>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function renderConsoleAIResponse(responseText) {
        const codeBlockRegex = /```(?:[a-zA-Z0-9+#-]+)?\n([\s\S]*?)\n```/g;
        
        const container = document.createElement('div');
        container.className = 'ai-response-container';
        container.style.borderTop = '1px dashed rgba(0, 210, 255, 0.3)';
        container.style.paddingTop = '12px';
        container.style.marginTop = '12px';
        container.style.color = '#ffffff';
        container.style.fontFamily = 'var(--font-sans)';
        
        const title = document.createElement('div');
        title.style.color = 'var(--accent-color)';
        title.style.fontSize = '0.7rem';
        title.style.fontWeight = 'bold';
        title.style.letterSpacing = '1px';
        title.style.marginBottom = '6px';
        title.innerText = 'J.A.R.V.I.S. ANALYSIS:';
        container.appendChild(title);

        let lastIndex = 0;
        let match;
        
        while ((match = codeBlockRegex.exec(responseText)) !== null) {
            const textBefore = responseText.substring(lastIndex, match.index);
            if (textBefore.trim()) {
                const p = document.createElement('p');
                p.style.fontSize = '0.75rem';
                p.style.lineHeight = '1.45';
                p.style.margin = '0 0 8px 0';
                p.style.color = '#e0e0e0';
                p.innerHTML = parseConsoleMarkdown(textBefore);
                container.appendChild(p);
            }
            
            const suggestedCode = match[1];
            
            const codeBlockWrapper = document.createElement('div');
            codeBlockWrapper.style.background = 'rgba(4, 6, 8, 0.95)';
            codeBlockWrapper.style.border = '1px solid rgba(0, 210, 255, 0.25)';
            codeBlockWrapper.style.borderRadius = '6px';
            codeBlockWrapper.style.margin = '8px 0';
            codeBlockWrapper.style.position = 'relative';
            
            const pre = document.createElement('pre');
            pre.style.margin = '0';
            pre.style.padding = '12px';
            pre.style.overflowX = 'auto';
            pre.style.fontFamily = 'var(--font-mono)';
            pre.style.fontSize = '0.75rem';
            pre.style.color = '#bde0fe';
            pre.innerText = suggestedCode;
            codeBlockWrapper.appendChild(pre);
            
            const applyBtn = document.createElement('button');
            applyBtn.innerText = 'APPLY CODE FIX';
            applyBtn.style.position = 'absolute';
            applyBtn.style.top = '6px';
            applyBtn.style.right = '6px';
            applyBtn.style.background = 'rgba(0, 210, 255, 0.2)';
            applyBtn.style.border = '1px solid var(--accent-color)';
            applyBtn.style.color = 'var(--accent-color)';
            applyBtn.style.padding = '4px 8px';
            applyBtn.style.fontSize = '0.6rem';
            applyBtn.style.fontWeight = 'bold';
            applyBtn.style.borderRadius = '4px';
            applyBtn.style.cursor = 'pointer';
            applyBtn.style.outline = 'none';
            applyBtn.style.transition = 'all 0.2s';
            
            applyBtn.addEventListener('mouseenter', () => {
                applyBtn.style.background = 'var(--accent-color)';
                applyBtn.style.color = '#000';
            });
            applyBtn.addEventListener('mouseleave', () => {
                applyBtn.style.background = 'rgba(0, 210, 255, 0.2)';
                applyBtn.style.color = 'var(--accent-color)';
            });
            
            applyBtn.addEventListener('click', () => {
                codeDisplay.innerText = suggestedCode.trim();
                updateLineNumbers();
                
                applyBtn.innerText = 'APPLIED!';
                applyBtn.style.borderColor = 'var(--success-color)';
                applyBtn.style.color = 'var(--success-color)';
                applyBtn.style.background = 'rgba(0, 255, 204, 0.1)';
                
                const logLine = document.createElement('div');
                logLine.style.color = 'var(--success-color)';
                logLine.style.fontSize = '0.7rem';
                logLine.style.marginTop = '4px';
                logLine.innerText = '[System: Applied AI suggested code correction to editor]';
                container.appendChild(logLine);
                
                setTimeout(() => {
                    applyBtn.innerText = 'APPLY CODE FIX';
                    applyBtn.style.borderColor = 'var(--accent-color)';
                    applyBtn.style.color = 'var(--accent-color)';
                    applyBtn.style.background = 'rgba(0, 210, 255, 0.2)';
                }, 2000);
            });
            
            codeBlockWrapper.appendChild(applyBtn);
            container.appendChild(codeBlockWrapper);
            
            lastIndex = codeBlockRegex.lastIndex;
        }
        
        const textAfter = responseText.substring(lastIndex);
        if (textAfter.trim()) {
            const p = document.createElement('p');
            p.style.fontSize = '0.75rem';
            p.style.lineHeight = '1.45';
            p.style.margin = '0';
            p.style.color = '#e0e0e0';
            p.innerHTML = parseConsoleMarkdown(textAfter);
            container.appendChild(p);
        }
        
        if (codeConsoleOutput.children.length === 0) {
            const currentText = codeConsoleOutput.innerText;
            codeConsoleOutput.innerHTML = '';
            const textNode = document.createElement('div');
            textNode.style.fontFamily = 'var(--font-mono)';
            textNode.style.whiteSpace = 'pre-wrap';
            textNode.innerText = currentText;
            codeConsoleOutput.appendChild(textNode);
        }
        
        codeConsoleOutput.appendChild(container);
        codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
    }

    async function sendConsoleAiQuery(customPrompt) {
        const query = customPrompt || (codeConsoleAiInput ? codeConsoleAiInput.value.trim() : '');
        if (!query) return;
        
        if (!customPrompt && codeConsoleAiInput) {
            codeConsoleAiInput.value = '';
        }
        
        const loader = document.createElement('div');
        loader.className = 'ai-loader';
        loader.style.color = 'var(--accent-color)';
        loader.style.fontSize = '0.75rem';
        loader.style.marginTop = '10px';
        loader.style.fontStyle = 'italic';
        loader.innerText = ' [J.A.R.V.I.S. is analyzing the code and terminal output...]';
        
        if (codeConsoleOutput.children.length === 0) {
            const currentText = codeConsoleOutput.innerText;
            codeConsoleOutput.innerHTML = '';
            const textNode = document.createElement('div');
            textNode.style.fontFamily = 'var(--font-mono)';
            textNode.style.whiteSpace = 'pre-wrap';
            textNode.innerText = currentText;
            codeConsoleOutput.appendChild(textNode);
        }
        codeConsoleOutput.appendChild(loader);
        codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
        
        const code = codeDisplay.innerText;
        const rawOutput = codeConsoleOutput.innerText.split('J.A.R.V.I.S. ANALYSIS:')[0].trim();
        const selectedLang = codeLangSelect ? codeLangSelect.value : 'python';
        
        try {
            const res = await fetch(`${apiBase}/api/debug_code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    output: rawOutput,
                    language: selectedLang,
                    prompt: query
                })
            });
            const data = await res.json();
            
            if (loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
            
            if (data.success) {
                renderConsoleAIResponse(data.response);
            } else {
                const errDiv = document.createElement('div');
                errDiv.style.color = '#ff0055';
                errDiv.style.fontSize = '0.75rem';
                errDiv.style.marginTop = '10px';
                errDiv.innerText = 'AI Debugger Error: ' + (data.error || 'Unknown error');
                codeConsoleOutput.appendChild(errDiv);
                codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
            }
        } catch (err) {
            if (loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
            const errDiv = document.createElement('div');
            errDiv.style.color = '#ff0055';
            errDiv.style.fontSize = '0.75rem';
            errDiv.style.marginTop = '10px';
            errDiv.innerText = 'Network error contacting AI debugger: ' + err.message;
            codeConsoleOutput.appendChild(errDiv);
            codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
        }
    }

    function setConsoleInputMode(mode) {
        currentInputMode = mode;
        if (mode === 'input') {
            if (codeConsoleAiPrefix) {
                codeConsoleAiPrefix.innerText = 'INPUT >';
                codeConsoleAiPrefix.style.color = 'var(--accent-color)';
            }
            if (codeConsoleAiInput) {
                codeConsoleAiInput.placeholder = 'Type input value and press Enter...';
                codeConsoleAiInput.value = '';
                codeConsoleAiInput.focus();
            }
        } else {
            if (codeConsoleAiPrefix) {
                codeConsoleAiPrefix.innerText = 'AI >';
                codeConsoleAiPrefix.style.color = 'var(--accent-color)';
            }
            if (codeConsoleAiInput) {
                codeConsoleAiInput.placeholder = 'Ask J.A.R.V.I.S. to explain, fix, or optimize...';
                codeConsoleAiInput.value = '';
            }
        }
    }

    async function sendConsoleInput() {
        if (!codeConsoleAiInput) return;
        const val = codeConsoleAiInput.value;
        codeConsoleAiInput.value = '';
        
        // Append input value locally
        codeConsoleOutput.innerText += val + '\n';
        codeConsoleOutput.scrollTop = codeConsoleOutput.scrollHeight;
        
        try {
            await fetch(`${apiBase}/api/console_input`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: val })
            });
        } catch (e) {
            console.error("Failed to send console input:", e);
        }
    }

    if (codeConsoleAiSendBtn) {
        codeConsoleAiSendBtn.addEventListener('click', () => {
            if (currentInputMode === 'input') {
                sendConsoleInput();
            } else {
                sendConsoleAiQuery();
            }
        });
    }
    if (codeConsoleAiInput) {
        codeConsoleAiInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (currentInputMode === 'input') {
                    sendConsoleInput();
                } else {
                    sendConsoleAiQuery();
                }
            }
        });
    }
    if (codeDebugAiBtn) {
        codeDebugAiBtn.addEventListener('click', () => {
            sendConsoleAiQuery("Explain and fix the error in the current code.");
        });
    }

    function updateLineNumbers() {
        const container = document.querySelector('.code-editor-container');
        let lineNumContainer = container.querySelector('.line-numbers');
        if (!lineNumContainer) {
            lineNumContainer = document.createElement('div');
            lineNumContainer.className = 'line-numbers';
            lineNumContainer.style.color = 'var(--text-muted)';
            lineNumContainer.style.textAlign = 'right';
            lineNumContainer.style.paddingLeft = '16px';
            lineNumContainer.style.paddingRight = '12px';
            lineNumContainer.style.marginRight = '12px';
            lineNumContainer.style.borderRight = '1px solid rgba(255,255,255,0.05)';
            lineNumContainer.style.userSelect = 'none';
            lineNumContainer.style.position = 'sticky';
            lineNumContainer.style.left = '0';
            lineNumContainer.style.background = '#040608';
            lineNumContainer.style.zIndex = '2';
            container.insertBefore(lineNumContainer, codeDisplay);
        }
        
        let lines = codeDisplay.innerText.split('\n');
        if (lines.length > 1 && lines[lines.length - 1] === '') {
            lines.pop();
        }
        let numbersHtml = '';
        for (let i = 1; i <= Math.max(1, lines.length); i++) {
            numbersHtml += `${i}<br>`;
        }
        lineNumContainer.innerHTML = numbersHtml;
    }

    codeDisplay.addEventListener('input', () => {
        updateLineNumbers();
    });
    codeDisplay.addEventListener('paste', (e) => {
        e.preventDefault();
        const text = (e.originalEvent || e).clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
        updateLineNumbers();
    });
    updateLineNumbers();

    // Helper to build futuristic custom dropdown selects
    function setupCustomSelect(selectId) {
        const originalSelect = document.getElementById(selectId);
        if (!originalSelect) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';
        wrapper.id = 'wrapper-' + selectId;
        
        // If original select has style width 100% or is inline block, carry it over
        if (originalSelect.style.width === '100%' || (originalSelect.getAttribute('style') && originalSelect.getAttribute('style').includes('width: 100%'))) {
            wrapper.classList.add('full-width');
        }
        
        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        
        const triggerText = document.createElement('span');
        triggerText.innerText = originalSelect.options[originalSelect.selectedIndex] ? originalSelect.options[originalSelect.selectedIndex].text : '';
        trigger.appendChild(triggerText);
        
        const arrow = document.createElement('div');
        arrow.className = 'arrow';
        trigger.appendChild(arrow);
        
        wrapper.appendChild(trigger);
        
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-select-options';
        
        Array.from(originalSelect.options).forEach((opt, idx) => {
            const customOpt = document.createElement('div');
            customOpt.className = 'custom-option';
            if (idx === originalSelect.selectedIndex) customOpt.classList.add('selected');
            customOpt.innerText = opt.text;
            customOpt.dataset.value = opt.value;
            
            customOpt.addEventListener('click', (e) => {
                e.stopPropagation();
                optionsContainer.querySelectorAll('.custom-option').forEach(el => el.classList.remove('selected'));
                customOpt.classList.add('selected');
                
                originalSelect.value = opt.value;
                triggerText.innerText = opt.text;
                wrapper.classList.remove('open');
                
                originalSelect.dispatchEvent(new Event('change'));
            });
            optionsContainer.appendChild(customOpt);
        });
        
        wrapper.appendChild(optionsContainer);
        
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.custom-select-wrapper').forEach(w => {
                if (w !== wrapper) w.classList.remove('open');
            });
            wrapper.classList.toggle('open');
        });
        
        // Sync custom UI with select state
        function syncUI() {
            const selectedOpt = originalSelect.options[originalSelect.selectedIndex];
            triggerText.innerText = selectedOpt ? selectedOpt.text : '';
            optionsContainer.querySelectorAll('.custom-option').forEach((el) => {
                if (el.dataset.value === originalSelect.value) {
                    el.classList.add('selected');
                } else {
                    el.classList.remove('selected');
                }
            });
        }
        
        // Listen to change events
        originalSelect.addEventListener('change', syncUI);
        
        // Override value property setter to update the custom UI programmatically (e.g. form resets)
        try {
            const descriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
            Object.defineProperty(originalSelect, 'value', {
                get: function() {
                    return descriptor.get.call(this);
                },
                set: function(val) {
                    descriptor.set.call(this, val);
                    syncUI();
                },
                configurable: true
            });
        } catch (e) {
            console.warn('Could not override value property of select', selectId, e);
        }
        
        originalSelect.style.display = 'none';
        originalSelect.parentNode.insertBefore(wrapper, originalSelect);
    }

    // Close custom dropdowns on outside click
    document.addEventListener('click', () => {
        document.querySelectorAll('.custom-select-wrapper').forEach(w => w.classList.remove('open'));
    });

    // Custom select initialization
    setupCustomSelect('news-category-select');
    setupCustomSelect('code-lang-select');
    setupCustomSelect('ppt-theme-select');
    setupCustomSelect('email-role-select');
    setupCustomSelect('email-format-select');
    setupCustomSelect('idea-mode-select');
    setupCustomSelect('idea-exp-select');
    setupCustomSelect('idea-type-select');
    setupCustomSelect('idea-domain-select');
    setupCustomSelect('idea-time-select');
    setupCustomSelect('prompt-visual-select');
    setupCustomSelect('prompt-motion-select');
    setupCustomSelect('prompt-3d-select');
    setupCustomSelect('prompt-platform-select');


    // Terminal Command Inputs Listeners
    if (btnSend) {
        btnSend.addEventListener('click', () => {
            const commandText = commandInput.value.trim();
            if (commandText) {
                sendCommand(commandText);
            }
        });
    }

    if (commandInput) {
        commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const commandText = commandInput.value.trim();
                if (commandText) {
                    sendCommand(commandText);
                }
            }
        });
    }

    // Diagnostics Button Listener
    const btnDiagnostics = document.getElementById('btn-diagnostics');
    if (btnDiagnostics) {
        btnDiagnostics.addEventListener('click', async () => {
            playTransmissionSweep();
            appendLog('SYSTEM', 'Initiating full system diagnostic sweep, Sir...', 'system-log');
            
            // Set visual state
            if (arcReactorContainer) {
                arcReactorContainer.classList.remove('listening');
                arcReactorContainer.classList.add('speaking');
            }
            if (statusMode) {
                statusMode.innerText = 'DIAGNOSING...';
                statusMode.className = 'status-indicator active';
            }
            
            try {
                const res = await fetch(`${apiBase}/api/diagnostics`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    playCompletionChirp();
                    appendLog('JARVIS', data.report, 'assistant-log');
                } else {
                    playErrorBeep();
                    appendLog('SYSTEM ERROR', data.error || 'Diagnostics failed', 'error-log');
                }
            } catch (err) {
                playErrorBeep();
                appendLog('SYSTEM ERROR', 'Mainframe diagnostic channel offline.', 'error-log');
            } finally {
                setTimeout(() => {
                    if (arcReactorContainer) arcReactorContainer.classList.remove('speaking');
                    if (statusMode) {
                        statusMode.innerText = 'SECURE MODE';
                        statusMode.className = 'status-indicator online';
                    }
                }, 1000);
            }
        });
    }

    // ==========================================
    // J.A.R.V.I.S. IDEA ENGINE CONTROLLER
    // ==========================================
    const ideaModeSelect = document.getElementById('idea-mode-select');
    const ideaTechTags = document.getElementById('idea-tech-tags');
    const ideaTechInput = document.getElementById('idea-tech-input');
    const ideaAddTechBtn = document.getElementById('idea-add-tech-btn');
    const ideaProblemGroup = document.getElementById('idea-problem-group');
    const ideaProblemInput = document.getElementById('idea-problem-input');
    const ideaExpSelect = document.getElementById('idea-exp-select');
    const ideaTypeSelect = document.getElementById('idea-type-select');
    const ideaDomainSelect = document.getElementById('idea-domain-select');
    const ideaTimeSelect = document.getElementById('idea-time-select');
    const ideaGenerateBtn = document.getElementById('idea-generate-btn');
    const ideaAnalysisBanner = document.getElementById('idea-analysis-banner');
    const ideaSynergiesCount = document.getElementById('idea-synergies-count');
    const ideaSynergiesList = document.getElementById('idea-synergies-list');
    const ideaEmptyState = document.getElementById('idea-empty-state');
    const ideaLoadingState = document.getElementById('idea-loading-state');
    const ideaCardsGrid = document.getElementById('idea-cards-grid');

    // Idea Details Modal Elements
    const ideaDetailsModal = document.getElementById('idea-details-modal');
    const ideaModalCloseX = document.getElementById('idea-modal-close-x');
    const ideaModalCloseBtn = document.getElementById('idea-modal-close-btn');
    const ideaModalCopyBtn = document.getElementById('idea-modal-copy-btn');
    const ideaModalTitle = document.getElementById('idea-modal-title');
    const ideaModalTierBadge = document.getElementById('idea-modal-tier-badge');
    const ideaModalPitch = document.getElementById('idea-modal-pitch');
    const ideaModalSolution = document.getElementById('idea-modal-solution');
    const ideaModalScoresGrid = document.getElementById('idea-modal-scores-grid');
    const ideaModalProblem = document.getElementById('idea-modal-problem');
    const ideaModalUsers = document.getElementById('idea-modal-users');
    const ideaModalTechTbody = document.getElementById('idea-modal-tech-tbody');
    const ideaModalFeatures = document.getElementById('idea-modal-features');
    const ideaModalArch = document.getElementById('idea-modal-arch');
    const ideaModalDataflow = document.getElementById('idea-modal-dataflow');
    const ideaModalRoadmap = document.getElementById('idea-modal-roadmap');
    const ideaModalRisks = document.getElementById('idea-modal-risks');
    const ideaModalFuture = document.getElementById('idea-modal-future');

    let currentTechStack = ['Python', 'FastAPI', 'Supabase', 'Gemini API', 'Docker'];
    let lastGeneratedResult = null;
    let selectedIdeaForModal = null;

    function renderTechTags() {
        if (!ideaTechTags) return;
        ideaTechTags.innerHTML = '';
        currentTechStack.forEach((tech, idx) => {
            const pill = document.createElement('span');
            pill.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; background: rgba(0, 210, 255, 0.12); border: 1px solid rgba(0, 210, 255, 0.3); color: var(--accent-color); font-size: 0.75rem; padding: 3px 8px; border-radius: 4px; font-family: var(--font-mono);';
            pill.innerHTML = `<span>${tech}</span><span style="cursor: pointer; opacity: 0.7; font-weight: bold;" data-idx="${idx}">&times;</span>`;
            pill.querySelector('span:last-child').addEventListener('click', (e) => {
                const targetIdx = parseInt(e.target.dataset.idx, 10);
                currentTechStack.splice(targetIdx, 1);
                renderTechTags();
            });
            ideaTechTags.appendChild(pill);
        });
    }

    function addTechTag(techName) {
        const clean = techName.trim();
        if (clean && !currentTechStack.map(t => t.toLowerCase()).includes(clean.toLowerCase())) {
            currentTechStack.push(clean);
            renderTechTags();
        }
    }

    if (ideaAddTechBtn && ideaTechInput) {
        ideaAddTechBtn.addEventListener('click', () => {
            addTechTag(ideaTechInput.value);
            ideaTechInput.value = '';
            ideaTechInput.focus();
        });
        ideaTechInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addTechTag(ideaTechInput.value);
                ideaTechInput.value = '';
            }
        });
    }

    document.querySelectorAll('.tech-chip-quick').forEach(chip => {
        chip.style.cssText = 'cursor: pointer; font-size: 0.65rem; font-family: var(--font-mono); color: var(--text-secondary); background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); padding: 2px 6px; border-radius: 4px; transition: all 0.2s;';
        chip.addEventListener('click', () => {
            addTechTag(chip.dataset.tech);
        });
    });

    const STACK_PRESETS = {
        'ai-fullstack': ['Python', 'FastAPI', 'Supabase', 'Gemini API', 'Docker'],
        'vision-ai': ['Python', 'OpenCV', 'PyTorch', 'FastAPI', 'Docker'],
        'cloud-devops': ['Go', 'Docker', 'Kubernetes', 'Terraform', 'PostgreSQL'],
        'modern-web': ['React', 'TypeScript', 'Tailwind', 'Next.js', 'Supabase']
    };

    document.querySelectorAll('.tech-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presetKey = btn.getAttribute('data-preset');
            const presetStack = STACK_PRESETS[presetKey];
            if (presetStack) {
                currentTechStack = [...presetStack];
                renderTechTags();
                playButtonBeep();
            }
        });
    });

    if (ideaModeSelect && ideaProblemGroup) {
        ideaModeSelect.addEventListener('change', () => {
            const mode = ideaModeSelect.value;
            if (mode === 'stack_to_ideas') {
                ideaProblemGroup.style.display = 'none';
            } else {
                ideaProblemGroup.style.display = 'block';
                if (mode === 'problem_to_stack') {
                    ideaProblemGroup.querySelector('label').innerText = 'PROBLEM STATEMENT TO SOLVE';
                } else if (mode === 'stack_and_problem') {
                    ideaProblemGroup.querySelector('label').innerText = 'TARGET PROBLEM STATEMENT';
                } else if (mode === 'project_improvements') {
                    ideaProblemGroup.querySelector('label').innerText = 'PROJECT FEATURES & ARCHITECTURE TO IMPROVE';
                }
            }
        });
    }

    renderTechTags();

    if (ideaGenerateBtn) {
        ideaGenerateBtn.addEventListener('click', async () => {
            const mode = ideaModeSelect ? ideaModeSelect.value : 'stack_to_ideas';
            if (mode === 'stack_to_ideas' && currentTechStack.length === 0) {
                alert('Please add at least one technology to your stack.');
                return;
            }

            playTransmissionSweep();
            appendLog('IDEA ENGINE', `Initiating project blueprint analysis for mode: ${mode}...`, 'system-log');

            // UI State updates
            if (ideaEmptyState) ideaEmptyState.style.display = 'none';
            if (ideaCardsGrid) ideaCardsGrid.style.display = 'none';
            if (ideaLoadingState) ideaLoadingState.style.display = 'flex';
            if (ideaAnalysisBanner) ideaAnalysisBanner.style.display = 'none';
            ideaGenerateBtn.disabled = true;
            ideaGenerateBtn.innerText = 'ANALYZING STACK & REASONING...';

            try {
                const payload = {
                    technologies: currentTechStack,
                    mode: mode,
                    problem_statement: ideaProblemInput ? ideaProblemInput.value.trim() : null,
                    experience_level: ideaExpSelect ? ideaExpSelect.value : 'Intermediate',
                    project_type: ideaTypeSelect ? ideaTypeSelect.value : 'Portfolio Project',
                    domain: ideaDomainSelect ? ideaDomainSelect.value : 'Open-ended',
                    time_available: ideaTimeSelect ? ideaTimeSelect.value : '2 weeks',
                    number_of_ideas: 6
                };

                const res = await fetch(`${apiBase}/api/idea_engine/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const errorText = await res.text();
                    let errMsg = `Server returned HTTP ${res.status}`;
                    try {
                        const parsedErr = JSON.parse(errorText);
                        if (parsedErr.error) errMsg = parsedErr.error;
                    } catch (e) {
                        if (res.status === 404) {
                            errMsg = "Backend routes not found (HTTP 404). Please restart buddy.py to load the new Idea Engine endpoints.";
                        }
                    }
                    throw new Error(errMsg);
                }

                const data = await res.json();
                if (data.success && data.ideas && data.ideas.length > 0) {
                    playCompletionChirp();
                    lastGeneratedResult = data;
                    renderStackAnalysis(data.stack_analysis);
                    renderRankedIdeaCards(data.ideas);
                    appendLog('IDEA ENGINE', `Synthesized ${data.ideas.length} ranked project blueprints. Top rank: ${data.top_recommendation ? data.top_recommendation.title : 'Ready'}`, 'assistant-log');
                } else {
                    playErrorBeep();
                    appendLog('IDEA ENGINE', `Idea generation failed: ${data.error || 'No valid ideas produced.'}`, 'error-log');
                    if (ideaEmptyState) ideaEmptyState.style.display = 'flex';
                }
            } catch (err) {
                playErrorBeep();
                console.error(err);
                appendLog('IDEA ENGINE', `Communication error: ${err.message}`, 'error-log');
                if (ideaEmptyState) ideaEmptyState.style.display = 'flex';
            } finally {
                if (ideaLoadingState) ideaLoadingState.style.display = 'none';
                ideaGenerateBtn.disabled = false;
                ideaGenerateBtn.innerText = 'ANALYZE STACK & GENERATE';
            }
        });
    }

    function renderStackAnalysis(analysis) {
        if (!analysis || !ideaAnalysisBanner) return;
        ideaAnalysisBanner.style.display = 'block';
        if (ideaSynergiesCount) {
            ideaSynergiesCount.innerText = `${analysis.synergies.length} Technical Synergies Found`;
        }
        if (ideaSynergiesList) {
            ideaSynergiesList.innerHTML = '';
            analysis.synergies.forEach(s => {
                const item = document.createElement('div');
                item.style.cssText = 'display: flex; align-items: flex-start; gap: 6px;';
                item.innerHTML = `<span style="color: var(--accent-color); font-weight: bold;">&bull;</span> <span>${s}</span>`;
                ideaSynergiesList.appendChild(item);
            });
        }
    }

    function renderRankedIdeaCards(ideas) {
        if (!ideaCardsGrid) return;
        ideaCardsGrid.innerHTML = '';
        ideaCardsGrid.style.display = 'grid';

        (ideas || []).forEach((idea, index) => {
            const card = document.createElement('div');
            card.className = 'idea-project-card';
            card.style.cssText = 'background: rgba(0, 20, 30, 0.5); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; cursor: pointer; transition: transform 0.2s ease, border-color 0.2s ease; position: relative; overflow: hidden; user-select: none;';
            card.onmouseenter = () => { card.style.borderColor = 'var(--accent-color)'; card.style.transform = 'translateY(-2px)'; };
            card.onmouseleave = () => { card.style.borderColor = 'var(--border-color)'; card.style.transform = 'none'; };

            const rankNum = index + 1;
            const scoreVal = Math.round(idea.score?.overall_score || 0);
            const tierStr = (idea.score?.tier || 'Good').toUpperCase();
            const tierColor = scoreVal >= 90 ? '#00ffcc' : (scoreVal >= 80 ? '#00d2ff' : '#ffaa00');
            const techList = idea.technology_usage || [];

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                    <span style="font-size: 0.65rem; font-family: var(--font-mono); color: var(--accent-color); background: rgba(0, 210, 255, 0.1); padding: 2px 6px; border-radius: 4px;">#${rankNum} RANK</span>
                    <span style="font-size: 0.75rem; font-family: var(--font-mono); font-weight: bold; color: ${tierColor};">${scoreVal}/100 <small style="font-size: 0.6rem;">${tierStr}</small></span>
                </div>
                <div>
                    <h4 style="font-size: 0.95rem; color: #fff; margin: 0 0 4px 0; font-weight: 600;">${idea.title || 'Untitled Project'}</h4>
                    <p style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4; margin: 0;">${idea.one_line_pitch || ''}</p>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: auto;">
                    ${techList.slice(0, 4).map(t => `<span style="font-size: 0.65rem; font-family: var(--font-mono); background: rgba(255,255,255,0.04); color: #94d2bd; padding: 2px 6px; border-radius: 4px;">${t.technology || t}</span>`).join('')}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem; color: var(--text-secondary); border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; margin-top: 4px;">
                    <span>⏱ ${idea.estimated_time || '2 weeks'}</span>
                    <span class="view-blueprint-link" style="color: var(--accent-color); font-weight: bold;">VIEW BLUEPRINT &rarr;</span>
                </div>
            `;

            card.addEventListener('click', (e) => {
                e.preventDefault();
                playClickBeep();
                openIdeaModal(idea);
            });

            ideaCardsGrid.appendChild(card);
        });
    }

    function openIdeaModal(idea) {
        if (!idea || !ideaDetailsModal) return;
        selectedIdeaForModal = idea;

        try {
            if (ideaModalTitle) ideaModalTitle.innerText = idea.title || 'PROJECT BLUEPRINT';
            if (ideaModalTierBadge) {
                const s = Math.round(idea.score?.overall_score || 0);
                const t = (idea.score?.tier || 'Good').toUpperCase();
                ideaModalTierBadge.innerText = `${s}/100 ${t}`;
            }
            if (ideaModalPitch) ideaModalPitch.innerText = idea.one_line_pitch || '';
            if (ideaModalSolution) ideaModalSolution.innerText = idea.solution || '';

            // Render Score Breakdown
            if (ideaModalScoresGrid) {
                const sc = idea.score || {};
                ideaModalScoresGrid.innerHTML = `
                    <div style="background: rgba(0,210,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--text-secondary);">STACK FIT (25%)</div>
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--accent-color);">${sc.stack_compatibility || 0}</div>
                    </div>
                    <div style="background: rgba(0,210,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--text-secondary);">FEASIBILITY (20%)</div>
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--accent-color);">${sc.feasibility || 0}</div>
                    </div>
                    <div style="background: rgba(0,210,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--text-secondary);">REAL VALUE (20%)</div>
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--accent-color);">${sc.real_world_value || 0}</div>
                    </div>
                    <div style="background: rgba(0,210,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--text-secondary);">TECH DEPTH (15%)</div>
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--accent-color);">${sc.technical_depth || 0}</div>
                    </div>
                    <div style="background: rgba(0,210,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 0.65rem; color: var(--text-secondary);">PORTFOLIO (10%)</div>
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--accent-color);">${sc.portfolio_value || 0}</div>
                    </div>
                `;
            }

            // Problem & Target Users
            if (ideaModalProblem) ideaModalProblem.innerText = idea.problem || '';
            if (ideaModalUsers) {
                ideaModalUsers.innerHTML = '';
                (idea.target_users || []).forEach(u => {
                    const li = document.createElement('li');
                    li.innerText = u;
                    ideaModalUsers.appendChild(li);
                });
            }

            // Tech Mapping Table
            if (ideaModalTechTbody) {
                ideaModalTechTbody.innerHTML = '';
                (idea.technology_usage || []).forEach(m => {
                    const tr = document.createElement('tr');
                    tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.05);';
                    tr.innerHTML = `
                        <td style="padding: 8px 12px; font-weight: bold; color: var(--accent-color); font-family: var(--font-mono);">${m.technology || ''}</td>
                        <td style="padding: 8px 12px; color: #fff;">${m.role || ''}</td>
                        <td style="padding: 8px 12px; color: var(--text-secondary);">${m.justification || ''}</td>
                    `;
                    ideaModalTechTbody.appendChild(tr);
                });
            }

            // Features
            if (ideaModalFeatures) {
                ideaModalFeatures.innerHTML = '';
                (idea.core_features || []).forEach(f => {
                    const li = document.createElement('li');
                    li.innerText = f;
                    ideaModalFeatures.appendChild(li);
                });
            }

            // Architecture & Data Flow
            if (ideaModalArch) ideaModalArch.innerText = idea.architecture_summary || '';
            if (ideaModalDataflow) {
                ideaModalDataflow.innerHTML = '';
                (idea.data_flow || []).forEach(df => {
                    const step = document.createElement('div');
                    step.innerHTML = `<span style="color: var(--accent-color); font-family: var(--font-mono);">&rarr;</span> ${df}`;
                    ideaModalDataflow.appendChild(step);
                });
            }

            // Roadmap
            if (ideaModalRoadmap) {
                ideaModalRoadmap.innerHTML = '';
                (idea.roadmap || []).forEach(phase => {
                    const pCard = document.createElement('div');
                    pCard.style.cssText = 'background: rgba(0, 20, 30, 0.5); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px; font-size: 0.75rem;';
                    const tasks = phase.key_tasks || [];
                    pCard.innerHTML = `
                        <div style="font-weight: bold; color: var(--accent-color); margin-bottom: 4px;">${phase.phase_name || 'Phase'} <small style="color: var(--text-secondary);">(${phase.duration || ''})</small></div>
                        <ul style="margin: 0; padding-left: 14px; color: var(--text-primary);">
                            ${tasks.map(t => `<li>${t}</li>`).join('')}
                        </ul>
                    `;
                    ideaModalRoadmap.appendChild(pCard);
                });
            }

            // Risks & Mitigations
            if (ideaModalRisks) {
                ideaModalRisks.innerHTML = '';
                const risksList = (idea.risks && idea.risks.length > 0) ? idea.risks : [
                    { risk: "Data Consistency & Latency", mitigation: "Implement asynchronous queue buffering and database indexing." },
                    { risk: "Third-Party Rate Limits", mitigation: "Apply token bucket rate-limiting and client-side caching." }
                ];
                risksList.forEach(r => {
                    const li = document.createElement('li');
                    li.style.marginBottom = '4px';
                    if (typeof r === 'string') {
                        if (r.includes(':')) {
                            const [rT, rM] = r.split(':', 2);
                            li.innerHTML = `<strong style="color: #ff9999;">${rT.trim()}</strong>: <span style="color: var(--text-secondary);">${rM.trim()}</span>`;
                        } else {
                            li.innerHTML = `<span style="color: var(--text-primary);">${r}</span>`;
                        }
                    } else {
                        const rTitle = r.risk || r.title || 'Technical Risk';
                        const rMit = r.mitigation || r.mitigate || 'Follow architectural best practices.';
                        li.innerHTML = `<strong style="color: #ff9999;">${rTitle}</strong>: <span style="color: var(--text-secondary);">${rMit}</span>`;
                    }
                    ideaModalRisks.appendChild(li);
                });
            }

            // Future Expansion
            if (ideaModalFuture) {
                ideaModalFuture.innerHTML = '';
                const futureList = (idea.future_expansion && idea.future_expansion.length > 0) ? idea.future_expansion : [
                    "Multi-tenant organization workspaces with granular role-based access control",
                    "Automated webhook integrations with Slack, Discord, and GitHub CI/CD",
                    "Predictive AI anomaly detection and telemetry forecasting models"
                ];
                futureList.forEach(fe => {
                    const li = document.createElement('li');
                    li.style.marginBottom = '4px';
                    const text = typeof fe === 'string' ? fe : (fe.feature || fe.title || fe.description || JSON.stringify(fe));
                    li.innerText = text;
                    ideaModalFuture.appendChild(li);
                });
            }

            ideaDetailsModal.classList.add('open');
        } catch (err) {
            console.error('Failed to open idea modal:', err);
        }
    }

    const closeIdeaModal = () => {
        if (ideaDetailsModal) {
            ideaDetailsModal.classList.remove('open');
        }
    };

    if (ideaModalCloseX) ideaModalCloseX.addEventListener('click', closeIdeaModal);
    if (ideaModalCloseBtn) ideaModalCloseBtn.addEventListener('click', closeIdeaModal);
    if (ideaDetailsModal) {
        ideaDetailsModal.addEventListener('click', (e) => {
            if (e.target === ideaDetailsModal) closeIdeaModal();
        });
    }

    if (ideaModalCopyBtn) {
        ideaModalCopyBtn.addEventListener('click', () => {
            if (!selectedIdeaForModal) return;
            const md = `# ${selectedIdeaForModal.title}\n\n`
                + `> ${selectedIdeaForModal.one_line_pitch}\n\n`
                + `**Overall Score:** ${Math.round(selectedIdeaForModal.score.overall_score)}/100 (${selectedIdeaForModal.score.tier})\n`
                + `**Difficulty:** ${selectedIdeaForModal.difficulty} | **Estimated Time:** ${selectedIdeaForModal.estimated_time}\n\n`
                + `## Problem\n${selectedIdeaForModal.problem}\n\n`
                + `## Solution\n${selectedIdeaForModal.solution}\n\n`
                + `## Architecture\n${selectedIdeaForModal.architecture_summary}\n\n`
                + `## Tech Stack Roles\n`
                + selectedIdeaForModal.technology_usage.map(t => `- **${t.technology}**: ${t.role} (${t.justification})`).join('\n')
                + `\n\n## Core Features\n`
                + selectedIdeaForModal.core_features.map(f => `- ${f}`).join('\n');

            navigator.clipboard.writeText(md).then(() => {
                const orig = ideaModalCopyBtn.innerText;
                ideaModalCopyBtn.innerText = 'COPIED!';
                setTimeout(() => { ideaModalCopyBtn.innerText = orig; }, 1500);
            });
        });
    }

    // ==========================================
    // J.A.R.V.I.S. MASTER BUILD PROMPT ENGINE
    // ==========================================
    const masterPromptModal = document.getElementById('master-prompt-modal');
    const promptModalCloseX = document.getElementById('prompt-modal-close-x');
    const btnCloseMasterPrompt = document.getElementById('btn-close-master-prompt');
    const btnOpenMasterPrompt = document.getElementById('btn-open-master-prompt');
    const btnCopyMasterPrompt = document.getElementById('btn-copy-master-prompt');
    const btnSaveMasterPrompt = document.getElementById('btn-save-master-prompt');
    const btnRegeneratePrompt = document.getElementById('btn-regenerate-prompt');

    const promptModalTitle = document.getElementById('prompt-modal-title');
    const promptModalSubtitle = document.getElementById('prompt-modal-subtitle');
    const promptVisualSelect = document.getElementById('prompt-visual-select');
    const promptMotionSelect = document.getElementById('prompt-motion-select');
    const prompt3dSelect = document.getElementById('prompt-3d-select');
    const promptPlatformSelect = document.getElementById('prompt-platform-select');
    const promptMarkdownDisplay = document.getElementById('prompt-markdown-display');

    const promptScoreOverall = document.getElementById('prompt-score-overall');
    const promptScoreTech = document.getElementById('prompt-score-tech');
    const promptScoreUx = document.getElementById('prompt-score-ux');
    const promptScoreVis = document.getElementById('prompt-score-vis');
    const promptScoreImpl = document.getElementById('prompt-score-impl');

    let currentMasterPrompt = null;

    async function openMasterPromptModal() {
        if (!selectedIdeaForModal) return;
        if (promptModalTitle) promptModalTitle.innerText = `MASTER BUILD SPECIFICATION: ${selectedIdeaForModal.title.toUpperCase()}`;
        if (promptModalSubtitle) promptModalSubtitle.innerText = `AI-Readable Engineering & Creative Spec for ${selectedIdeaForModal.title}`;
        
        if (masterPromptModal) masterPromptModal.classList.add('open');
        await generateAndRenderMasterPrompt();
    }

    async function generateAndRenderMasterPrompt() {
        if (!selectedIdeaForModal) return;
        if (promptMarkdownDisplay) {
            promptMarkdownDisplay.innerText = '⚡ Synthesizing 25+ section Master Build Specification and Creative Direction...';
        }

        const payload = {
            idea_id: selectedIdeaForModal.id,
            idea: selectedIdeaForModal,
            visual_direction: promptVisualSelect ? promptVisualSelect.value : 'Auto (AI-Determined)',
            motion_level: promptMotionSelect ? promptMotionSelect.value : 'Balanced',
            threed_intensity: prompt3dSelect ? prompt3dSelect.value : 'Auto (AI-Determined)',
            target_platform: promptPlatformSelect ? promptPlatformSelect.value : 'Universal'
        };

        try {
            const res = await fetch(`${apiBase}/api/idea_engine/generate_master_prompt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success && data.prompt) {
                currentMasterPrompt = data.prompt;
                renderMasterPrompt(data.prompt);
            } else {
                if (promptMarkdownDisplay) promptMarkdownDisplay.innerText = `Error: ${data.error || 'Failed to generate prompt'}`;
            }
        } catch (err) {
            console.error('Failed to generate master build prompt:', err);
            if (promptMarkdownDisplay) promptMarkdownDisplay.innerText = 'Connection error: Unable to generate prompt from mainframe.';
        }
    }

    function renderMasterPrompt(prompt) {
        if (promptMarkdownDisplay) {
            promptMarkdownDisplay.innerText = prompt.platform_adapted_prompt || prompt.full_markdown_prompt;
        }

        // Render Completeness Scores
        const scores = prompt.completeness_scores || {};
        if (promptScoreOverall) promptScoreOverall.innerText = `${scores.overall || 95}%`;
        if (promptScoreTech) promptScoreTech.innerText = `${scores.technical || 96}%`;
        if (promptScoreUx) promptScoreUx.innerText = `${scores.ux_ui || 94}%`;
        if (promptScoreVis) promptScoreVis.innerText = `${scores.visual_direction || 95}%`;
        if (promptScoreImpl) promptScoreImpl.innerText = `${scores.implementation || 95}%`;
    }

    const closeMasterPromptModal = () => {
        if (masterPromptModal) masterPromptModal.classList.remove('open');
    };

    if (btnOpenMasterPrompt) btnOpenMasterPrompt.addEventListener('click', openMasterPromptModal);
    if (promptModalCloseX) promptModalCloseX.addEventListener('click', closeMasterPromptModal);
    if (btnCloseMasterPrompt) btnCloseMasterPrompt.addEventListener('click', closeMasterPromptModal);
    if (masterPromptModal) {
        masterPromptModal.addEventListener('click', (e) => {
            if (e.target === masterPromptModal) closeMasterPromptModal();
        });
    }

    if (btnRegeneratePrompt) {
        btnRegeneratePrompt.addEventListener('click', () => {
            generateAndRenderMasterPrompt();
        });
    }

    if (btnCopyMasterPrompt) {
        btnCopyMasterPrompt.addEventListener('click', () => {
            if (!currentMasterPrompt) return;
            const textToCopy = currentMasterPrompt.platform_adapted_prompt || currentMasterPrompt.full_markdown_prompt;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const orig = btnCopyMasterPrompt.innerText;
                btnCopyMasterPrompt.innerText = '✓ MASTER PROMPT COPIED!';
                btnCopyMasterPrompt.style.background = 'var(--success-color)';
                btnCopyMasterPrompt.style.color = '#000';
                setTimeout(() => {
                    btnCopyMasterPrompt.innerText = orig;
                    btnCopyMasterPrompt.style.background = '';
                    btnCopyMasterPrompt.style.color = '';
                }, 1800);
            });
        });
    }

    if (btnSaveMasterPrompt) {
        btnSaveMasterPrompt.addEventListener('click', async () => {
            if (!currentMasterPrompt) return;
            try {
                const res = await fetch(`${apiBase}/api/idea_engine/save_master_prompt`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt_id: currentMasterPrompt.prompt_id })
                });
                const d = await res.json();
                if (d.success) {
                    const orig = btnSaveMasterPrompt.innerText;
                    btnSaveMasterPrompt.innerText = '✓ SAVED TO MEMORY!';
                    setTimeout(() => { btnSaveMasterPrompt.innerText = orig; }, 1500);
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    // ==========================================
    // J.A.R.V.I.S. INTELLIGENCE HUB CONTROLLER
    // ==========================================
    const intelTabBtns = document.querySelectorAll('.intel-tab-btn');
    const intelPanels = {
        project: document.getElementById('intel-panel-project'),
        goal: document.getElementById('intel-panel-goal'),
        memory: document.getElementById('intel-panel-memory'),
        skills: document.getElementById('intel-panel-skills'),
        performance: document.getElementById('intel-panel-performance')
    };
    let activeIntelTab = 'project';

    intelTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            intelTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeIntelTab = btn.dataset.tab;
            
            Object.keys(intelPanels).forEach(key => {
                if (intelPanels[key]) {
                    intelPanels[key].style.display = (key === activeIntelTab) ? 'flex' : 'none';
                }
            });
            loadCurrentIntelTab();
        });
    });

    function loadCurrentIntelTab() {
        if (activeIntelTab === 'memory') {
            loadMemoryEntries();
        } else if (activeIntelTab === 'skills') {
            loadSkillsRegistry();
        } else if (activeIntelTab === 'performance') {
            loadPerformanceTelemetry();
        }
    }

    // 1. Project Analyzer Controller
    const projectScanPath = document.getElementById('project-scan-path');
    const btnScanProject = document.getElementById('btn-scan-project');
    const projectReportContainer = document.getElementById('project-report-container');
    const projectOverallScore = document.getElementById('project-overall-score');
    const projectOverallTier = document.getElementById('project-overall-tier');
    const projectSubscoresGrid = document.getElementById('project-subscores-grid');
    const projectLanguagesList = document.getElementById('project-languages-list');
    const projectFrameworksList = document.getElementById('project-frameworks-list');
    const projectFindingsTbody = document.getElementById('project-findings-tbody');

    if (btnScanProject) {
        btnScanProject.addEventListener('click', async () => {
            const rawUrl = projectScanPath ? projectScanPath.value.trim() : '';
            if (!rawUrl || rawUrl === '.' || !/^https?:\/\/github\.com\/[^\/\s]+\/[^\/\s]+/i.test(rawUrl)) {
                alert('Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)');
                if (projectScanPath) projectScanPath.focus();
                return;
            }

            btnScanProject.disabled = true;
            btnScanProject.innerText = 'CLONING & SCANNING...';

            try {
                const res = await fetch(`${apiBase}/api/intelligence/analyze_project`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_path: rawUrl })
                });
                const data = await res.json();
                if (data.success && data.report) {
                    renderProjectReport(data.report);
                    appendLog('INTELLIGENCE', `GitHub scan completed for ${rawUrl}. Overall Health: ${data.report.scores.overall}/100`, 'assistant-log');
                } else {
                    alert(`Scan failed: ${data.error || 'Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)'}`);
                }
            } catch (err) {
                console.error(err);
                alert('Failed to connect to Intelligence API for project inspection.');
            } finally {
                btnScanProject.disabled = false;
                btnScanProject.innerText = 'INSPECT GITHUB REPO';
            }
        });
    }

    function renderProjectReport(report) {
        if (!projectReportContainer) return;
        projectReportContainer.style.display = 'flex';

        // Overall Score & Tier
        const overall = Math.round(report.scores.overall || 0);
        if (projectOverallScore) projectOverallScore.innerText = overall;
        if (projectOverallTier) {
            if (overall >= 85) {
                projectOverallTier.innerText = 'EXCELLENT';
                projectOverallTier.style.color = 'var(--success-color)';
                projectOverallTier.style.background = 'rgba(0, 255, 204, 0.1)';
            } else if (overall >= 70) {
                projectOverallTier.innerText = 'GOOD / STABLE';
                projectOverallTier.style.color = 'var(--accent-color)';
                projectOverallTier.style.background = 'rgba(0, 210, 255, 0.1)';
            } else {
                projectOverallTier.innerText = 'ATTENTION REQUIRED';
                projectOverallTier.style.color = '#ffaa00';
                projectOverallTier.style.background = 'rgba(255, 170, 0, 0.1)';
            }
        }

        // Subscores
        if (projectSubscoresGrid) {
            projectSubscoresGrid.innerHTML = '';
            const scoresMap = [
                { key: 'Architecture', val: report.scores.architecture },
                { key: 'Code Quality', val: report.scores.code_quality },
                { key: 'Security Posture', val: report.scores.security },
                { key: 'Automated Tests', val: report.scores.testing },
                { key: 'Documentation', val: report.scores.documentation },
                { key: 'Maintainability', val: report.scores.maintainability }
            ];
            scoresMap.forEach(s => {
                const card = document.createElement('div');
                card.className = 'intel-stat-card';
                card.innerHTML = `
                    <div class="label">${s.key.toUpperCase()}</div>
                    <div class="value">${Math.round(s.val)}<span style="font-size: 0.75rem; color: var(--text-secondary);">/100</span></div>
                `;
                projectSubscoresGrid.appendChild(card);
            });
        }

        // Languages & Lines
        if (projectLanguagesList) {
            projectLanguagesList.innerHTML = '';
            Object.entries(report.languages || {}).forEach(([lang, count]) => {
                const tag = document.createElement('span');
                tag.style.cssText = 'background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.25); color: var(--text-primary); font-size: 0.75rem; padding: 4px 10px; border-radius: 4px; font-family: var(--font-mono);';
                tag.innerText = `${lang} (${count} files)`;
                projectLanguagesList.appendChild(tag);
            });
            const metricsPill = document.createElement('span');
            metricsPill.style.cssText = 'background: rgba(0, 255, 204, 0.1); border: 1px solid rgba(0, 255, 204, 0.3); color: var(--success-color); font-size: 0.75rem; padding: 4px 10px; border-radius: 4px; font-family: var(--font-mono);';
            metricsPill.innerText = `Total: ${report.total_files} files, ${report.total_lines} lines`;
            projectLanguagesList.appendChild(metricsPill);
        }

        // Frameworks
        if (projectFrameworksList) {
            projectFrameworksList.innerHTML = '';
            (report.frameworks || []).forEach(fw => {
                const tag = document.createElement('span');
                tag.style.cssText = 'background: rgba(147, 51, 234, 0.15); border: 1px solid rgba(147, 51, 234, 0.3); color: #c084fc; font-size: 0.75rem; padding: 4px 10px; border-radius: 4px; font-family: var(--font-mono);';
                tag.innerText = fw;
                projectFrameworksList.appendChild(tag);
            });
        }

        // Findings Table
        if (projectFindingsTbody) {
            projectFindingsTbody.innerHTML = '';
            const findings = report.findings || [];
            if (findings.length === 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="5" style="padding: 16px; text-align: center; color: var(--success-color);">Zero critical security or architecture defects detected. Codebase in sound health.</td>`;
                projectFindingsTbody.appendChild(tr);
            } else {
                findings.forEach(f => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
                    
                    let sevBg = 'rgba(0, 210, 255, 0.15)';
                    let sevColor = 'var(--accent-color)';
                    if (f.severity === 'high' || f.severity === 'critical') {
                        sevBg = 'rgba(255, 59, 48, 0.2)';
                        sevColor = 'var(--danger-color)';
                    } else if (f.severity === 'medium') {
                        sevBg = 'rgba(255, 170, 0, 0.2)';
                        sevColor = '#ffaa00';
                    }

                    tr.innerHTML = `
                        <td style="padding: 10px 8px;"><span style="background: ${sevBg}; color: ${sevColor}; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.65rem; font-family: var(--font-mono);">${f.severity.toUpperCase()}</span></td>
                        <td style="padding: 10px 8px; color: var(--text-secondary);">${f.category}</td>
                        <td style="padding: 10px 8px; font-family: var(--font-mono); color: var(--accent-color);">${f.file} <span style="color: var(--text-muted);">(${f.location})</span></td>
                        <td style="padding: 10px 8px;"><strong>${f.problem}</strong><br><span style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-secondary); background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 2px;">${f.evidence}</span></td>
                        <td style="padding: 10px 8px; color: #bde0fe;">${f.recommendation}</td>
                    `;
                    projectFindingsTbody.appendChild(tr);
                });
            }
        }
    }

    // 2. Goal Decomposition Controller
    const goalInput = document.getElementById('goal-input');
    const btnDecomposeGoal = document.getElementById('btn-decompose-goal');
    const goalPlanContainer = document.getElementById('goal-plan-container');
    const goalPlanTitle = document.getElementById('goal-plan-title');
    const goalPlanCount = document.getElementById('goal-plan-count');
    const goalTasksList = document.getElementById('goal-tasks-list');

    if (btnDecomposeGoal) {
        btnDecomposeGoal.addEventListener('click', async () => {
            const goalText = (goalInput ? goalInput.value.trim() : '');
            if (!goalText) {
                alert('Please enter a goal or project objective to decompose.');
                return;
            }
            btnDecomposeGoal.disabled = true;
            btnDecomposeGoal.innerText = 'GENERATING TASK GRAPH...';

            try {
                const res = await fetch(`${apiBase}/api/intelligence/decompose_goal`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ goal: goalText })
                });
                const data = await res.json();
                if (data.success && data.plan) {
                    renderGoalPlan(data.plan);
                    appendLog('INTELLIGENCE', `Goal decomposed into ${data.plan.tasks.length} tasks. Critical path ready.`, 'assistant-log');
                } else {
                    alert(`Decomposition failed: ${data.error || 'Unknown error'}`);
                }
            } catch (err) {
                console.error(err);
                alert('Failed to connect to Intelligence API for goal decomposition.');
            } finally {
                btnDecomposeGoal.disabled = false;
                btnDecomposeGoal.innerText = 'DECOMPOSE OBJECTIVE';
            }
        });
    }

    function renderGoalPlan(plan) {
        if (!goalPlanContainer) return;
        goalPlanContainer.style.display = 'flex';
        if (goalPlanTitle) goalPlanTitle.innerText = `OBJECTIVE: ${plan.goal}`;
        if (goalPlanCount) goalPlanCount.innerText = `${plan.tasks.length} Execution Tasks`;

        if (goalTasksList) {
            goalTasksList.innerHTML = '';
            plan.tasks.forEach((t, idx) => {
                const card = document.createElement('div');
                card.style.cssText = 'background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 8px;';
                
                const isCritPath = (plan.critical_path || []).includes(t.id);
                const critPill = isCritPath ? `<span style="font-size: 0.65rem; font-family: var(--font-mono); color: #ffaa00; background: rgba(255,170,0,0.1); border: 1px solid rgba(255,170,0,0.3); padding: 2px 6px; border-radius: 4px;">CRITICAL PATH</span>` : '';
                
                const depsHtml = (t.dependencies && t.dependencies.length > 0)
                    ? `<div style="font-size: 0.7rem; color: var(--text-secondary); font-family: var(--font-mono);">Requires: ${t.dependencies.map(d => `<span style="background: rgba(0,210,255,0.1); color: var(--accent-color); padding: 1px 5px; border-radius: 3px;">${d}</span>`).join(' ')}</div>`
                    : `<div style="font-size: 0.7rem; color: var(--success-color); font-family: var(--font-mono);">Root Task (No Dependencies)</div>`;

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-color); font-weight: bold;">[${t.id}]</span>
                            <span style="font-size: 0.85rem; font-weight: bold; color: var(--text-primary);">${t.title}</span>
                            ${critPill}
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <span style="font-size: 0.65rem; font-family: var(--font-mono); background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary);">${t.category}</span>
                            <span style="font-size: 0.65rem; font-family: var(--font-mono); background: rgba(0,210,255,0.15); color: var(--accent-color); padding: 2px 6px; border-radius: 4px;">${t.estimated_effort}</span>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4;">${t.description}</div>
                    ${depsHtml}
                `;
                goalTasksList.appendChild(card);
            });
        }
    }

    // 3. Memory Inspector Controller
    const memorySearchInput = document.getElementById('memory-search-input');
    const memoryTypeFilters = document.querySelectorAll('.mem-filter-btn');
    const memoryEntriesGrid = document.getElementById('memory-entries-grid');
    let activeMemoryFilter = 'all';

    memoryTypeFilters.forEach(btn => {
        btn.addEventListener('click', () => {
            memoryTypeFilters.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeMemoryFilter = btn.dataset.type;
            loadMemoryEntries();
        });
    });

    if (memorySearchInput) {
        memorySearchInput.addEventListener('input', () => {
            loadMemoryEntries();
        });
    }

    async function loadMemoryEntries() {
        if (!memoryEntriesGrid) return;
        const q = memorySearchInput ? memorySearchInput.value.trim() : '';
        let url = `${apiBase}/api/intelligence/memory?query=${encodeURIComponent(q)}`;
        if (activeMemoryFilter && activeMemoryFilter !== 'all') {
            url += `&type=${encodeURIComponent(activeMemoryFilter)}`;
        }

        try {
            const res = await fetch(url);
            const data = await res.json();
            if (data.success) {
                renderMemoryEntries(data.entries || []);
            }
        } catch (err) {
            console.error('Failed to load memory entries:', err);
        }
    }

    function renderMemoryEntries(entries) {
        if (!memoryEntriesGrid) return;
        memoryEntriesGrid.innerHTML = '';

        if (entries.length === 0) {
            memoryEntriesGrid.innerHTML = `<div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-secondary); font-size: 0.8rem;">No memory records match the selected filter.</div>`;
            return;
        }

        entries.forEach(entry => {
            const card = document.createElement('div');
            card.style.cssText = 'background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 8px; position: relative;';
            
            const confPercent = Math.round(entry.confidence * 100);
            const tagsHtml = (entry.tags || []).map(t => `<span style="font-size: 0.65rem; font-family: var(--font-mono); color: var(--accent-color); background: rgba(0,210,255,0.08); padding: 1px 5px; border-radius: 3px;">#${t}</span>`).join(' ');

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 0.65rem; font-family: var(--font-mono); background: rgba(0, 210, 255, 0.15); color: var(--accent-color); padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">${entry.type}</span>
                        <span style="font-size: 0.65rem; color: var(--text-secondary); font-family: var(--font-mono);">Conf: ${confPercent}%</span>
                    </div>
                    <button class="mem-delete-btn" data-id="${entry.id}" style="background: transparent; border: none; color: var(--danger-color); cursor: pointer; font-size: 0.75rem; opacity: 0.6;" title="Delete Record">&times;</button>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-primary); line-height: 1.4;">${entry.content}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; pt: 4px;">
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">${tagsHtml}</div>
                    <span style="font-size: 0.65rem; font-family: var(--font-mono); color: var(--text-muted);">${entry.source}</span>
                </div>
            `;

            const delBtn = card.querySelector('.mem-delete-btn');
            if (delBtn) {
                delBtn.addEventListener('click', async () => {
                    if (confirm('Delete this memory record from permanent storage?')) {
                        try {
                            const res = await fetch(`${apiBase}/api/intelligence/memory?id=${entry.id}`, { method: 'DELETE' });
                            const d = await res.json();
                            if (d.success) {
                                loadMemoryEntries();
                            }
                        } catch (e) {
                            console.error('Delete memory error:', e);
                        }
                    }
                });
            }

            memoryEntriesGrid.appendChild(card);
        });
    }

    // 4. Skills Registry Controller
    const skillsRegistryGrid = document.getElementById('skills-registry-grid');

    async function loadSkillsRegistry() {
        if (!skillsRegistryGrid) return;
        try {
            const res = await fetch(`${apiBase}/api/intelligence/skills`);
            const data = await res.json();
            if (data.success) {
                renderSkillsRegistry(data.skills || []);
            }
        } catch (err) {
            console.error('Failed to load skills registry:', err);
        }
    }

    function renderSkillsRegistry(skills) {
        if (!skillsRegistryGrid) return;
        skillsRegistryGrid.innerHTML = '';

        skills.forEach(s => {
            const card = document.createElement('div');
            card.style.cssText = 'background: rgba(0, 20, 30, 0.5); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 8px;';
            
            let riskBg = 'rgba(0, 210, 255, 0.15)';
            let riskColor = 'var(--accent-color)';
            if (s.risk_level === 'HIGH' || s.risk_level === 'CRITICAL') {
                riskBg = 'rgba(255, 59, 48, 0.2)';
                riskColor = 'var(--danger-color)';
            } else if (s.risk_level === 'MEDIUM') {
                riskBg = 'rgba(255, 170, 0, 0.2)';
                riskColor = '#ffaa00';
            }

            const permsHtml = (s.permissions || []).map(p => `<span style="font-size: 0.6rem; font-family: var(--font-mono); background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 3px; color: var(--text-secondary);">${p}</span>`).join(' ');

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.85rem; font-weight: bold; color: var(--accent-color); font-family: var(--font-mono);">${s.name}</span>
                    <span style="font-size: 0.65rem; font-family: var(--font-mono); background: ${riskBg}; color: ${riskColor}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">RISK: ${s.risk_level}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4;">${s.description}</div>
                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 6px;">
                    <span style="font-size: 0.65rem; color: var(--text-muted); font-family: var(--font-mono);">REQUIRED PERMISSIONS:</span>
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">${permsHtml}</div>
                </div>
            `;
            skillsRegistryGrid.appendChild(card);
        });
    }

    // 5. Performance HUD Controller
    const perfGaugesGrid = document.getElementById('perf-gauges-grid');
    const perfAnomaliesBox = document.getElementById('perf-anomalies-box');
    const perfAnomaliesList = document.getElementById('perf-anomalies-list');

    async function loadPerformanceTelemetry() {
        if (!perfGaugesGrid) return;
        try {
            const res = await fetch(`${apiBase}/api/intelligence/performance`);
            const data = await res.json();
            if (data.success && data.performance) {
                renderPerformanceHUD(data.performance);
            }
        } catch (err) {
            console.error('Failed to load performance telemetry:', err);
        }
    }

    function renderPerformanceHUD(perf) {
        if (!perfGaugesGrid) return;
        perfGaugesGrid.innerHTML = '';

        const metrics = [
            { label: 'AVG SYSTEM LATENCY', val: `${Math.round(perf.avg_response_ms)} ms` },
            { label: 'DECISION ENGINE', val: `${Math.round(perf.decision_ms)} ms` },
            { label: 'PERCEPTION ENGINE', val: `${Math.round(perf.perception_ms)} ms` },
            { label: 'OCR LATENCY', val: `${Math.round(perf.ocr_ms)} ms` },
            { label: 'ACTION EXECUTION', val: `${Math.round(perf.execution_ms)} ms` },
            { label: 'VERIFICATION ENGINE', val: `${Math.round(perf.verification_ms)} ms` },
            { label: 'MEMORY RETRIEVAL', val: `${Math.round(perf.memory_retrieval_ms)} ms` },
            { label: 'TOOL SUCCESS RATE', val: `${Math.round(perf.tool_success_rate)}%`, color: 'var(--success-color)' },
            { label: 'AI FAILURE RATE', val: `${Math.round(perf.ai_failure_rate)}%`, color: perf.ai_failure_rate > 5 ? 'var(--danger-color)' : 'var(--text-primary)' }
        ];

        metrics.forEach(m => {
            const card = document.createElement('div');
            card.className = 'intel-stat-card';
            card.innerHTML = `
                <div class="label">${m.label}</div>
                <div class="value" style="${m.color ? `color: ${m.color};` : ''}">${m.val}</div>
            `;
            perfGaugesGrid.appendChild(card);
        });

        // Anomalies
        if (perfAnomaliesBox && perfAnomaliesList) {
            const anoms = perf.anomalies || [];
            if (anoms.length > 0) {
                perfAnomaliesBox.style.display = 'block';
                perfAnomaliesList.innerHTML = anoms.map(a => `<li>${a}</li>`).join('');
            } else {
                perfAnomaliesBox.style.display = 'none';
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SEO Intelligence & Scoring Engine UI Controller
    // ─────────────────────────────────────────────────────────────────────────
    const seoModal = document.getElementById('seo-modal');
    const launchSeoBtn = document.getElementById('launch-seo-btn');
    const btnCardSeo = document.getElementById('btn-card-seo');
    const seoModalCloseX = document.getElementById('seo-modal-close-x');
    const seoModalCloseBtn = document.getElementById('seo-modal-close-btn');

    const seoModeUrlBtn = document.getElementById('seo-mode-url-btn');
    const seoModeProjectBtn = document.getElementById('seo-mode-project-btn');
    const seoUrlInputGroup = document.getElementById('seo-url-input-group');
    const seoProjectInputGroup = document.getElementById('seo-project-input-group');
    const seoUrlInput = document.getElementById('seo-url-input');
    const seoProjectPathInput = document.getElementById('seo-project-path-input');
    const seoKeywordInput = document.getElementById('seo-keyword-input');
    const seoAnalyzeBtn = document.getElementById('seo-analyze-btn');

    const seoInputSection = document.getElementById('seo-input-section');
    const seoAnalyzingState = document.getElementById('seo-analyzing-state');
    const seoProgressCurrentStage = document.getElementById('seo-progress-current-stage');
    const seoErrorBox = document.getElementById('seo-error-box');
    const seoErrorMessage = document.getElementById('seo-error-message');
    const seoResultsContainer = document.getElementById('seo-results-container');

    const seoScoreNum = document.getElementById('seo-score-num');
    const seoTierBadge = document.getElementById('seo-tier-badge');
    const seoTargetDisplay = document.getElementById('seo-target-display');
    const seoStatusBadge = document.getElementById('seo-status-badge');
    const seoSummaryTagline = document.getElementById('seo-summary-tagline');

    const seoStatLatency = document.getElementById('seo-stat-latency');
    const seoStatSize = document.getElementById('seo-stat-size');
    const seoStatWords = document.getElementById('seo-stat-words');
    const seoStatResources = document.getElementById('seo-stat-resources');

    const seoCategoriesGrid = document.getElementById('seo-categories-grid');
    const seoActionPlanList = document.getElementById('seo-action-plan-list');
    const seoActionItemsCount = document.getElementById('seo-action-items-count');
    const seoAiInsightsBox = document.getElementById('seo-ai-insights-box');
    const seoAiInsightsContent = document.getElementById('seo-ai-insights-content');

    const seoFindingsFilters = document.getElementById('seo-findings-filters');
    const seoFindingsList = document.getElementById('seo-findings-list');
    const countFindingsAll = document.getElementById('count-findings-all');
    const countFindingsCrit = document.getElementById('count-findings-crit');
    const countFindingsWarn = document.getElementById('count-findings-warn');
    const countFindingsPass = document.getElementById('count-findings-pass');

    const seoCopyBtn = document.getElementById('seo-copy-btn');
    const seoResetBtn = document.getElementById('seo-reset-btn');

    let currentSeoMode = 'url';
    let currentSeoReport = null;
    let currentFilterSeverity = 'all';

    function openSeoModal() {
        if (!seoModal) return;
        seoModal.classList.add('open');
        if (seoUrlInput && currentSeoMode === 'url') seoUrlInput.focus();
    }

    function closeSeoModal() {
        if (!seoModal) return;
        seoModal.classList.remove('open');
    }

    if (launchSeoBtn) {
        launchSeoBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openSeoModal();
        });
    }

    if (btnCardSeo) {
        btnCardSeo.addEventListener('click', () => {
            openSeoModal();
        });
    }

    if (seoModalCloseX) seoModalCloseX.addEventListener('click', closeSeoModal);
    if (seoModalCloseBtn) seoModalCloseBtn.addEventListener('click', closeSeoModal);
    if (seoModal) {
        seoModal.addEventListener('click', (e) => {
            if (e.target === seoModal) closeSeoModal();
        });
    }

    // Mode Switcher
    if (seoModeUrlBtn && seoModeProjectBtn) {
        seoModeUrlBtn.addEventListener('click', () => {
            currentSeoMode = 'url';
            seoModeUrlBtn.classList.add('active');
            seoModeProjectBtn.classList.remove('active');
            if (seoUrlInputGroup) seoUrlInputGroup.style.display = 'flex';
            if (seoProjectInputGroup) seoProjectInputGroup.style.display = 'none';
            if (seoAnalyzeBtn) seoAnalyzeBtn.innerText = 'ANALYZE WEBSITE';
        });

        seoModeProjectBtn.addEventListener('click', () => {
            currentSeoMode = 'project';
            seoModeProjectBtn.classList.add('active');
            seoModeUrlBtn.classList.remove('active');
            if (seoUrlInputGroup) seoUrlInputGroup.style.display = 'none';
            if (seoProjectInputGroup) seoProjectInputGroup.style.display = 'flex';
            if (seoAnalyzeBtn) seoAnalyzeBtn.innerText = 'INSPECT PROJECT';
        });
    }

    // Stage progression helper
    const stageIds = ['stage-connect', 'stage-fetch', 'stage-meta', 'stage-headings', 'stage-assets', 'stage-schema', 'stage-score'];
    function setProgressStage(activeIdx, message) {
        if (seoProgressCurrentStage) seoProgressCurrentStage.innerText = message;
        stageIds.forEach((sid, idx) => {
            const el = document.getElementById(sid);
            if (!el) return;
            const icon = el.querySelector('.stage-icon');
            if (idx < activeIdx) {
                el.className = 'seo-stage-item completed';
                if (icon) icon.innerText = '✓';
            } else if (idx === activeIdx) {
                el.className = 'seo-stage-item active';
                if (icon) icon.innerText = '●';
            } else {
                el.className = 'seo-stage-item';
                if (icon) icon.innerText = '○';
            }
        });
    }

    // Run SEO Analysis
    async function runSeoAudit() {
        if (seoErrorBox) seoErrorBox.style.display = 'none';
        if (seoResultsContainer) seoResultsContainer.style.display = 'none';
        if (seoCopyBtn) seoCopyBtn.style.display = 'none';
        if (seoResetBtn) seoResetBtn.style.display = 'none';

        const keyword = seoKeywordInput ? seoKeywordInput.value.trim() : '';
        let targetVal = seoUrlInput ? seoUrlInput.value.trim() : '';
        if (!targetVal) {
            showSeoError('Please enter a valid website URL to analyze.');
            return;
        }
        if (!targetVal.startsWith('http://') && !targetVal.startsWith('https://')) {
            targetVal = 'https://' + targetVal;
            if (seoUrlInput) seoUrlInput.value = targetVal;
        }
        let endpoint = `${apiBase}/api/seo/analyze`;
        let requestBody = { url: targetVal, target_keyword: keyword, use_llm: true };

        // Show Analyzing State
        if (seoAnalyzingState) seoAnalyzingState.style.display = 'flex';
        if (seoAnalyzeBtn) {
            seoAnalyzeBtn.disabled = true;
            seoAnalyzeBtn.innerText = 'AUDITING...';
        }

        playTransmissionSweep();
        setProgressStage(0, `Connecting to ${targetVal}...`);

        // Stage progress animation timer while waiting for real backend analysis
        let stageStep = 0;
        const stageMessages = [
            'Retrieving HTML document and security headers...',
            'Auditing technical metadata, title & canonicals...',
            'Evaluating heading hierarchy and content structure...',
            'Inspecting image alt optimization and link graph...',
            'Validating Schema.org JSON-LD and social tags...',
            'Synthesizing score and evidence-grounded action plan...'
        ];

        const progressTimer = setInterval(() => {
            stageStep++;
            if (stageStep < stageIds.length) {
                setProgressStage(stageStep, stageMessages[stageStep - 1] || 'Processing signals...');
            }
        }, 600);

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            clearInterval(progressTimer);
            const data = await res.json();

            if (seoAnalyzingState) seoAnalyzingState.style.display = 'none';
            if (seoAnalyzeBtn) {
                seoAnalyzeBtn.disabled = false;
                seoAnalyzeBtn.innerText = 'ANALYZE WEBSITE';
            }

            if (data.success && data.report) {
                currentSeoReport = data.report;
                playCompletionChirp();
                renderSeoReport(data.report);
            } else {
                playErrorBeep();
                showSeoError(data.error || 'Failed to complete SEO audit.');
            }
        } catch (err) {
            clearInterval(progressTimer);
            if (seoAnalyzingState) seoAnalyzingState.style.display = 'none';
            if (seoAnalyzeBtn) {
                seoAnalyzeBtn.disabled = false;
                seoAnalyzeBtn.innerText = 'ANALYZE WEBSITE';
            }
            playErrorBeep();
            showSeoError(`Network communication error: ${err.message}`);
        }
    }

    function showSeoError(msg) {
        if (seoErrorBox && seoErrorMessage) {
            seoErrorMessage.innerText = msg;
            seoErrorBox.style.display = 'flex';
        }
    }

    function renderSeoReport(report) {
        if (!seoResultsContainer) return;
        seoResultsContainer.style.display = 'flex';
        if (seoCopyBtn) seoCopyBtn.style.display = 'block';
        if (seoResetBtn) seoResetBtn.style.display = 'block';

        // 1. Overview Score & Badge
        const score = report.overall_score || 0;
        if (seoScoreNum) seoScoreNum.innerText = Math.round(score);
        if (seoTierBadge) {
            seoTierBadge.innerText = (report.tier || 'MODERATE').toUpperCase();
            if (score >= 90) {
                seoTierBadge.style.color = 'var(--success-color)';
                seoTierBadge.style.background = 'rgba(0, 255, 204, 0.15)';
            } else if (score >= 80) {
                seoTierBadge.style.color = 'var(--accent-color)';
                seoTierBadge.style.background = 'rgba(0, 210, 255, 0.15)';
            } else if (score >= 70) {
                seoTierBadge.style.color = '#ffd60a';
                seoTierBadge.style.background = 'rgba(255, 214, 10, 0.15)';
            } else {
                seoTierBadge.style.color = '#ff9500';
                seoTierBadge.style.background = 'rgba(255, 149, 0, 0.15)';
            }
        }

        if (seoTargetDisplay) seoTargetDisplay.innerText = `Target: ${report.target}`;
        if (seoStatusBadge) seoStatusBadge.innerText = `HTTP ${report.status_code || 200}`;
        if (seoSummaryTagline) seoSummaryTagline.innerText = report.summary || 'Technical and on-page audit completed.';

        // Telemetry stats
        const perf = report.performance_signals || {};
        if (seoStatLatency) seoStatLatency.innerText = perf.response_time_ms ? `${Math.round(perf.response_time_ms)} ms` : 'N/A';
        if (seoStatSize) seoStatSize.innerText = `${perf.document_size_kb || Math.round((perf.document_size_bytes || 0)/1024)} KB`;
        if (seoStatWords) seoStatWords.innerText = `${report.word_count || 0}`;
        if (seoStatResources) seoStatResources.innerText = `${perf.total_resources || 0}`;

        // 2. Category Cards Grid
        if (seoCategoriesGrid) {
            seoCategoriesGrid.innerHTML = '';
            const catEntries = Object.entries(report.category_scores || {});
            catEntries.forEach(([catName, cs]) => {
                const card = document.createElement('div');
                card.className = 'seo-category-card';
                const catScore = Math.round(cs.score || 0);
                let barColor = 'var(--accent-color)';
                if (catScore >= 90) barColor = 'var(--success-color)';
                else if (catScore < 70) barColor = '#ff9500';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.75rem; font-weight: bold; color: var(--text-primary);">${catName}</span>
                        <span style="font-size: 0.85rem; font-family: var(--font-mono); font-weight: bold; color: ${barColor};">${catScore}/100</span>
                    </div>
                    <div class="progress-bar" style="height: 5px;">
                        <div class="progress-fill" style="width: ${catScore}%; background: ${barColor};"></div>
                    </div>
                    <div style="display: flex; gap: 8px; font-size: 0.65rem; color: var(--text-muted); font-family: var(--font-mono);">
                        <span>Weight: ${Math.round(cs.weight * 100)}%</span>
                        <span>•</span>
                        <span style="color: var(--success-color);">✓ ${cs.passed_count || 0}</span>
                        <span style="color: #ffd60a;">⚠ ${cs.warning_count || 0}</span>
                        <span style="color: #ff3b30;">✗ ${cs.critical_count || 0}</span>
                    </div>
                `;
                seoCategoriesGrid.appendChild(card);
            });
        }

        // 3. Action Plan ("What to Fix First")
        if (seoActionPlanList) {
            seoActionPlanList.innerHTML = '';
            const actionItems = report.action_plan || [];
            if (seoActionItemsCount) seoActionItemsCount.innerText = `${actionItems.length} Actions`;

            if (actionItems.length === 0) {
                seoActionPlanList.innerHTML = `
                    <div style="font-size: 0.8rem; color: var(--success-color); padding: 8px 0;">
                        ✓ No critical issues detected! Core technical SEO standards are satisfied.
                    </div>
                `;
            } else {
                actionItems.forEach(item => {
                    const itemEl = document.createElement('div');
                    itemEl.className = 'seo-action-item-card';
                    itemEl.innerHTML = `
                        <div class="seo-rank-number">${item.rank}</div>
                        <div style="display: flex; flex-direction: column; gap: 4px; flex: 1;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong style="font-size: 0.8rem; color: var(--text-primary);">${item.title}</strong>
                                <div style="display: flex; gap: 6px;">
                                    <span style="font-size: 0.6rem; font-family: var(--font-mono); padding: 1px 6px; border-radius: 3px; background: rgba(255, 149, 0, 0.15); color: #ff9500;">Impact: ${item.impact}</span>
                                    <span style="font-size: 0.6rem; font-family: var(--font-mono); padding: 1px 6px; border-radius: 3px; background: rgba(0, 210, 255, 0.1); color: var(--accent-color);">Effort: ${item.effort}</span>
                                </div>
                            </div>
                            <p style="margin: 0; font-size: 0.75rem; color: #bde0fe; line-height: 1.35;">${item.action}</p>
                            ${item.why_it_matters ? `<span style="font-size: 0.68rem; color: var(--text-muted);">Why: ${item.why_it_matters}</span>` : ''}
                        </div>
                    `;
                    seoActionPlanList.appendChild(itemEl);
                });
            }
        }

        // 4. AI Strategic Insights
        if (seoAiInsightsBox && seoAiInsightsContent) {
            if (report.ai_recommendations) {
                seoAiInsightsBox.style.display = 'block';
                seoAiInsightsContent.innerText = report.ai_recommendations;
            } else {
                seoAiInsightsBox.style.display = 'none';
            }
        }

        // 5. Findings List
        renderFindingsFilter(report.findings || [], 'all');
    }

    function renderFindingsFilter(findings, filterType) {
        if (!seoFindingsList) return;
        currentFilterSeverity = filterType;

        // Calculate counts
        let critCount = 0;
        let warnCount = 0;
        let passCount = 0;

        findings.forEach(f => {
            const sev = (f.severity || '').toUpperCase();
            if (sev === 'CRITICAL' || sev === 'HIGH') critCount++;
            else if (sev === 'MEDIUM' || sev === 'LOW') warnCount++;
            else if (sev === 'PASSED') passCount++;
        });

        if (countFindingsAll) countFindingsAll.innerText = findings.length;
        if (countFindingsCrit) countFindingsCrit.innerText = critCount;
        if (countFindingsWarn) countFindingsWarn.innerText = warnCount;
        if (countFindingsPass) countFindingsPass.innerText = passCount;

        // Filter list
        const filtered = findings.filter(f => {
            const sev = (f.severity || '').toUpperCase();
            if (filterType === 'all') return true;
            if (filterType === 'critical') return sev === 'CRITICAL' || sev === 'HIGH';
            if (filterType === 'warning') return sev === 'MEDIUM' || sev === 'LOW';
            if (filterType === 'passed') return sev === 'PASSED';
            return true;
        });

        seoFindingsList.innerHTML = '';
        if (filtered.length === 0) {
            seoFindingsList.innerHTML = `<div style="font-size: 0.75rem; color: var(--text-muted); padding: 8px 0;">No findings in this category.</div>`;
            return;
        }

        filtered.forEach(f => {
            const sev = (f.severity || 'MEDIUM').toUpperCase();
            const sevClass = `severity-${sev.toLowerCase()}`;
            const card = document.createElement('div');
            card.className = `seo-finding-card ${sevClass}`;

            let sevBadgeColor = 'var(--accent-color)';
            if (sev === 'CRITICAL') sevBadgeColor = '#ff3b30';
            else if (sev === 'HIGH') sevBadgeColor = '#ff9500';
            else if (sev === 'MEDIUM') sevBadgeColor = '#ffd60a';
            else if (sev === 'PASSED') sevBadgeColor = 'var(--success-color)';

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 0.65rem; font-family: var(--font-mono); font-weight: bold; color: ${sevBadgeColor};">[${sev}]</span>
                        <strong style="font-size: 0.8rem; color: var(--text-primary);">${f.title}</strong>
                    </div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <span style="font-size: 0.65rem; color: var(--text-secondary); font-family: var(--font-mono);">${f.category}</span>
                        <span class="seo-evidence-badge">${f.evidence_type || 'OBSERVED'}</span>
                    </div>
                </div>
                ${f.problem ? `<p style="margin: 0; font-size: 0.75rem; color: #ffb4b4; line-height: 1.35;">${f.problem}</p>` : ''}
                <div style="font-size: 0.72rem; color: var(--text-secondary); font-family: var(--font-mono); background: rgba(0, 10, 20, 0.4); padding: 4px 8px; border-radius: 4px;">
                    Evidence: ${f.evidence || 'N/A'}
                </div>
                ${f.recommendation ? `<p style="margin: 0; font-size: 0.75rem; color: #bde0fe; line-height: 1.35;">&rarr; <strong>Fix</strong>: ${f.recommendation}</p>` : ''}
            `;
            seoFindingsList.appendChild(card);
        });
    }

    // Bind findings filter buttons
    if (seoFindingsFilters) {
        const filterBtns = seoFindingsFilters.querySelectorAll('.mem-filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filterType = btn.getAttribute('data-filter') || 'all';
                if (currentSeoReport) {
                    renderFindingsFilter(currentSeoReport.findings || [], filterType);
                }
            });
        });
    }

    if (seoAnalyzeBtn) {
        seoAnalyzeBtn.addEventListener('click', runSeoAudit);
    }

    // Reset button
    if (seoResetBtn) {
        seoResetBtn.addEventListener('click', () => {
            if (seoResultsContainer) seoResultsContainer.style.display = 'none';
            if (seoInputSection) seoInputSection.scrollIntoView({ behavior: 'smooth' });
            if (seoUrlInput && currentSeoMode === 'url') seoUrlInput.focus();
        });
    }

    // Copy Report in Markdown
    if (seoCopyBtn) {
        seoCopyBtn.addEventListener('click', async () => {
            if (!currentSeoReport) return;
            try {
                const res = await fetch(`${apiBase}/api/seo/export`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ report: currentSeoReport })
                });
                const data = await res.json();
                if (data.success && data.markdown) {
                    await navigator.clipboard.writeText(data.markdown);
                    const originalTxt = seoCopyBtn.innerText;
                    seoCopyBtn.innerText = '✓ REPORT COPIED!';
                    setTimeout(() => { seoCopyBtn.innerText = originalTxt; }, 2500);
                }
            } catch (err) {
                console.error('Error copying report:', err);
            }
        });
    }


    // =========================================================================
    // J.A.R.V.I.S. Defensive Security Assessment Engine Controller
    // =========================================================================
    let currentSecTab = 'overview';

    // Sub-nav tab switching
    const secSubnav = document.getElementById('sec-subnav');
    if (secSubnav) {
        secSubnav.querySelectorAll('.intel-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                secSubnav.querySelectorAll('.intel-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const tab = btn.getAttribute('data-sectab');
                switchSecurityTab(tab);
            });
        });
    }

    function switchSecurityTab(tab) {
        currentSecTab = tab;
        document.querySelectorAll('.sec-panel').forEach(p => p.style.display = 'none');
        const activePanel = document.getElementById(`sec-panel-${tab}`);
        if (activePanel) activePanel.style.display = 'flex';

        if (tab === 'overview') loadSecurityOverview();
        else if (tab === 'scans') loadSecurityScans();
        else if (tab === 'findings') loadSecurityFindings();
        else if (tab === 'assets') loadSecurityAssets();
        else if (tab === 'health') loadSecurityHealth();
    }

    // 1. Overview Loader
    async function loadSecurityOverview() {
        try {
            const res = await fetch(`${apiBase}/api/v1/security/overview`);
            const data = await res.json();
            if (!data.success || !data.overview) return;
            const ov = data.overview;

            const elAssets = document.getElementById('sec-stat-assets');
            if (elAssets) elAssets.innerText = ov.assets_total || 0;

            const elScans = document.getElementById('sec-stat-scans');
            if (elScans) elScans.innerText = `${ov.scans_running || 0} / ${ov.scans_total || 0}`;

            const bySev = (ov.findings && ov.findings.by_severity) || {};
            const elCrit = document.getElementById('sec-stat-critical');
            if (elCrit) elCrit.innerText = bySev.critical || 0;

            const elHigh = document.getElementById('sec-stat-high');
            if (elHigh) elHigh.innerText = bySev.high || 0;

            const elRem = document.getElementById('sec-stat-remediations');
            if (elRem) elRem.innerText = ov.remediations_open || 0;

            // Render severity breakdown
            const barsContainer = document.getElementById('sec-severity-bars');
            if (barsContainer) {
                const total = ov.findings.total || 1;
                const sevs = [
                    { key: 'critical', label: 'CRITICAL', color: '#ef4444' },
                    { key: 'high', label: 'HIGH', color: '#f97316' },
                    { key: 'medium', label: 'MEDIUM', color: '#eab308' },
                    { key: 'low', label: 'LOW', color: '#3b82f6' },
                    { key: 'informational', label: 'INFORMATIONAL', color: '#94a3b8' }
                ];
                barsContainer.innerHTML = sevs.map(s => {
                    const count = bySev[s.key] || 0;
                    const pct = Math.round((count / (ov.findings.total || 1)) * 100);
                    return `
                        <div style="font-size: 0.72rem; font-family: var(--font-mono);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                                <span style="color: ${s.color}; font-weight: bold;">${s.label}</span>
                                <span style="color: var(--text-secondary);">${count} (${pct}%)</span>
                            </div>
                            <div style="height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;">
                                <div style="width: ${pct}%; height: 100%; background: ${s.color};"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Load scanners overview list
            const scRes = await fetch(`${apiBase}/api/v1/security/scanners`);
            const scData = await scRes.json();
            const scList = document.getElementById('sec-scanners-overview-list');
            if (scList && scData.success && scData.scanners) {
                scList.innerHTML = scData.scanners.map(sc => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(0,20,30,0.3); border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.75rem;">
                        <span style="font-family: var(--font-mono); color: #00d2ff; text-transform: uppercase;">${sc.name}</span>
                        <span style="font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; background: ${sc.available ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${sc.available ? '#10b981' : '#ef4444'};">
                            ${sc.available ? 'ONLINE / READY' : 'UNAVAILABLE / WORKER'}
                        </span>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading security overview:', e);
        }
    }

    // Auto-detect profile from target input format
    const secTargetInput = document.getElementById('sec-input-target');
    const secProfileSelect = document.getElementById('sec-select-profile');
    if (secTargetInput && secProfileSelect) {
        secTargetInput.addEventListener('input', () => {
            const val = secTargetInput.value.trim().toLowerCase();
            if (val.includes('github.com') || val.endsWith('.txt') || val.endsWith('.json') || val.endsWith('.lock')) {
                secProfileSelect.value = 'dependency_audit';
            } else if (val.startsWith('http://') || val.startsWith('https://')) {
                secProfileSelect.value = 'web_baseline';
            }
        });
    }

    // 2. Submit New Scan
    const btnSubmitScan = document.getElementById('sec-btn-submit-scan');
    if (btnSubmitScan) {
        btnSubmitScan.addEventListener('click', async () => {
            const target = (document.getElementById('sec-input-target')?.value || '').trim();
            const profile = document.getElementById('sec-select-profile')?.value || 'dependency_audit';
            const owner = (document.getElementById('sec-input-owner')?.value || 'SecOps Administrator').trim();
            const isAuthAck = document.getElementById('sec-check-auth')?.checked;

            if (!target) {
                alert('Please enter a target host, IP, domain, or lockfile path.');
                return;
            }
            if (!isAuthAck) {
                alert('Authorization acknowledgement checkbox must be checked. Scanning unauthorized systems is strictly prohibited.');
                return;
            }

            btnSubmitScan.disabled = true;
            btnSubmitScan.innerText = 'INITIALIZING SCAN...';

            try {
                const res = await fetch(`${apiBase}/api/v1/security/scans`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target: target,
                        profile: profile,
                        owner: owner,
                        authorization_acknowledged: true,
                        initiated_by: 'jarvis_dashboard'
                    })
                });
                const data = await res.json();
                if (data.success && data.job) {
                    playCompletionChirp();
                    alert(`Scan initiated successfully. Job ID: ${data.job.id}`);
                    // Switch to scan jobs tab
                    const btnScans = document.querySelector('[data-sectab="scans"]');
                    if (btnScans) btnScans.click();
                } else {
                    playErrorBeep();
                    alert(`Scan submission rejected: ${data.error || 'Unknown error'}`);
                }
            } catch (err) {
                playErrorBeep();
                alert(`Error submitting scan: ${err.message}`);
            } finally {
                btnSubmitScan.disabled = false;
                btnSubmitScan.innerText = 'INITIATE ASSESSMENT';
            }
        });
    }

    // 3. Scan Jobs Loader
    const btnRefreshScans = document.getElementById('sec-btn-refresh-scans');
    if (btnRefreshScans) btnRefreshScans.addEventListener('click', loadSecurityScans);

    async function loadSecurityScans() {
        const tbody = document.getElementById('sec-scans-tbody');
        if (!tbody) return;
        try {
            const res = await fetch(`${apiBase}/api/v1/security/scans?limit=50`);
            const data = await res.json();
            if (!data.success || !data.scans || data.scans.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="padding: 16px; text-align: center; color: var(--text-secondary);">No scans executed yet.</td></tr>';
                return;
            }

            tbody.innerHTML = data.scans.map(j => {
                const statusColor = {
                    completed: '#10b981', running: '#38bdf8', pending: '#fbbf24',
                    failed: '#ef4444', cancelled: '#94a3b8'
                }[j.status] || '#94a3b8';

                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 8px; font-family: var(--font-mono); color: #e2e8f0;">${j.target}</td>
                        <td style="padding: 8px; color: var(--text-secondary);">${j.profile}</td>
                        <td style="padding: 8px;"><span style="color: ${statusColor}; font-weight: bold; text-transform: uppercase;">${j.status}</span></td>
                        <td style="padding: 8px;">
                            <div style="font-size: 0.68rem; color: var(--text-secondary); margin-bottom: 2px;">${j.progress_pct}% - ${j.progress_msg || ''}</div>
                            <div style="width: 100px; height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden;">
                                <div style="width: ${j.progress_pct}%; height: 100%; background: ${statusColor};"></div>
                            </div>
                        </td>
                        <td style="padding: 8px; font-weight: bold; color: #00d2ff;">${(j.result_ids && j.result_ids.length) || 0}</td>
                        <td style="padding: 8px;">
                            <a href="${apiBase}/api/v1/security/reports/${j.id}/html" target="_blank" style="color: #38bdf8; text-decoration: none; margin-right: 6px; font-size: 0.7rem;">[HTML]</a>
                            <a href="${apiBase}/api/v1/security/reports/${j.id}/csv" target="_blank" style="color: #38bdf8; text-decoration: none; font-size: 0.7rem;">[CSV]</a>
                        </td>
                        <td style="padding: 8px;">
                            ${j.status === 'running' || j.status === 'pending' ? `
                                <button onclick="window.cancelSecurityScan('${j.id}')" style="background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; padding: 2px 8px; border-radius: 4px; cursor: pointer; font-size: 0.68rem;">CANCEL</button>
                            ` : `<span style="color: var(--text-secondary); font-size: 0.68rem;">${j.duration_s ? j.duration_s + 's' : '–'}</span>`}
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            console.error('Error loading scans:', e);
        }
    }

    window.cancelSecurityScan = async function(jobId) {
        if (!confirm('Are you sure you want to cancel this scan?')) return;
        try {
            await fetch(`${apiBase}/api/v1/security/scans/${jobId}/cancel`, { method: 'POST' });
            loadSecurityScans();
        } catch (e) {
            alert('Failed to cancel scan.');
        }
    };

    // 4. Findings & Remediation Loader
    const btnRefreshFindings = document.getElementById('sec-btn-refresh-findings');
    if (btnRefreshFindings) btnRefreshFindings.addEventListener('click', loadSecurityFindings);

    const filterSevSelect = document.getElementById('sec-findings-filter-sev');
    if (filterSevSelect) filterSevSelect.addEventListener('change', loadSecurityFindings);

    async function loadSecurityFindings() {
        const container = document.getElementById('sec-findings-container');
        if (!container) return;
        const sevFilter = filterSevSelect?.value || '';
        const url = `${apiBase}/api/v1/security/findings?limit=100${sevFilter ? '&severity=' + sevFilter : ''}`;
        try {
            const res = await fetch(url);
            const data = await res.json();
            if (!data.success || !data.findings || data.findings.length === 0) {
                container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 0.75rem;">No security findings match the current criteria.</div>';
                return;
            }

            container.innerHTML = data.findings.map(f => {
                const sevColor = {
                    critical: '#ef4444', high: '#f97316', medium: '#eab308',
                    low: '#3b82f6', informational: '#94a3b8'
                }[f.severity] || '#94a3b8';

                return `
                    <div style="background: rgba(0,20,30,0.4); border: 1px solid var(--border-color); border-left: 4px solid ${sevColor}; border-radius: 8px; padding: 12px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.68rem; font-weight: bold; background: ${sevColor}22; color: ${sevColor}; margin-right: 6px;">${f.severity.toUpperCase()}</span>
                                <span style="font-size: 0.82rem; font-weight: bold; color: var(--text-primary); font-family: var(--font-mono);">${f.title}</span>
                            </div>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                <button onclick="window.requestAIAnalysis('${f.id}')" style="background: rgba(0,210,255,0.1); border: 1px solid #00d2ff; color: #00d2ff; padding: 3px 8px; border-radius: 4px; font-size: 0.68rem; cursor: pointer; font-family: var(--font-mono);">⚡ AI EXPLANATION</button>
                                <button onclick="window.toggleFalsePositive('${f.id}', ${!f.false_positive})" style="background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); padding: 3px 8px; border-radius: 4px; font-size: 0.68rem; cursor: pointer;">
                                    ${f.false_positive ? '✓ FALSE POSITIVE' : 'MARK FALSE POSITIVE'}
                                </button>
                            </div>
                        </div>

                        <div style="font-size: 0.74rem; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.4;">
                            ${f.description}
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; font-size: 0.7rem; font-family: var(--font-mono); background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px;">
                            <div><span style="color: var(--text-secondary);">COMPONENT:</span> <span style="color: #38bdf8;">${f.affected_component || 'N/A'}</span></div>
                            <div><span style="color: var(--text-secondary);">SCANNER:</span> <span style="color: #e2e8f0;">${f.scanner} (${f.confidence} conf)</span></div>
                            <div><span style="color: var(--text-secondary);">VULN ID:</span> <span style="color: #fbbf24;">${f.vuln_id || 'N/A'}</span></div>
                            <div><span style="color: var(--text-secondary);">STATUS:</span> <span style="color: #10b981;">${f.verification}</span></div>
                        </div>

                        ${f.remediation ? `
                            <div style="margin-top: 8px; font-size: 0.72rem; color: #a7f3d0; background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15); border-radius: 6px; padding: 8px;">
                                <strong>REMEDIATION GUIDANCE:</strong> ${f.remediation}
                            </div>
                        ` : ''}

                        <div id="ai-analysis-box-${f.id}" style="display: none; margin-top: 10px; background: rgba(0,210,255,0.05); border: 1px solid rgba(0,210,255,0.2); border-radius: 6px; padding: 12px; font-size: 0.72rem;"></div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Error loading findings:', e);
        }
    }

    window.toggleFalsePositive = async function(findingId, isFp) {
        try {
            await fetch(`${apiBase}/api/v1/security/findings/${findingId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    false_positive: isFp,
                    fp_justification: isFp ? 'Flagged via security dashboard by analyst' : ''
                })
            });
            loadSecurityFindings();
        } catch (e) {
            alert('Failed to update finding status.');
        }
    };

    window.requestAIAnalysis = async function(findingId) {
        const box = document.getElementById(`ai-analysis-box-${findingId}`);
        if (!box) return;
        box.style.display = 'block';
        box.innerHTML = '<span style="color: #00d2ff;">Consulting J.A.R.V.I.S. AI Security Analyst...</span>';

        try {
            const res = await fetch(`${apiBase}/api/v1/security/findings/${findingId}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ asset_criticality: 'medium' })
            });
            const data = await res.json();
            if (data.success && data.ai_analysis) {
                const a = data.ai_analysis;
                box.innerHTML = `
                    <div style="color: #00d2ff; font-weight: bold; margin-bottom: 6px; font-family: var(--font-mono);">🛡️ J.A.R.V.I.S. GROUNDED INTELLIGENCE BRIEF</div>
                    <div style="margin-bottom: 6px;"><strong>EXECUTIVE SUMMARY:</strong> ${a.executive_summary || 'N/A'}</div>
                    <div style="margin-bottom: 6px;"><strong>TECHNICAL BREAKDOWN:</strong> ${a.technical_analysis || 'N/A'}</div>
                    <div style="margin-bottom: 6px; color: #fbbf24;"><strong>UNCERTAINTY &amp; FP ASSESSMENT:</strong> ${a.uncertainty_and_fp_risk || 'N/A'}</div>
                    <div style="color: #86efac;"><strong>ACTION PLAN:</strong> ${a.prioritized_action || 'N/A'}</div>
                `;
            } else {
                box.innerHTML = '<span style="color: #ef4444;">Could not generate AI analysis.</span>';
            }
        } catch (e) {
            box.innerHTML = `<span style="color: #ef4444;">Error: ${e.message}</span>`;
        }
    };

    // 5. Asset Inventory Loader
    async function loadSecurityAssets() {
        const tbody = document.getElementById('sec-assets-tbody');
        if (!tbody) return;
        try {
            const res = await fetch(`${apiBase}/api/v1/security/assets?limit=100`);
            const data = await res.json();
            if (!data.success || !data.assets || data.assets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding: 16px; text-align: center; color: var(--text-secondary);">No assets discovered yet.</td></tr>';
                return;
            }

            tbody.innerHTML = data.assets.map(a => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 8px; font-weight: bold; color: var(--text-primary); font-family: var(--font-mono);">${a.display_name}</td>
                    <td style="padding: 8px; color: var(--text-secondary);">${a.asset_type}</td>
                    <td style="padding: 8px; font-family: var(--font-mono); color: #38bdf8;">${a.ip_address || '–'}</td>
                    <td style="padding: 8px; font-family: var(--font-mono); color: #e2e8f0;">${a.hostname || '–'}</td>
                    <td style="padding: 8px; color: var(--text-secondary);">${a.discovery_source}</td>
                    <td style="padding: 8px;"><span style="color: #fbbf24; text-transform: uppercase; font-size: 0.68rem; font-weight: bold;">${a.criticality}</span></td>
                </tr>
            `).join('');
        } catch (e) {
            console.error('Error loading assets:', e);
        }
    }

    // 6. Scanner Health Loader
    async function loadSecurityHealth() {
        const grid = document.getElementById('sec-health-grid');
        if (!grid) return;
        try {
            const res = await fetch(`${apiBase}/api/v1/security/scanners`);
            const data = await res.json();
            if (!data.success || !data.scanners) return;

            grid.innerHTML = data.scanners.map(s => {
                const isOnline = s.available;
                return `
                    <div style="background: rgba(0,20,30,0.4); border: 1px solid ${isOnline ? 'rgba(16,185,129,0.3)' : 'var(--border-color)'}; border-radius: 10px; padding: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 0.85rem; font-weight: bold; color: #00d2ff; font-family: var(--font-mono); text-transform: uppercase;">${s.name}</span>
                            <span style="font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; background: ${isOnline ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${isOnline ? '#10b981' : '#ef4444'};">
                                ${isOnline ? 'ONLINE' : 'OFFLINE'}
                            </span>
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 6px;">
                            <strong>LOCATION:</strong> ${s.execution_location}
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 6px;">
                            <strong>PROFILES:</strong> ${(s.supported_profiles || []).join(', ') || 'None'}
                        </div>
                        <div style="font-size: 0.7rem; color: var(--text-primary); line-height: 1.3; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
                            ${s.resource_note || s.last_error || 'Operating normally.'}
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Error loading health:', e);
        }
    }

    // Initialization
    pollStatus();
    setInterval(pollStatus, 2000);
    
    // Load default weather and news
    const defaultCity = localStorage.getItem('last_weather_city') || 'Rajkot';
    fetchWeather(defaultCity, false);
    fetchNews();
});

