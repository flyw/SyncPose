import api from '../services/api.js';

export default class RefinementPage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.video = await api.getVideo(this.videoId);

        return `
            <div class="pro-layout">
                <!-- Left Sidebar: Clip List -->
                <div class="pro-sidebar" style="width: 300px; border-right: 1px solid var(--border); background: var(--panel);">
                    <div style="padding: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Project Clips</h3>
                        <button id="refresh-clips-btn" class="btn-outline" style="padding: 4px 8px; font-size: 10px;">Refresh</button>
                    </div>
                    <div id="clip-list" style="flex: 1; overflow-y: auto; padding: 10px;">
                        <div class="text-muted small" style="text-align: center; padding: 20px;">Loading clips...</div>
                    </div>
                </div>

                <!-- Center: Video Preview -->
                <div style="flex: 1; display: flex; flex-direction: column; background: #000; position: relative;">
                    <div id="preview-container" style="flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;">
                        <!-- Empty State Leading Page -->
                        <div id="leading-page" style="text-align: center; color: var(--text-muted); z-index: 10;">
                            <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">📼</div>
                            <h2 style="color: var(--text-main); margin-bottom: 10px;">No Clip Selected</h2>
                            <p style="max-width: 400px; margin: 0 auto; line-height: 1.6;">
                                Choose a video segment from the left panel to begin fine-tuning. 
                                You can align poses, smooth motions, and check frame-by-frame consistency.
                            </p>
                        </div>
                        
                        <video id="video-player" class="hidden" style="max-width: 100%; max-height: 100%; z-index: 1;"></video>
                        <img id="warp-preview-image" class="hidden" style="position: absolute; pointer-events: auto; z-index: 3; object-fit: contain; cursor: pointer;">
                        <img id="keyframe-photo" class="hidden" style="position: absolute; pointer-events: none; z-index: 4; object-fit: contain; opacity: 0.5;">
                        <!-- Interactive Canvas -->
                        <canvas id="landmark-overlay" class="hidden" style="position: absolute; pointer-events: auto; z-index: 5; cursor: default;"></canvas>
                    </div>
                </div>

                <!-- Right Sidebar: Refinement Toolbox -->
                <div id="toolbox" class="pro-sidebar hidden" style="width: 350px; border-left: 1px solid var(--border); background: var(--panel);">
                    <div style="padding: 15px; border-bottom: 1px solid var(--border);">
                        <h3 style="margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Optimization Toolbox</h3>
                    </div>
                    
                    <div style="padding: 20px; flex: 1; overflow-y: auto;">
                        <div class="control-group">
                            <h3>Playback Control</h3>
                            <div style="background: #020617; border-radius: 4px; padding: 12px; margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; font-family: monospace; font-size: 11px; color: var(--primary); margin-bottom: 10px;">
                                    <span>Frame: <strong id="cur-frame-text">0</strong></span>
                                    <span>Time: <strong id="cur-time-text">0.000s</strong></span>
                                </div>
                                <div id="mini-timeline" style="width: 100%; height: 6px; background: #334155; border-radius: 3px; position: relative; cursor: pointer; margin-bottom: 15px;">
                                    <div id="mini-playhead" style="position: absolute; top: -4px; left: 0%; width: 14px; height: 14px; background: var(--primary); border: 2px solid white; border-radius: 50%; transform: translateX(-50%); pointer-events: none;"></div>
                                </div>
                                <div style="display: flex; gap: 8px; justify-content: center;">
                                    <button id="ref-prev-frame" class="btn-outline" style="padding: 6px 12px;">❮</button>
                                    <button id="ref-play-btn" class="btn-primary" style="flex: 1; padding: 6px 12px;">▶ Play</button>
                                    <button id="ref-next-frame" class="btn-outline" style="padding: 6px 12px;">❯</button>
                                </div>
                            </div>

                            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                                <button id="loop-toggle" class="btn-outline" style="flex: 1; padding: 6px; font-size: 11px;">🔄 Loop: Off</button>
                                <button id="skeleton-toggle" class="btn-outline active" style="flex: 1; padding: 6px; font-size: 11px; border-color: var(--primary);">🔘 Skeleton: On</button>
                            </div>
                            
                            <label>Keyframe Photo Opacity: <span id="opacity-val">50%</span></label>
                            <input type="range" id="keyframe-opacity" min="0" max="100" value="50" style="width: 100%;">
                        </div>

                        <div class="control-group">
                            <h3>Method Selection</h3>
                            <select id="refine-method" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 10px; border-radius: 4px; font-size: 13px;">
                                <option value="mls">Spatial Alignment (MLS Warp)</option>
                                <option value="rife">Temporal Smoothing (RIFE)</option>
                            </select>
                        </div>

                        <!-- MLS Parameters -->
                        <div id="mls-params" class="control-group">
                            <h3>MLS Parameters</h3>
                            <div style="margin-bottom: 15px;">
                                <label>Alignment Strategy</label>
                                <select id="mls-strategy" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 8px; border-radius: 4px;">
                                    <option value="progressive">Progressive (Fade to Start)</option>
                                    <option value="constant">Constant (Uniform Warp)</option>
                                </select>
                            </div>
                            <div style="margin-bottom: 15px;">
                                <label>Alpha (Influence Decay): <span id="alpha-val">1.0</span></label>
                                <input type="range" id="mls-alpha" min="0.5" max="3.0" step="0.1" value="1.0" style="width: 100%;">
                            </div>
                            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                                <div style="flex: 1;">
                                    <label>Fade In Window</label>
                                    <input type="number" id="mls-fade-in-frames" value="15" min="0" max="120" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 8px; border-radius: 4px;">
                                </div>
                                <div style="flex: 1;">
                                    <label>Fade Out Window</label>
                                    <input type="number" id="mls-fade-out-frames" value="15" min="0" max="120" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 8px; border-radius: 4px;">
                                </div>
                            </div>

                            <!-- NEW: Manual Adjustment Toggle -->
                            <div style="margin-bottom: 15px; border: 1px solid var(--border); padding: 10px; border-radius: 6px; background: #020617;">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                    <label style="margin: 0; font-weight: bold; color: var(--warning);">Manual Anchor Adjust</label>
                                    <input type="checkbox" id="manual-adjust-toggle" style="width: 18px; height: 18px; cursor: pointer;">
                                </div>
                                <p class="text-muted" style="font-size: 10px; margin: 0;">Enable this to drag yellow dots on the screen and fine-tune the target pose.</p>
                                <button id="reset-manual-btn" class="btn-outline hidden" style="width: 100%; margin-top: 8px; padding: 4px; font-size: 10px;">Reset to Original Keyframe</button>
                            </div>

                            <div style="margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="mls-show-grid" style="width: 16px; height: 16px; cursor: pointer;">
                                <label for="mls-show-grid" style="margin-bottom: 0; cursor: pointer;">Show Deformation Grid</label>
                            </div>
                            <button id="preview-warp-btn" class="btn-outline" style="width: 100%; padding: 8px; font-size: 12px; border-color: var(--warning); color: var(--warning);">👁️ Warp Current Frame Preview</button>
                        </div>

                        <div id="rife-params" class="control-group hidden">
                            <h3>RIFE Parameters</h3>
                            <label>Interpolated Frames</label>
                            <input type="number" id="rife-frames" value="8" min="2" max="64" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 8px; border-radius: 4px;">
                        </div>

                        <div style="margin-top: 20px;">
                            <label>Iterative Remarks (Notes)</label>
                            <textarea id="refine-remarks" placeholder="e.g. Manual tweak shoulders..." style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 10px; border-radius: 4px; font-size: 12px; height: 50px; resize: vertical;"></textarea>
                        </div>

                        <div style="margin-top: 30px;">
                            <div id="process-status" style="font-size: 11px; color: var(--primary); margin-bottom: 10px; min-height: 14px; font-weight: 600;"></div>
                            <div id="progress-container" class="hidden" style="width: 100%; height: 4px; background: #0f172a; border-radius: 2px; margin-bottom: 15px; overflow: hidden;">
                                <div id="refine-progress-bar" style="width: 0%; height: 100%; background: var(--primary); transition: width 0.3s;"></div>
                            </div>
                            <button id="process-btn" class="btn-success" style="padding: 15px; font-size: 14px; width: 100%;">🚀 Process & Save As New</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async afterRender() {
        // Elements
        this.clipList = document.getElementById('clip-list');
        this.videoPlayer = document.getElementById('video-player');
        this.canvas = document.getElementById('landmark-overlay');
        this.keyframePhoto = document.getElementById('keyframe-photo');
        this.warpPreview = document.getElementById('warp-preview-image');
        this.ctx = this.canvas.getContext('2d');
        this.leadingPage = document.getElementById('leading-page');
        this.toolbox = document.getElementById('toolbox');
        this.playBtn = document.getElementById('ref-play-btn');
        this.prevBtn = document.getElementById('ref-prev-frame');
        this.nextBtn = document.getElementById('ref-next-frame');
        this.curFrameText = document.getElementById('cur-frame-text');
        this.curTimeText = document.getElementById('cur-time-text');
        this.miniTimeline = document.getElementById('mini-timeline');
        this.miniPlayhead = document.getElementById('mini-playhead');
        this.processBtn = document.getElementById('process-btn');
        this.processStatus = document.getElementById('process-status');
        this.loopToggle = document.getElementById('loop-toggle');
        this.skeletonToggle = document.getElementById('skeleton-toggle');
        this.manualToggle = document.getElementById('manual-adjust-toggle');
        this.resetManualBtn = document.getElementById('reset-manual-btn');
        this.opacitySlider = document.getElementById('keyframe-opacity');
        this.refineMethod = document.getElementById('refine-method');
        this.alphaSlider = document.getElementById('mls-alpha');
        this.alphaVal = document.getElementById('alpha-val');
        this.previewBtn = document.getElementById('preview-warp-btn');
        
        // State
        this.selectedClip = null;
        this.running = true;
        this.isLooping = false;
        this.showSkeleton = true;
        this.keyframeOpacity = 0.5;
        this.keyframeLandmarks = null; // Original
        this.targetLandmarks = null;   // Editable version
        this.currentFrameLandmarks = null;
        this.poseProcessing = false;
        this.isManualMode = false;
        this.draggingPointIdx = -1;
        this.fps = 30;

        const CONNECTIONS = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28]];

        // Fetch Keyframe reference
        const fetchKeyframe = async () => {
            try {
                const kfs = await api.getKeyframes(this.videoId);
                if (kfs.length > 0) {
                    const k = kfs[0];
                    this.keyframePhoto.src = k.image_url || `/uploads/${this.videoId}/keyframes/frame_${k.frame}.jpg`;
                    const data = await fetch(`/api/v1/resources/${this.videoId}/frame_data/${k.frame}`).then(r => r.json());
                    if (data.landmarks) {
                        this.keyframeLandmarks = JSON.parse(JSON.stringify(data.landmarks));
                        this.targetLandmarks = JSON.parse(JSON.stringify(data.landmarks));
                    }
                }
            } catch (e) { console.error("Failed to load keyframe", e); }
        };
        await fetchKeyframe();

        // Initialize MediaPipe
        this.initPose = async () => {
            if (typeof Pose === 'undefined') return;
            this.pose = new Pose({ locateFile: (file) => `/static/libs/${file}` });
            this.pose.setOptions({ modelComplexity: 1, smoothLandmarks: true, minDetectionConfidence: 0.5 });
            this.pose.onResults((results) => { if (results.poseLandmarks) this.currentFrameLandmarks = results.poseLandmarks.map(lm => [lm.x, lm.y, lm.z, lm.visibility]); });
        };
        this.initPose();

        const loadClips = async () => {
            this.clipList.innerHTML = '<div class="text-muted small" style="text-align: center; padding: 20px;">Loading clips...</div>';
            try {
                const clips = await api.getClips(this.videoId);
                if (clips.length === 0) { 
                    this.clipList.innerHTML = '<div class="text-muted small" style="text-align: center; padding: 20px;">No clips found.</div>'; 
                    return; 
                }

                // Group clips by their base name
                const groups = {};
                const baseNamesOrder = []; // To maintain chronological order of groups

                clips.forEach(clip => {
                    const nameNoExt = clip.filename.replace(/\.[^/.]+$/, "");
                    // Extract base name by stripping refinement suffixes and timestamps
                    const baseName = nameNoExt.split(/(_mls_|_rife_|_\d{8}_\d{6})/)[0];
                    
                    if (!groups[baseName]) {
                        groups[baseName] = [];
                        baseNamesOrder.push(baseName);
                    }
                    groups[baseName].push(clip);
                });

                this.clipList.innerHTML = baseNamesOrder.map(baseName => {
                    const groupClips = groups[baseName];
                    const isGroupActive = groupClips.some(c => c.filename === this.selectedClip);
                    
                    return `
                        <div class="clip-group" style="margin-bottom: 1.2rem; border: 1px solid ${isGroupActive ? 'var(--primary)' : 'var(--border)'}; border-radius: 8px; background: ${isGroupActive ? 'rgba(99, 102, 241, 0.03)' : 'transparent'}; overflow: hidden;">
                            <div class="group-header" style="padding: 8px 12px; background: ${isGroupActive ? 'rgba(99, 102, 241, 0.1)' : 'var(--panel-header)'}; font-size: 11px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border);">
                                <span style="color: ${isGroupActive ? 'var(--primary)' : 'var(--text-muted)'}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px;">📦 ${baseName}</span>
                                <span style="background: var(--border); padding: 1px 6px; border-radius: 10px; font-size: 9px; opacity: 0.7;">${groupClips.length}</span>
                            </div>
                            <div style="padding: 6px;">
                                ${groupClips.map(clip => {
                                    const isSelected = this.selectedClip === clip.filename;
                                    const isRefined = clip.filename.includes('_mls_') || clip.filename.includes('_rife_');
                                    // Clean up display name: remove baseName and leading underscores
                                    let displayName = clip.filename === (baseName + '.mp4') 
                                        ? '⭐ Original Slice' 
                                        : '└── ' + clip.filename.replace(baseName, '').replace(/^[_]+/, '').replace(/\.mp4$/, '');

                                    return `
                                        <div class="candidate-card ${isSelected ? 'active' : ''}" 
                                             style="padding: 8px 10px; margin-bottom: 4px; position: relative; cursor: pointer; border-radius: 4px; border: 1px solid ${isSelected ? 'var(--primary)' : 'transparent'}; background: ${isSelected ? 'var(--panel)' : 'transparent'}; transition: all 0.2s;" 
                                             onclick="window.selectRefineClip('${clip.filename}', '${clip.url}')">
                                            
                                            <div style="font-size: 12px; font-weight: ${isSelected ? '600' : '400'}; color: ${isSelected ? 'var(--primary)' : 'var(--text-main)'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 42px;" title="${clip.filename}">
                                                ${displayName}
                                            </div>
                                            
                                            <div style="margin-top: 3px; display: flex; justify-content: space-between; align-items: center; opacity: 0.8;">
                                                <span style="font-size: 9px; opacity: 0.6;">${(clip.size / (1024 * 1024)).toFixed(2)} MB</span>
                                                ${clip.remarks ? `<span style="font-size: 9px; color: var(--success); font-style: italic; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${clip.remarks}</span>` : ''}
                                            </div>

                                            <div style="position: absolute; top: 7px; right: 6px; display: flex; gap: 4px;">
                                                <button title="Download" style="background: transparent; border: none; color: var(--primary); cursor: pointer; padding: 2px; font-size: 12px; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6" onclick="window.downloadClip(event, '${clip.url}', '${clip.filename}')">📥</button>
                                                <button title="Delete" style="background: transparent; border: none; color: #ef4444; cursor: pointer; padding: 2px; font-size: 12px; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6" onclick="window.deleteRefineClip(event, '${clip.filename}')">✕</button>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) { 
                this.clipList.innerHTML = '<div class="text-danger small">Failed to load clips.</div>'; 
            }
        };

        window.selectRefineClip = (filename, url) => {
            this.selectedClip = filename;
            this.currentFrameLandmarks = null;
            this.videoPlayer.src = url;
            this.videoPlayer.classList.remove('hidden'); this.canvas.classList.remove('hidden'); this.keyframePhoto.classList.remove('hidden');
            this.warpPreview.classList.add('hidden'); this.leadingPage.classList.add('hidden'); this.toolbox.classList.remove('hidden');
            this.videoPlayer.load();
            this.videoPlayer.onloadedmetadata = () => { this.fps = this.video.fps || 30; this.videoPlayer.play(); this.playBtn.textContent = '⏸ Pause'; };
            loadClips();
        };

        window.deleteRefineClip = async (event, filename) => {
            event.stopPropagation();
            if (confirm(`Delete "${filename}"?`)) {
                try {
                    await api.deleteClip(this.videoId, filename);
                    if (this.selectedClip === filename) { this.selectedClip = null; this.videoPlayer.src = ''; this.leadingPage.classList.remove('hidden'); this.toolbox.classList.add('hidden'); }
                    await loadClips();
                } catch (e) { alert('Failed: ' + e.message); }
            }
        };

        window.downloadClip = (event, url, filename) => {
            event.stopPropagation();
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };

        // --- Interaction Logic ---
        this.manualToggle.onchange = () => {
            this.isManualMode = this.manualToggle.checked;
            this.resetManualBtn.classList.toggle('hidden', !this.isManualMode);
            this.canvas.style.cursor = this.isManualMode ? 'crosshair' : 'default';
        };

        this.resetManualBtn.onclick = () => {
            if (this.keyframeLandmarks) this.targetLandmarks = JSON.parse(JSON.stringify(this.keyframeLandmarks));
        };

        this.canvas.onmousedown = (e) => {
            if (!this.isManualMode || !this.targetLandmarks) return;
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            
            // Find closest landmark (膝盖及以上 0-26)
            let minDist = 0.03;
            let foundIdx = -1;
            for (let i = 0; i <= 26; i++) {
                const lm = this.targetLandmarks[i];
                const d = Math.sqrt((x - lm[0])**2 + (y - lm[1])**2);
                if (d < minDist) { minDist = d; foundIdx = i; }
            }
            this.draggingPointIdx = foundIdx;
        };

        window.onmousemove = (e) => {
            if (this.draggingPointIdx === -1) return;
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            this.targetLandmarks[this.draggingPointIdx][0] = Math.max(0, Math.min(1, x));
            this.targetLandmarks[this.draggingPointIdx][1] = Math.max(0, Math.min(1, y));
        };

        window.onmouseup = () => { this.draggingPointIdx = -1; };

        this.playBtn.onclick = () => { if (this.videoPlayer.paused) { this.videoPlayer.play(); this.playBtn.textContent = '⏸ Pause'; } else { this.videoPlayer.pause(); this.playBtn.textContent = '▶ Play'; } };
        this.prevBtn.onclick = () => { this.videoPlayer.pause(); this.videoPlayer.currentTime = Math.max(0, this.videoPlayer.currentTime - 1/this.fps); };
        this.nextBtn.onclick = () => { this.videoPlayer.pause(); this.videoPlayer.currentTime = Math.min(this.videoPlayer.duration, this.videoPlayer.currentTime + 1/this.fps); };
        this.miniTimeline.onclick = (e) => { const rect = this.miniTimeline.getBoundingClientRect(); const pos = (e.clientX - rect.left) / rect.width; if (this.videoPlayer.duration) this.videoPlayer.currentTime = pos * this.videoPlayer.duration; };
        
        this.loopToggle.onclick = () => { this.isLooping = !this.isLooping; this.videoPlayer.loop = this.isLooping; this.loopToggle.classList.toggle('active', this.isLooping); this.loopToggle.textContent = this.isLooping ? '🔄 Loop: On' : '🔄 Loop: Off'; };
        this.skeletonToggle.onclick = () => { this.showSkeleton = !this.showSkeleton; this.skeletonToggle.classList.toggle('active', this.showSkeleton); this.skeletonToggle.textContent = this.showSkeleton ? '🔘 Skeleton: On' : '🔘 Skeleton: Off'; };
        this.opacitySlider.oninput = (e) => { this.keyframeOpacity = e.target.value / 100; document.getElementById('opacity-val').textContent = e.target.value + '%'; if (this.keyframePhoto) this.keyframePhoto.style.opacity = this.keyframeOpacity; };
        this.alphaSlider.oninput = (e) => { this.alphaVal.textContent = e.target.value; };

        this.previewBtn.onclick = async () => {
            if (!this.selectedClip) return;
            this.previewBtn.disabled = true; this.previewBtn.textContent = '⌛ Warping...';
            const currentFrameIdx = Math.round(this.videoPlayer.currentTime * this.fps);
            try {
                const res = await api.previewMls(this.videoId, { 
                    source_filename: this.selectedClip, frame_index: currentFrameIdx, 
                    manual_target_lms: this.targetLandmarks,
                    params: { alpha: this.alphaSlider.value, show_grid: document.getElementById('mls-show-grid').checked } 
                });
                if (res.url) { this.warpPreview.src = res.url; this.warpPreview.classList.remove('hidden'); }
            } catch (e) { alert("Preview failed: " + e.message); }
            this.previewBtn.disabled = false; this.previewBtn.textContent = '👁️ Warp Current Frame Preview';
        };

        this.warpPreview.onclick = () => { this.warpPreview.classList.add('hidden'); };
        this.refineMethod.onchange = () => { const method = this.refineMethod.value; document.getElementById('mls-params').classList.toggle('hidden', method !== 'mls'); document.getElementById('rife-params').classList.toggle('hidden', method !== 'rife'); };
        document.getElementById('refresh-clips-btn').onclick = loadClips;

        const drawPose = (lms, color, radius, opacity = 1.0, isInteractive = false) => {
            if (!lms) return;
            this.ctx.globalAlpha = opacity; this.ctx.strokeStyle = color; this.ctx.fillStyle = color;
            const scale = this.canvas.width / 1000;
            this.ctx.lineWidth = Math.max(2, 3 * scale);
            const scaledRadius = Math.max(2, radius * scale);
            const w = this.canvas.width, h = this.canvas.height;
            
            CONNECTIONS.forEach(([i, j]) => {
                const p1 = lms[i], p2 = lms[j];
                if (p1[3] > 0.3 && p2[3] > 0.3) { this.ctx.beginPath(); this.ctx.moveTo(p1[0] * w, p1[1] * h); this.ctx.lineTo(p2[0] * w, p2[1] * h); this.ctx.stroke(); }
            });
            lms.forEach((p, idx) => { 
                if (p[3] > 0.3) { 
                    this.ctx.beginPath(); 
                    // Draw larger handles if interactive and knee-up
                    const r = (isInteractive && idx <= 26) ? (scaledRadius * 1.5) : scaledRadius;
                    this.ctx.arc(p[0] * w, p[1] * h, r, 0, Math.PI*2); 
                    this.ctx.fill(); 
                    if (isInteractive && idx <= 26) { this.ctx.strokeStyle = 'white'; this.ctx.stroke(); }
                } 
            });
            this.ctx.globalAlpha = 1.0;
        };

        const renderLoop = async () => {
            if (!this.running) return;
            if (this.videoPlayer && !this.videoPlayer.classList.contains('hidden')) {
                const curTime = this.videoPlayer.currentTime;
                this.curFrameText.textContent = Math.round(curTime * this.fps);
                this.curTimeText.textContent = curTime.toFixed(3) + 's';
                if (this.videoPlayer.duration) this.miniPlayhead.style.left = (curTime / this.videoPlayer.duration * 100) + '%';
            }
            if (this.videoPlayer.videoWidth && (this.canvas.width !== this.videoPlayer.videoWidth || this.canvas.height !== this.videoPlayer.videoHeight)) {
                this.canvas.width = this.videoPlayer.videoWidth; this.canvas.height = this.videoPlayer.videoHeight;
            }
            const vRect = this.videoPlayer.getBoundingClientRect();
            const containerRect = document.getElementById('preview-container').getBoundingClientRect();
            if (vRect.width > 0) {
                const style = { width: vRect.width + 'px', height: vRect.height + 'px', left: (vRect.left - containerRect.left) + 'px', top: (vRect.top - containerRect.top) + 'px' };
                Object.assign(this.canvas.style, style); Object.assign(this.keyframePhoto.style, style); Object.assign(this.warpPreview.style, style);
            }
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            if (this.showSkeleton && !this.videoPlayer.classList.contains('hidden')) {
                if (!this.videoPlayer.paused && this.pose && !this.poseProcessing && this.videoPlayer.readyState >= 2 && this.videoPlayer.videoWidth > 0) {
                    this.poseProcessing = true;
                    this.pose.send({image: this.videoPlayer}).then(() => { this.poseProcessing = false; }).catch(() => { this.poseProcessing = false; });
                }
                // Draw Target (Editable) Skeleton - Yellow
                if (this.targetLandmarks) drawPose(this.targetLandmarks, '#fbbf24', 4, this.keyframeOpacity, this.isManualMode);
                // Draw Current Skeleton - Green
                if (this.currentFrameLandmarks) drawPose(this.currentFrameLandmarks, '#22c55e', 6);
            }
            requestAnimationFrame(renderLoop);
        };

        this.processBtn.onclick = async () => {
            if (!this.selectedClip) return;
            const method = this.refineMethod.value;
            const params = { alpha: this.alphaSlider.value };
            if (method === 'mls') {
                params.strategy = document.getElementById('mls-strategy').value;
                params.fade_in_frames = parseInt(document.getElementById('mls-fade-in-frames').value);
                params.fade_out_frames = parseInt(document.getElementById('mls-fade-out-frames').value);
            }
            this.processBtn.disabled = true; this.processBtn.textContent = '⚙️ Processing...';
            const progressBar = document.getElementById('refine-progress-bar');
            const progressContainer = document.getElementById('progress-container');
            progressContainer.classList.remove('hidden');
            const pollInterval = setInterval(async () => {
                const status = await api.getVideo(this.videoId);
                if (status && status.refine_progress !== undefined) {
                    progressBar.style.width = status.refine_progress + '%';
                    if (status.refine_status === 'warping') this.processStatus.textContent = `Warping frames: ${status.refine_progress}%`;
                }
            }, 500);
            try {
                const res = await api.processRefinement(this.videoId, { 
                    source_filename: this.selectedClip, operation: method, params: params, 
                    remarks: document.getElementById('refine-remarks').value,
                    manual_target_lms: this.targetLandmarks // Send manually adjusted points
                });
                clearInterval(pollInterval); progressContainer.classList.add('hidden');
                if (res.filename) {
                    document.getElementById('refine-remarks').value = '';
                    this.processStatus.textContent = '✅ Generated: ' + res.filename;
                    this.processBtn.disabled = false; this.selectedClip = res.filename;
                    await loadClips(); window.selectRefineClip(res.filename, res.url);
                }
            } catch (e) { clearInterval(pollInterval); progressContainer.classList.add('hidden'); this.processStatus.textContent = '❌ Error: ' + e.message; this.processBtn.disabled = false; }
        };

        loadClips();
        requestAnimationFrame(renderLoop);
    }
    dispose() { this.running = false; }
}
