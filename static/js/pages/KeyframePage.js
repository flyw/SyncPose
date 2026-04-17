import api from '../services/api.js';

export default class KeyframePage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.video = await api.getVideo(this.videoId);

        return `
            <div class="pro-layout">
                <div class="preview-area">
                    <div class="video-wrapper" id="preview-container">
                        <video id="video-player" src="${this.video.url}" playsinline></video>
                        <canvas id="landmark-overlay"></canvas>
                    </div>
                    <div class="timeline-container">
                        <div class="timeline-track" id="timeline-track">
                            <div class="timeline-progress" id="timeline-progress"></div>
                            <div id="markers-layer"></div>
                        </div>
                    </div>
                </div>

                <div class="pro-sidebar">
                    <div class="sidebar-header">
                        <h3>Selection & Alignment</h3>
                    </div>

                    <div class="panel-section scrollable">
                        <div class="control-group">
                            <h3>🏆 AI Recommended Frames</h3>
                            <p class="small text-muted">Top 20 most stable poses found automatically.</p>
                            <div id="candidates-list" class="frame-list">
                                <div style="text-align:center; color:#444; padding:20px;">Calculating...</div>
                            </div>
                        </div>
                    </div>

                    <!-- Bottom Action Panel -->
                    <div class="sidebar-footer-actions">
                        <div class="legend-box">
                            <div class="legend-item">
                                <span class="dot white"></span> 
                                <span>Reference Base (Ideal)</span>
                            </div>
                            <div class="legend-item">
                                <span class="dot yellow"></span> 
                                <span>Current Video Frame</span>
                            </div>
                        </div>

                        <div class="control-group no-bg">
                            <div class="toggle-row">
                                <button class="toggle-btn active" id="toggle-keypoints" style="width: 100%;">
                                    🔘 33-Point Skeleton Overlay
                                </button>
                            </div>
                            <button class="btn-success" id="add-keyframe-btn" style="width: 100%; padding: 12px; font-size: 14px;">
                                📸 Save Current as Keyframe
                            </button>
                            <div id="save-status" style="margin-top:10px; font-size:11px; text-align:center;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async afterRender() {
        const video = document.getElementById('video-player');
        const canvas = document.getElementById('landmark-overlay');
        const ctx = canvas.getContext('2d');
        const timelineTrack = document.getElementById('timeline-track');
        const timelineProgress = document.getElementById('timeline-progress');
        const markersLayer = document.getElementById('markers-layer');
        const statusBox = document.getElementById('save-status');
        
        this.fps = this.video.fps || 30;
        this.totalFrames = this.video.total_frames;
        this.similarFrames = [];
        this.averagePose = null;
        this.currentFrameLandmarks = null;
        this.showKeypoints = true;
        this.running = true;
        this.keyframes = await api.getKeyframes(this.videoId) || [];

        // Initialize MediaPipe Pose for real-time frontend calibration
        this.initPose = async () => {
            if (typeof Pose === 'undefined') {
                await new Promise(resolve => {
                    const check = setInterval(() => {
                        if (typeof Pose !== 'undefined') {
                            clearInterval(check);
                            resolve();
                        }
                    }, 100);
                });
            }

            this.pose = new Pose({
                locateFile: (file) => {
                    return `/static/libs/${file}`;
                }
            });

            this.pose.setOptions({
                modelComplexity: 1,
                smoothLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            this.pose.onResults((results) => {
                if (results.poseLandmarks) {
                    this.currentFrameLandmarks = results.poseLandmarks.map(lm => [lm.x, lm.y, lm.z, lm.visibility]);
                }
            });
        };

        this.initPose();

        const CONNECTIONS = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28]];

        video.onloadedmetadata = () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        };

        const loadAnalysis = async () => {
            const data = await api.getAnalysis(this.videoId, 92.0);
            this.averagePose = data.average_pose;
            this.similarFrames = data.similar_frames;
            this.renderCandidates(data.candidates);
            this.renderMarkers();
            this.syncSelectedCards();

            // Initial highlighting sync
            const currentIdx = Math.round(video.currentTime * this.fps);
            document.querySelectorAll('.frame-card').forEach(card => {
                card.classList.toggle('active', parseInt(card.dataset.idx) === currentIdx);
            });
        };

        this.syncSelectedCards = () => {
            const selectedIndices = this.keyframes.map(k => k.frame);
            document.querySelectorAll('.frame-card').forEach(card => {
                const idx = parseInt(card.dataset.idx);
                card.classList.toggle('selected', selectedIndices.includes(idx));
            });
        };

        this.renderCandidates = (list) => {
            const selectedIndices = this.keyframes.map(k => k.frame);
            document.getElementById('candidates-list').innerHTML = list.map(c => `
                <div class="frame-card ${selectedIndices.includes(c.idx) ? 'selected' : ''}" data-idx="${c.idx}" onclick="window.seekToFrame(${c.idx})">
                    <img src="/api/v1/resources/${this.videoId}/frame_image/${c.idx}" loading="lazy">
                    <div class="frame-info">
                        <div style="font-weight:bold; color:var(--primary)">Frame ${c.idx}</div>
                        <div class="candidate-meta">
                            <span>Time: ${c.timestamp.toFixed(2)}s</span>
                            <span style="color:var(--success)">${c.score.toFixed(1)}% Match</span>
                        </div>
                    </div>
                </div>
            `).join('');
        };

        this.renderMarkers = () => {
            if (!this.totalFrames) return;
            markersLayer.innerHTML = '';
            this.similarFrames.forEach(f => {
                const m = document.createElement('div');
                m.className = 'marker';
                const pos = (f.frame_index / this.totalFrames) * 100;
                if (isFinite(pos)) {
                    m.style.left = pos + '%';
                    markersLayer.appendChild(m);
                }
            });
        };

        this.drawPose = (lms, color, radius, opacity = 1.0) => {
            if (!lms) return;
            ctx.globalAlpha = opacity;
            ctx.strokeStyle = color; 
            ctx.fillStyle = color; 
            
            // Scalable line width based on internal canvas resolution
            ctx.lineWidth = Math.max(2, canvas.width / 300); 
            
            const w = canvas.width;
            const h = canvas.height;

            CONNECTIONS.forEach(([i, j]) => {
                const p1 = lms[i], p2 = lms[j];
                if (p1[3] > 0.5 && p2[3] > 0.5) {
                    ctx.beginPath(); 
                    ctx.moveTo(p1[0] * w, p1[1] * h);
                    ctx.lineTo(p2[0] * w, p2[1] * h); 
                    ctx.stroke();
                }
            });
            lms.forEach(p => { 
                if (p[3] > 0.5) { 
                    ctx.beginPath(); 
                    ctx.arc(p[0] * w, p[1] * h, radius * (w / 1000), 0, Math.PI*2); 
                    ctx.fill(); 
                } 
            });
            ctx.globalAlpha = 1.0;
        };

        const renderLoop = () => {
            if (!this.running) return;
            
            // 1. Ensure internal resolution matches video intrinsic resolution
            if (video.videoWidth && (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight)) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
            }

            // 2. Use getBoundingClientRect for sub-pixel precision alignment
            const vRect = video.getBoundingClientRect();
            const containerRect = video.parentElement.getBoundingClientRect();
            
            // Synchronize CSS dimensions and position
            canvas.style.width = vRect.width + 'px';
            canvas.style.height = vRect.height + 'px';
            canvas.style.left = (vRect.left - containerRect.left) + 'px';
            canvas.style.top = (vRect.top - containerRect.top) + 'px';
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (this.showKeypoints) {
                if (this.averagePose) this.drawPose(this.averagePose, '#ffffff', 5, 0.35);
                if (this.currentFrameLandmarks) this.drawPose(this.currentFrameLandmarks, '#fbbf24', 8);
            }

            if (video.duration) timelineProgress.style.width = (video.currentTime / video.duration) * 100 + '%';

            // Dynamic Button Label
            const addBtn = document.getElementById('add-keyframe-btn');
            if (addBtn) {
                const currentFrame = Math.round(video.currentTime * this.fps);
                const exists = this.keyframes.some(k => k.frame === currentFrame);
                addBtn.innerText = exists ? '🗑️ Remove Keyframe' : '📸 Save Current as Keyframe';
                addBtn.className = exists ? 'btn-danger' : 'btn-success';
            }

            requestAnimationFrame(renderLoop);
        };

        const runFrontendPose = async () => {
            if (video.videoWidth > 0 && this.showKeypoints && this.pose) {
                await this.pose.send({image: video});
            }
        };

        window.seekToFrame = (idx) => { 
            const time = idx / this.fps;
            if (isFinite(time) && isFinite(video.duration)) {
                video.currentTime = time; 
            }
            
            // Update UI highlighting
            document.querySelectorAll('.frame-card').forEach(card => {
                card.classList.toggle('active', parseInt(card.dataset.idx) === idx);
            });

            // Trigger frontend detection after seek
            setTimeout(runFrontendPose, 50);
        };
        
        document.getElementById('toggle-keypoints').onclick = (e) => {
            this.showKeypoints = !this.showKeypoints;
            e.target.classList.toggle('active', this.showKeypoints);
            if (this.showKeypoints) runFrontendPose();
        };

        timelineTrack.onclick = (e) => {
            if (!video.duration || !isFinite(video.duration)) return;
            const rect = timelineTrack.getBoundingClientRect();
            if (rect.width === 0) return;
            const pos = (e.clientX - rect.left) / rect.width;
            const targetTime = pos * video.duration;
            if (isFinite(targetTime)) {
                video.currentTime = targetTime;
                setTimeout(runFrontendPose, 50);
            }
        };

        video.onseeked = async () => {
            const idx = Math.round(video.currentTime * this.fps);
            // We still fetch data for backend sync, but frontend detection will provide the display
            const data = await fetch(`/api/v1/resources/${this.videoId}/frame_data/${idx}`).then(r => r.json());
            
            await runFrontendPose();

            // Sync card highlighting
            document.querySelectorAll('.frame-card').forEach(card => {
                card.classList.toggle('active', parseInt(card.dataset.idx) === idx);
            });
        };

        document.getElementById('add-keyframe-btn').onclick = async () => {
            const frame = Math.round(video.currentTime * this.fps);
            const isAlreadySelected = this.keyframes.some(k => k.frame === frame);
            
            if (isAlreadySelected) {
                // Toggle off: if clicking the same frame, remove it
                this.keyframes = [];
                statusBox.innerHTML = '<span style="color:var(--warning)">Removing...</span>';
            } else {
                // Replace: Set this as the ONLY keyframe
                statusBox.innerHTML = '<span style="color:var(--warning)">Saving...</span>';
                try {
                    const imgRes = await api.saveKeyframeImage(this.videoId, frame);
                    this.keyframes = [{ frame, timestamp: video.currentTime, image_url: imgRes.url }];
                } catch (e) {
                    statusBox.innerHTML = '<span style="color:var(--danger)">❌ Save failed</span>';
                    return;
                }
            }

            try {
                await api.saveKeyframes(this.videoId, this.keyframes);
                statusBox.innerHTML = `<span style="color:var(--success)">✅ ${isAlreadySelected ? 'Removed' : 'Updated'} successfully</span>`;
                this.syncSelectedCards();
                setTimeout(() => statusBox.innerHTML = '', 3000);
            } catch (e) {
                statusBox.innerHTML = '<span style="color:var(--danger)">❌ Action failed</span>';
            }
        };

        loadAnalysis();
        requestAnimationFrame(renderLoop);
    }

    dispose() { this.running = false; }
}
