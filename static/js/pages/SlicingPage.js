import api from '../services/api.js';

export default class SlicingPage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.video = await api.getVideo(this.videoId);

        return `
            <div class="pro-layout" style="flex-direction: column;">
                <div style="display: flex; flex: 1; overflow: hidden;">
                    <div class="preview-area">
                        <div class="video-wrapper" id="preview-container">
                            <video id="video-player" src="${this.video.url}" playsinline></video>
                            <canvas id="landmark-overlay"></canvas>
                        </div>
                    </div>

                    <div class="pro-sidebar">
                        <div class="sidebar-header">
                            <h3>Action Slicing</h3>
                        </div>
                        
                        <div class="slice-list-container">
                            <button class="btn-primary" id="new-slice-btn" style="width:100%; margin-bottom: 1.5rem;">➕ Create New Slice</button>
                            <div class="editor-title">Project Segments</div>
                            <div id="slice-list"></div>
                        </div>

                        <div class="sidebar-footer-editor">
                            <div id="editor-panel" class="hidden">
                                <div class="adj-group">
                                    <div class="adj-header"><label>Segment Name</label></div>
                                    <input type="text" id="active-slice-name" placeholder="Enter segment name..." style="width: 100%;">
                                </div>

                                <div class="adj-group">
                                   <div class="adj-header"><label>Start Point</label> <span id="start-time-val" class="small text-muted"></span></div>
                                   <div class="adj-controls">
                                       <button class="btn-nav-small" id="set-start-current" title="Set to current frame" style="background: var(--primary); margin-right: 4px;">📌</button>
                                       <button class="btn-nav-small" id="start-prev" title="Previous Frame">❮</button>
                                       <input type="number" class="val-display" id="start-frame-input" value="0" style="border:none; width: 60px;">
                                       <button class="btn-nav-small" id="start-next" title="Next Frame">❯</button>
                                       <button class="btn-nav-small" id="start-seek" title="Jump to start" style="margin-left: 4px;">🎯</button>
                                   </div>
                                </div>

                                <div class="adj-group">
                                   <div class="adj-header"><label>End Point</label> <span id="end-time-val" class="small text-muted"></span></div>
                                   <div class="adj-controls">
                                       <button class="btn-nav-small" id="set-end-current" title="Set to current frame" style="background: var(--primary); margin-right: 4px;">📌</button>
                                       <button class="btn-nav-small" id="end-prev" title="Previous Frame">❮</button>
                                       <input type="number" class="val-display" id="end-frame-input" value="0" style="border:none; width: 60px;">
                                       <button class="btn-nav-small" id="end-next" title="Next Frame">❯</button>
                                       <button class="btn-nav-small" id="end-seek" title="Jump to end" style="margin-left: 4px;">🎯</button>
                                   </div>
                                </div>
                                <div class="control-group no-bg">
                                    <div class="current-status-bar">
                                        <div class="status-item"><span>Frame:</span> <strong id="current-frame-display">0</strong></div>
                                        <div class="status-item"><span>Time:</span> <strong id="current-time-display">0.000s</strong></div>
                                    </div>
                                    
                                    <div class="compact-controls-row">
                                        <button class="btn-play" id="play-btn" style="flex: 1;">▶ Play</button>
                                        <button class="btn-toggle" id="loop-toggle" style="flex: 1;">🔄 Loop Off</button>
                                        <button class="btn-toggle active" id="skeleton-toggle" style="flex: 1;">🔘 Skeleton On</button>
                                    </div>

                                    <div class="legend-mini">
                                        <div class="legend-item"><span class="dot yellow"></span> Reference (Keyframe)</div>
                                        <div class="legend-item"><span class="dot green"></span> Current Frame</div>
                                    </div>

                                    <button class="btn-success" id="save-active-btn" style="width: 100%; padding: 12px; margin-top:10px;">💾 Save Current Slice</button>
                                    <button class="btn-primary" id="export-active-btn" style="width: 100%; padding: 12px; margin-top:10px; background: #6366f1;">✂️ Export Slice Video</button>
                                </div>
                            </div>
                            <div id="no-selection-msg" class="text-muted small" style="text-align:center;">Select a slice to edit or create a new one.</div>
                        </div>
                    </div>
                </div>

                <!-- Global Slicing Timeline -->
                <div class="slicing-timeline">
                    <div class="timeline-ruler" id="timeline-ruler"></div>
                    <div class="slice-track-container" id="slice-track">
                        <div id="playhead" class="playhead"></div>
                        <div id="marker-start" class="slice-marker marker-start hidden"><div class="marker-label">START</div></div>
                        <div id="marker-end" class="slice-marker marker-end hidden"><div class="marker-label">END</div></div>
                    </div>
                </div>
            </div>
        `;
    }

    async afterRender() {
        const video = document.getElementById('video-player');
        const canvas = document.getElementById('landmark-overlay');
        const ctx = canvas.getContext('2d');
        const ruler = document.getElementById('timeline-ruler');
        const track = document.getElementById('slice-track');
        const playhead = document.getElementById('playhead');
        const markerStart = document.getElementById('marker-start');
        const markerEnd = document.getElementById('marker-end');
        const playBtn = document.getElementById('play-btn');
        const loopToggle = document.getElementById('loop-toggle');
        const skeletonToggle = document.getElementById('skeleton-toggle');
        
        const CONNECTIONS = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28]];

        this.fps = this.video.fps || 30;
        this.totalFrames = this.video.total_frames || 0;
        this.slices = await api.getSlices(this.videoId) || [];
        this.keyframes = await api.getKeyframes(this.videoId) || [];
        
        // Initialize MediaPipe Pose for real-time frontend calibration
        this.initPose = async () => {
            if (typeof Pose === 'undefined') {
                console.log("Waiting for MediaPipe Pose to load...");
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

        this.keyframeLandmarks = null;
        this.currentFrameLandmarks = null;
        this.activeIndex = -1;
        this.isLooping = false;
        this.showSkeleton = true;
        this.running = true;

        // Load Keyframe reference if available
        if (this.keyframes.length > 0) {
            const k = this.keyframes[0];
            const data = await fetch(`/api/v1/resources/${this.videoId}/frame_data/${k.frame}`).then(r => r.json());
            if (data.landmarks) this.keyframeLandmarks = data.landmarks;
        }

        video.onloadedmetadata = () => {
            if (!this.totalFrames && video.duration) {
                this.totalFrames = Math.floor(video.duration * this.fps);
            }
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            renderRuler();
            syncUI();
        };

        const renderRuler = () => {
            if (!video.duration && !this.totalFrames) return;
            ruler.innerHTML = '';
            const duration = video.duration || (this.totalFrames / this.fps);
            const step = Math.max(1, Math.floor(duration / 10));
            for (let i = 0; i <= duration; i += step) {
                const mark = document.createElement('div');
                mark.className = 'time-mark';
                mark.style.left = (i / duration * 100) + '%';
                mark.textContent = i.toFixed(0) + 's';
                ruler.appendChild(mark);
            }
        };

        const syncUI = () => {
            // Sort slices chronologically by start frame
            const activeSlice = this.activeIndex >= 0 ? this.slices[this.activeIndex] : null;
            this.slices.sort((a, b) => a.start_frame - b.start_frame);
            if (activeSlice) {
                this.activeIndex = this.slices.indexOf(activeSlice);
            }

            const list = document.getElementById('slice-list');
            list.innerHTML = this.slices.map((s, i) => `
                <div class="slice-list-item ${this.activeIndex === i ? 'active' : ''}"
                      style="position: relative;"
                      onclick="window.selectSlice(${i})">
                    <div class="slice-main">
                        <div class="name">${s.name || 'Unnamed Segment'}</div>
                        <div class="range">${s.start_frame} - ${s.end_frame} (${((s.end_frame - s.start_frame)/this.fps).toFixed(2)}s)</div>
                    </div>
                    <button class="btn-delete-mini"
                            style="position: absolute; bottom: 8px; right: 8px; background: #ef4444; color: white; width: 18px; height: 18px; min-width: 18px; padding: 0; font-size: 10px; border: none; border-radius: 4px; display: flex; align-items: center; justify-content: center; cursor: pointer; opacity: 0.8;"
                            onclick="window.deleteSlice(event, ${i})">✕</button>
                </div>
            `).join('');
            const editor = document.getElementById('editor-panel');
            const msg = document.getElementById('no-selection-msg');
            
            if (this.activeIndex >= 0) {
                editor.classList.remove('hidden');
                msg.classList.add('hidden');
                const s = this.slices[this.activeIndex];
                const total = this.totalFrames || 1; 
                document.getElementById('start-frame-input').value = s.start_frame;
                document.getElementById('end-frame-input').value = s.end_frame;
                document.getElementById('start-time-val').textContent = (s.start_frame / this.fps).toFixed(3) + 's';
                document.getElementById('end-time-val').textContent = (s.end_frame / this.fps).toFixed(3) + 's';
                document.getElementById('active-slice-name').value = s.name;
                
                markerStart.classList.remove('hidden');
                markerEnd.classList.remove('hidden');
                markerStart.style.left = (s.start_frame / total * 100) + '%';
                markerEnd.style.left = (s.end_frame / total * 100) + '%';
            } else {
                editor.classList.add('hidden');
                msg.classList.remove('hidden');
                markerStart.classList.add('hidden');
                markerEnd.classList.add('hidden');
            }
        };

        this.seekToFrame = (frame) => {
            const time = (frame + 0.01) / this.fps;
            if (isFinite(time) && isFinite(video.duration)) {
                // Remove existing one-time listener to avoid accumulation
                if (this._seekHandler) video.removeEventListener('seeked', this._seekHandler);
                
                this._seekHandler = () => {
                    if (this.showSkeleton && this.pose) {
                        this.pose.send({image: video});
                    }
                };
                
                video.addEventListener('seeked', this._seekHandler, { once: true });
                video.currentTime = time;
            }
        };

        window.selectSlice = (index) => {
            this.activeIndex = index;
            const s = this.slices[index];
            if (s) {
                this.seekToFrame(s.start_frame);
            }
            syncUI();
        };

        window.deleteSlice = async (event, index) => {
            event.stopPropagation();
            if (confirm('Are you sure you want to delete this segment?')) {
                this.slices.splice(index, 1);
                if (this.activeIndex === index) this.activeIndex = -1;
                else if (this.activeIndex > index) this.activeIndex--;
                
                await api.saveSlices(this.videoId, this.slices);
                syncUI();
            }
        };

        const updateActiveSlice = (updates) => {
            if (this.activeIndex >= 0) {
                this.slices[this.activeIndex] = { ...this.slices[this.activeIndex], ...updates };
                syncUI();
            }
        };

        document.getElementById('new-slice-btn').onclick = () => {
            const start = Math.floor(video.currentTime * this.fps);
            const durationFrames = Math.floor(this.fps * 2);
            const limit = this.totalFrames || Math.floor((video.duration || 0) * this.fps) || (start + durationFrames);
            const end = Math.min(limit, start + durationFrames);
            this.slices.push({ name: `Action ${this.slices.length + 1}`, start_frame: start, end_frame: end });
            this.activeIndex = this.slices.length - 1;
            syncUI();
        };

        // Precision Adjustments
        document.getElementById('set-start-current').onclick = () => {
            if (this.activeIndex >= 0) {
                const currentFrame = Math.round(video.currentTime * this.fps);
                updateActiveSlice({ start_frame: currentFrame });
            }
        };
        document.getElementById('set-end-current').onclick = () => {
            if (this.activeIndex >= 0) {
                const currentFrame = Math.round(video.currentTime * this.fps);
                updateActiveSlice({ end_frame: currentFrame });
            }
        };

        document.getElementById('start-prev').onclick = () => {
            const val = Math.max(0, this.slices[this.activeIndex].start_frame - 1);
            updateActiveSlice({ start_frame: val });
            this.seekToFrame(val);
        };
        document.getElementById('start-next').onclick = () => {
            const val = Math.min(this.slices[this.activeIndex].end_frame - 1, this.slices[this.activeIndex].start_frame + 1);
            updateActiveSlice({ start_frame: val });
            this.seekToFrame(val);
        };
        document.getElementById('end-prev').onclick = () => {
            const val = Math.max(this.slices[this.activeIndex].start_frame + 1, this.slices[this.activeIndex].end_frame - 1);
            updateActiveSlice({ end_frame: val });
            this.seekToFrame(val);
        };
        document.getElementById('end-next').onclick = () => {
            const limit = this.totalFrames || Math.floor((video.duration || 0) * this.fps) || 999999;
            const val = Math.min(limit, this.slices[this.activeIndex].end_frame + 1);
            updateActiveSlice({ end_frame: val });
            this.seekToFrame(val);
        };

        document.getElementById('start-seek').onclick = () => {
            const s = this.slices[this.activeIndex];
            if (s) {
                this.seekToFrame(s.start_frame);
            }
        };

        document.getElementById('end-seek').onclick = () => {
            const s = this.slices[this.activeIndex];
            if (s) {
                this.seekToFrame(s.end_frame);
            }
        };

document.getElementById('start-frame-input').onchange = (e) => {
    const val = parseInt(e.target.value);
    if (!isNaN(val) && this.activeIndex >= 0) {
        const limit = this.totalFrames || Math.floor((video.duration || 0) * this.fps) || 999999;
        const safeVal = Math.min(limit, Math.max(0, val));
        
        let updates = { start_frame: safeVal };
        const currentEnd = this.slices[this.activeIndex].end_frame;
        
        if (safeVal >= currentEnd) {
            // If start exceeds end, push end forward by 2 seconds
            const durationFrames = Math.floor(this.fps * 2);
            updates.end_frame = Math.min(limit, safeVal + durationFrames);
        }
        
        updateActiveSlice(updates);
        this.seekToFrame(safeVal);
    }
};

document.getElementById('end-frame-input').onchange = (e) => {
    const val = parseInt(e.target.value);
    if (!isNaN(val) && this.activeIndex >= 0) {
        const limit = this.totalFrames || Math.floor((video.duration || 0) * this.fps) || 999999;
        const safeVal = Math.min(limit, Math.max(0, val));
        updateActiveSlice({ end_frame: safeVal });
        this.seekToFrame(safeVal);
    }
};

        document.getElementById('active-slice-name').oninput = (e) => {
            if (this.activeIndex >= 0) {
                this.slices[this.activeIndex].name = e.target.value;
                syncUI(); // Ensure name update is visible in list
            }
        };

        document.getElementById('save-active-btn').onclick = async () => {
            if (this.activeIndex < 0) return;
            const btn = document.getElementById('save-active-btn');
            btn.disabled = true;
            btn.textContent = 'Saving...';
            
            try {
                // Save the current state of slices (which are sorted via syncUI)
                await api.saveSlices(this.videoId, this.slices);
                
                btn.textContent = '✅ Saved';
                setTimeout(() => {
                    btn.textContent = '💾 Save Current Slice';
                    btn.disabled = false;
                }, 2000);
            } catch (e) {
                console.error(e);
                btn.textContent = '❌ Save Failed';
                setTimeout(() => {
                    btn.textContent = '💾 Save Current Slice';
                    btn.disabled = false;
                }, 2000);
            }
        };

        document.getElementById('export-active-btn').onclick = async () => {
            if (this.activeIndex < 0) return;
            const btn = document.getElementById('export-active-btn');
            const s = this.slices[this.activeIndex];
            
            btn.disabled = true;
            btn.textContent = 'Exporting...';
            
            try {
                const res = await api.exportSlice(this.videoId, {
                    start_frame: s.start_frame,
                    end_frame: s.end_frame,
                    name: s.name
                });
                
                if (res.url) {
                    btn.textContent = '✅ Exported';
                    setTimeout(() => {
                        btn.textContent = '✂️ Export Slice Video';
                        btn.disabled = false;
                    }, 2000);
                } else {
                    throw new Error('Export failed');
                }
            } catch (e) {
                console.error(e);
                btn.textContent = '❌ Export Failed';
                setTimeout(() => {
                    btn.textContent = '✂️ Export Slice Video';
                    btn.disabled = false;
                }, 2000);
            }
        };

        playBtn.onclick = () => {
            if (video.paused) {
                video.play();
                playBtn.textContent = '⏸ Pause';
                playBtn.classList.add('active');
            } else {
                video.pause();
                playBtn.textContent = '▶ Play';
                playBtn.classList.remove('active');
            }
        };

        loopToggle.onclick = () => {
            this.isLooping = !this.isLooping;
            loopToggle.classList.toggle('active', this.isLooping);
            loopToggle.textContent = this.isLooping ? '🔄 Loop On' : '🔄 Loop Off';
        };

        skeletonToggle.onclick = () => {
            this.showSkeleton = !this.showSkeleton;
            skeletonToggle.classList.toggle('active', this.showSkeleton);
            skeletonToggle.textContent = this.showSkeleton ? '🔘 Skeleton On' : '🔘 Skeleton Off';
        };

        track.onclick = (e) => {
            if (!video.duration || !isFinite(video.duration)) return;
            const rect = track.getBoundingClientRect();
            if (rect.width === 0) return;
            const pos = (e.clientX - rect.left) / rect.width;
            const targetFrame = Math.round(pos * this.totalFrames);
            this.seekToFrame(targetFrame);
        };

        const drawPose = (lms, color, radius, opacity = 1.0) => {
            if (!lms) return;
            ctx.globalAlpha = opacity;
            ctx.strokeStyle = color; 
            ctx.fillStyle = color; 
            
            // Scalable line width
            ctx.lineWidth = Math.max(2, canvas.width / 400); 
            
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

        video.ontimeupdate = async () => {
            if (this.showSkeleton && !video.paused && this.pose) {
                await this.pose.send({image: video});
            }
        };

        this.lastDisplayFrame = -1;
        this.lastDisplayTime = -1;

        const renderLoop = () => {
            if (!this.running) return;

            // Update current status display
            const currentFrame = Math.round(video.currentTime * this.fps);
            if (currentFrame !== this.lastDisplayFrame) {
                const el = document.getElementById('current-frame-display');
                if (el) el.textContent = currentFrame;
                this.lastDisplayFrame = currentFrame;
            }

            const currentTimeStr = video.currentTime.toFixed(3);
            if (currentTimeStr !== this.lastDisplayTime) {
                const el = document.getElementById('current-time-display');
                if (el) el.textContent = currentTimeStr + 's';
                this.lastDisplayTime = currentTimeStr;
            }

            // Ensure internal resolution matches video intrinsic resolution
            if (video.videoWidth && (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight)) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
            }


            // 2. Sub-pixel precision alignment via getBoundingClientRect
            const vRect = video.getBoundingClientRect();
            const containerRect = video.parentElement.getBoundingClientRect();
            
            canvas.style.width = vRect.width + 'px';
            canvas.style.height = vRect.height + 'px';
            canvas.style.left = (vRect.left - containerRect.left) + 'px';
            canvas.style.top = (vRect.top - containerRect.top) + 'px';

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (this.showSkeleton) {
                if (this.keyframeLandmarks) drawPose(this.keyframeLandmarks, '#fbbf24', 5, 0.4); // Yellow (Keyframe)
                if (this.currentFrameLandmarks) drawPose(this.currentFrameLandmarks, '#22c55e', 8); // Green (Current)
            }

            if (video.duration) {
                playhead.style.left = (video.currentTime / video.duration * 100) + '%';
            }

            if (this.isLooping && this.activeIndex >= 0 && !video.paused) {
                const s = this.slices[this.activeIndex];
                const endTime = s.end_frame / this.fps;
                const startTime = s.start_frame / this.fps;
                if (video.currentTime >= endTime || video.currentTime < startTime - 0.1) {
                    video.currentTime = startTime;
                }
            }

            requestAnimationFrame(renderLoop);
        };

        renderRuler();
        syncUI();
        requestAnimationFrame(renderLoop);
    }

    dispose() { this.running = false; }
}
