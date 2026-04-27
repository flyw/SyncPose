import api from '../services/api.js';

export default class RefinementPage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.selectedBaseClip = urlParams.get('clip'); // e.g. "slice_01"
        this.video = await api.getVideo(this.videoId);

        // --- LEVEL 1: SELECTION VIEW ---
        if (!this.selectedBaseClip) {
            return `
                <div class="page-container" style="padding: 30px;">
                    <div class="section-header" style="margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h2 style="font-size: 24px; margin-bottom: 8px;">Select a Segment</h2>
                            <p class="text-muted">Choose an original slice to view refined versions or start a new optimization.</p>
                        </div>
                        <button class="btn-outline" onclick="location.reload()">🔄 Refresh List</button>
                    </div>
                    <div id="base-clip-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                        <div class="text-muted">Scanning for segments...</div>
                    </div>
                </div>
            `;
        }

        // --- LEVEL 2: DETAIL VIEW ---
        return `
            <div class="pro-layout">
                <!-- Left Sidebar: Filtered Variant List -->
                <div class="pro-sidebar" style="width: 350px; border-right: 1px solid var(--border); background: var(--panel); display: flex; flex-direction: column; z-index: 10;">
                    <div style="padding: 15px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px;">
                        <button onclick="window.goBackToSelection()" class="btn-link" style="padding: 0; font-size: 11px; color: var(--primary); text-align: left; width: fit-content;">❮ Back to All Clips</button>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-main);">Variants</h3>
                            <button id="refresh-clips-btn" class="btn-outline" style="padding: 2px 6px; font-size: 9px;">Refresh</button>
                        </div>
                    </div>
                    <div id="clip-list" style="flex: 1; overflow-y: auto; padding: 10px;"></div>
                </div>

                <!-- Center: Video Preview -->
                <div style="flex: 1; display: flex; flex-direction: column; background: #000; position: relative; overflow: hidden;">
                    <div id="preview-container" style="flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;">
                        <div id="leading-page" style="text-align: center; color: var(--text-muted); z-index: 10;">
                            <div style="font-size: 48px; margin-bottom: 15px; opacity: 0.5;">👈</div>
                            <h3 style="color: var(--text-main); margin-bottom: 8px;">Select a Variant</h3>
                            <p style="max-width: 300px; margin: 0 auto; line-height: 1.4; font-size: 13px;">Click on a version in the left sidebar.</p>
                        </div>
                        <video id="video-player" class="hidden" style="max-width: 100%; max-height: 100%; z-index: 1;"></video>
                        <img id="warp-preview-image" class="hidden" style="position: absolute; pointer-events: auto; z-index: 4; object-fit: contain; cursor: pointer;">
                        <img id="keyframe-photo" class="hidden" style="position: absolute; pointer-events: none; z-index: 3; object-fit: contain; opacity: 0.5;">
                        <canvas id="landmark-overlay" class="hidden" style="position: absolute; pointer-events: none; z-index: 5; cursor: default;"></canvas>
                    </div>
                </div>

                <!-- Right Sidebar: Toolbox -->
                <div id="toolbox" class="pro-sidebar hidden" style="width: 350px; border-left: 1px solid var(--border); background: var(--panel); display: flex; flex-direction: column; z-index: 10;">
                    <div style="padding: 15px; border-bottom: 1px solid var(--border);">
                        <h3 style="margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Optimization</h3>
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
                                <div style="display: flex; gap: 8px; justify-content: center; margin-bottom: 15px;">
                                        <button id="ref-prev-frame" class="btn-outline" style="padding: 6px 12px;">❮</button>
                                        <button id="ref-play-btn" class="btn-primary" style="flex: 1; padding: 6px 12px;">▶ Play</button>
                                        <button id="ref-next-frame" class="btn-outline" style="padding: 6px 12px;">❯</button>
                                    </div>
                                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                                        <button id="loop-toggle" class="btn-outline" style="flex: 1; padding: 6px; font-size: 11px;">🔄 Loop: Off</button>
                                        <button id="skeleton-toggle" class="btn-primary" style="flex: 1; padding: 6px; font-size: 11px;">🔘 Skeleton: On</button>
                                    </div>
                            </div>
                            <label>Reference Opacity: <span id="opacity-val">50%</span></label>
                            <input type="range" id="keyframe-opacity" min="0" max="100" value="50" style="width: 100%;">
                        </div>
                        <div class="control-group">
                            <h3>Method Selection</h3>
                            <select id="refine-method" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 10px; border-radius: 4px; font-size: 13px;">
                                <option value="mls">Spatial Alignment (33 pts)</option>
                                <option value="holistic">Holistic Alignment (543 pts)</option>
                                <option value="rife">Temporal Smoothing (RIFE)</option>
                            </select>
                        </div>
                        <div id="method-params-container"></div>
                        
                        <div id="preview-tools" class="control-group hidden" style="margin-top: 20px; border-top: 1px solid var(--border); padding-top: 20px;">
                            <h3>Visualization</h3>
                            <div style="display: flex; gap: 8px; margin-bottom: 12px;">
                                <button id="preview-warp-btn" class="btn-primary" style="flex: 1; font-size: 11px; padding: 8px;">👁️ Preview Warp</button>
                                <button id="toggle-warp-layer" class="btn-outline" style="flex: 1; font-size: 11px; padding: 8px;">Layer: On</button>
                            </div>
                            <label>Warp Layer Opacity: <span id="warp-opacity-val">100%</span></label>
                            <input type="range" id="warp-layer-opacity" min="0" max="100" value="100" style="width: 100%;">
                            <label style="margin-top: 10px; display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
                                <input type="checkbox" id="show-grid-toggle" style="width: 14px; height: 14px; margin: 0; cursor: pointer;">
                                <span style="font-size: 11px; color: var(--text-muted);">Show MLS Grid</span>
                            </label>
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
        // State
        this.selectedClip = null;
        this.running = true;
        this.isLooping = false;
        this.showSkeleton = true;
        this.keyframeOpacity = 0.5;
        this.poseProcessing = false;
        this.currentFrameLandmarks = null;
        this.targetLandmarks = null;
        this.keyframeLandmarks = null;
        this.isManualMode = false;
        this.draggingPointIdx = -1;
        this.fps = 30;

        const CONNECTIONS = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28]];
        const HAND_CONNECTIONS = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];

        // Helper: Fetch Keyframe
        const fetchKeyframe = async () => {
            try {
                const kfs = await api.getKeyframes(this.videoId);
                if (kfs.length > 0) {
                    const k = kfs[0];
                    if (this.keyframePhoto) this.keyframePhoto.src = k.image_url || `/uploads/${this.videoId}/keyframes/frame_${k.frame}.jpg`;
                    const data = await fetch(`/api/v1/resources/${this.videoId}/frame_data/${k.frame}`).then(r => r.json());
                    if (data.landmarks) {
                        this.keyframeLandmarks = JSON.parse(JSON.stringify(data.landmarks));
                        this.targetLandmarks = JSON.parse(JSON.stringify(data.landmarks));
                    }
                }
            } catch (e) { console.error("Failed to load keyframe", e); }
        };

        // UI Binding Logic
        const loadClips = async () => {
            try {
                const clips = await api.getClips(this.videoId);
                const groups = {};
                const baseNamesOrder = [];
                clips.forEach(clip => {
                    const baseName = clip.filename.replace(/\.[^/.]+$/, "").split(/(_mls_|_holistic_|_rife_|_\d{8}_\d{6})/)[0];
                    if (!groups[baseName]) { groups[baseName] = []; baseNamesOrder.push(baseName); }
                    groups[baseName].push(clip);
                });

                if (!this.selectedBaseClip) {
                    const grid = document.getElementById('base-clip-grid');
                    if (grid) {
                        grid.innerHTML = baseNamesOrder.map(baseName => {
                            // Filter out _hq from count
                            const variantsCount = groups[baseName].filter(c => !c.filename.includes('_hq.mp4')).length - 1;
                            return `
                                <div class="project-card" style="cursor: pointer; padding: 15px;" onclick="window.enterClipDetail('${baseName}')">
                                    <div style="font-size: 48px; margin-bottom: 10px; text-align: center; background: #020617; border-radius: 8px; padding: 20px;">🎬</div>
                                    <h3 style="font-size: 14px; margin-bottom: 5px; color: var(--text-main);">${baseName}</h3>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                        <span class="status-badge" style="font-size: 10px;">Original</span>
                                        <span style="font-size: 10px; color: var(--primary); font-weight: bold;">${variantsCount} Variants</span>
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }
                } else {
                    const list = document.getElementById('clip-list');
                    // Filter out high-quality masters from the visible list
                    const groupClips = (groups[this.selectedBaseClip] || []).filter(c => !c.filename.includes('_hq.mp4'));
                    groupClips.sort((a,b) => a.filename === (this.selectedBaseClip + '.mp4') ? -1 : b.filename === (this.selectedBaseClip + '.mp4') ? 1 : 0);
                    
                    if (list) {
                        list.innerHTML = groupClips.map(clip => {
                            const isSelected = this.selectedClip === clip.filename;
                            let displayName = clip.filename === (this.selectedBaseClip + '.mp4') ? '⭐ Original Slice' : '└── ' + clip.filename.replace(this.selectedBaseClip, '').replace(/^[_]+/, '').replace(/\.mp4$/, '');
                            
                            // Check if an HQ version exists in the original groups array
                            const hasHq = (groups[this.selectedBaseClip] || []).some(c => c.filename === clip.filename.replace('.mp4', '_hq.mp4'));
                            const downloadUrl = hasHq ? clip.url.replace('.mp4', '_hq.mp4') : clip.url;
                            const downloadLabel = hasHq ? 'Download (HQ Master)' : 'Download';

                            return `
                                <div class="candidate-card ${isSelected ? 'active' : ''}" style="padding: 8px 10px; margin-bottom: 4px; position: relative; cursor: pointer;" onclick="window.selectRefineClip('${clip.filename}', '${clip.url}')">
                                    <div style="font-size: 12px; color: ${isSelected ? 'var(--primary)' : 'var(--text-main)'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 85px;">${displayName}</div>
                                    ${clip.remarks ? `<div style="font-size: 10px; color: var(--primary); background: rgba(99,102,241,0.05); padding: 2px 4px; border-radius: 2px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${clip.remarks}</div>` : ''}
                                    <div style="position: absolute; top: 7px; right: 6px; display: flex; gap: 4px;">
                                        <button class="btn-icon" onclick="window.editRemark(event, '${clip.filename}', '${clip.remarks || ''}')" title="Edit Remark">📝</button>
                                        <button class="btn-icon" onclick="window.downloadClip(event, '${downloadUrl}', '${clip.filename}')" title="${downloadLabel}">${hasHq ? '💎' : '📥'}</button>
                                        <button class="btn-icon" onclick="window.deleteRefineClip(event, '${clip.filename}')" title="Delete">✕</button>
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }
                }
            } catch (e) { console.error(e); }
        };

        // Window Functions
        window.enterClipDetail = (baseName) => { window.location.hash = `#/refinement?id=${this.videoId}&clip=${baseName}`; location.reload(); };
        window.goBackToSelection = () => { window.location.hash = `#/refinement?id=${this.videoId}`; location.reload(); };
        window.selectRefineClip = (filename, url) => {
            this.selectedClip = filename;
            if (this.videoPlayer) {
                this.videoPlayer.src = url;
                this.videoPlayer.classList.remove('hidden'); this.canvas.classList.remove('hidden'); this.keyframePhoto.classList.remove('hidden');
                document.getElementById('leading-page').classList.add('hidden');
                document.getElementById('toolbox').classList.remove('hidden');
                this.videoPlayer.load();
                this.videoPlayer.onloadedmetadata = () => { this.fps = this.video.fps || 30; this.playBtn.textContent = '▶ Play'; };
            }
            loadClips();
        };
        window.deleteRefineClip = async (event, filename) => {
            event.stopPropagation();
            if (confirm(`Delete "${filename}"?`)) {
                await api.deleteClip(this.videoId, filename);
                if (this.selectedClip === filename) location.reload();
                else loadClips();
            }
        };
        window.editRemark = async (event, filename, currentRemark) => {
            event.stopPropagation();
            const newRemark = prompt("Enter remark:", currentRemark);
            if (newRemark !== null) { await api.updateClipRemarks(this.videoId, filename, newRemark); loadClips(); }
        };
        window.downloadClip = (event, url, filename) => {
            event.stopPropagation();
            const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
        };

        // Start Logic
        if (this.selectedBaseClip) {
            this.videoPlayer = document.getElementById('video-player');
            this.canvas = document.getElementById('landmark-overlay');
            this.ctx = this.canvas.getContext('2d');
            this.keyframePhoto = document.getElementById('keyframe-photo');
            this.playBtn = document.getElementById('ref-play-btn');
            this.curFrameText = document.getElementById('cur-frame-text');
            this.curTimeText = document.getElementById('cur-time-text');
            this.miniTimeline = document.getElementById('mini-timeline');
            this.miniPlayhead = document.getElementById('mini-playhead');
            this.refineMethod = document.getElementById('refine-method');
            this.opacitySlider = document.getElementById('keyframe-opacity');
            
            // Initialization for Detail View
            await fetchKeyframe();
            
            const drawPose = (lms, color, radius, opacity = 1.0) => {
                if (!lms || !this.canvas) return;
                const v = this.videoPlayer;
                const cw = this.canvas.width, ch = this.canvas.height;
                const vR = v.videoWidth / v.videoHeight;
                const cR = cw / ch;
                let dW, dH, oX, oY;
                if (cR > vR) { dH = ch; dW = ch * vR; oX = (cw - dW) / 2; oY = 0; }
                else { dW = cw; dH = cw / vR; oX = 0; oY = (ch - dH) / 2; }
                this.ctx.globalAlpha = opacity;
                const isH = lms.length > 33;

                this.ctx.strokeStyle = color; this.ctx.lineWidth = 2;
                CONNECTIONS.forEach(([i, j]) => {
                    if (i >= lms.length || j >= lms.length || (isH && (i < 11 || j < 11))) return;
                    const p1 = lms[i], p2 = lms[j];
                    if (p1[3] > 0.3 && p2[3] > 0.3) { this.ctx.beginPath(); this.ctx.moveTo(p1[0]*dW+oX, p1[1]*dH+oY); this.ctx.lineTo(p2[0]*dW+oX, p2[1]*dH+oY); this.ctx.stroke(); }
                });
                if (isH) {
                    this.ctx.fillStyle = color === '#fbbf24' ? '#f59e0b' : '#22d3ee';
                    for (let i = 33; i < 33 + 478; i += 3) { 
                        const p = lms[i];
                        if (p) { this.ctx.beginPath(); this.ctx.arc(p[0]*dW+oX, p[1]*dH+oY, 1, 0, Math.PI*2); this.ctx.fill(); }
                    }
                }
                this.ctx.fillStyle = color;
                lms.forEach((p, idx) => { 
                    if ((isH && idx < 11) || idx >= 33) return;
                    if (p[3] > 0.3) { this.ctx.beginPath(); this.ctx.arc(p[0]*dW+oX, p[1]*dH+oY, radius, 0, Math.PI*2); this.ctx.fill(); }
                });
            };

            const updateMethodParams = () => {
                const method = this.refineMethod.value;
                const container = document.getElementById('method-params-container');
                const previewTools = document.getElementById('preview-tools');
                
                if (method === 'mls' || method === 'holistic') {
                    previewTools.classList.remove('hidden');
                    container.innerHTML = `
                        <div class="control-group" style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 4px; margin-top: 10px;">
                            <label style="font-size: 11px; margin-bottom: 5px; display: block; color: var(--text-main);">Warp Strategy</label>
                            <select id="mls-strategy" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 5px; font-size: 12px; margin-bottom: 10px;">
                                <option value="progressive">Progressive (Fade In/Out)</option>
                                <option value="global">Global (Whole Video)</option>
                            </select>
                            
                            <div id="progressive-params">
                                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                                    <div style="flex: 1;">
                                        <label style="font-size: 10px; opacity: 0.7; color: var(--text-main);">Fade In (Frames)</label>
                                        <input type="number" id="fade-in-frames" value="15" min="0" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 4px; font-size: 12px;">
                                    </div>
                                    <div style="flex: 1;">
                                        <label style="font-size: 10px; opacity: 0.7; color: var(--text-main);">Fade Out (Frames)</label>
                                        <input type="number" id="fade-out-frames" value="15" min="0" style="width: 100%; background: #0f172a; color: white; border: 1px solid var(--border); padding: 4px; font-size: 12px;">
                                    </div>
                                </div>
                            </div>

                            <label style="font-size: 11px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between; color: var(--text-main);">
                                <span>Warp Strength (Alpha): <span id="alpha-val">1.0</span></span>
                                <span class="info-icon" title="Control the 'hardness' of the warp.&#10;• 1.0: Precise & strict following of points.&#10;• < 1.0: Softer, more natural deformation.&#10;• > 1.0: Very localized distortion." style="cursor: help; opacity: 0.6;">ⓘ</span>
                            </label>
                            <input type="range" id="mls-alpha" min="0" max="300" value="100" style="width: 100%;">
                        </div>
                    `;
                    
                    const strategySelect = document.getElementById('mls-strategy');
                    const progParams = document.getElementById('progressive-params');
                    strategySelect.onchange = () => {
                        progParams.style.display = strategySelect.value === 'progressive' ? 'block' : 'none';
                    };
                    
                    const alphaSlider = document.getElementById('mls-alpha');
                    if (alphaSlider) {
                        alphaSlider.oninput = (e) => {
                            document.getElementById('alpha-val').textContent = (e.target.value / 100).toFixed(1);
                        };
                    }
                } else if (method === 'rife') {
                    previewTools.classList.add('hidden');
                    container.innerHTML = `
                        <div class="control-group" style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; margin-top: 10px; border: 1px solid rgba(255,255,255,0.05);">
                            <label style="font-size: 11px; margin-bottom: 10px; display: block; color: var(--text-dim);">Interpolation Scheme</label>
                            <div class="mode-selector" style="display: flex; gap: 4px; background: #0f172a; padding: 4px; border-radius: 6px; margin-bottom: 15px;">
                                <button class="mode-btn active" data-mode="both" style="flex: 1; font-size: 10px; padding: 6px 2px; border: none; border-radius: 4px; cursor: pointer; transition: all 0.2s;">Both</button>
                                <button class="mode-btn" data-mode="front" style="flex: 1; font-size: 10px; padding: 6px 2px; border: none; border-radius: 4px; cursor: pointer; transition: all 0.2s;">Front</button>
                                <button class="mode-btn" data-mode="back" style="flex: 1; font-size: 10px; padding: 6px 2px; border: none; border-radius: 4px; cursor: pointer; transition: all 0.2s;">Back</button>
                            </div>
                            <input type="hidden" id="rife-mode" value="both">
                            
                            <label style="font-size: 11px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; color: var(--text-dim); border-top: 1px solid rgba(255,255,255,0.05); padding-top: 12px;">
                                <span>Interpolation Factor: <span id="rife-factor-val" style="color: var(--primary); font-weight: bold;">4</span>x</span>
                                <span class="info-icon" title="Number of frames to generate for transitions." style="cursor: help; opacity: 0.6;">ⓘ</span>
                            </label>
                            <input type="range" id="rife-factor" min="2" max="32" value="4" style="width: 100%; accent-color: var(--primary);">
                            
                            <p id="mode-desc" style="font-size: 10px; color: var(--text-dim); margin-top: 12px; line-height: 1.4; opacity: 0.8; font-style: italic;">Seamless loop: Interpolates both Start and End transitions.</p>
                        </div>
                    `;
                    const factorSlider = document.getElementById('rife-factor');
                    factorSlider.oninput = (e) => {
                        document.getElementById('rife-factor-val').textContent = e.target.value;
                    };

                    const modeBtns = container.querySelectorAll('.mode-btn');
                    const modeInput = container.querySelector('#rife-mode');
                    const modeDesc = container.querySelector('#mode-desc');
                    const descs = {
                        'both': 'Seamless loop: Interpolates both Start and End transitions.',
                        'front': 'Start only: Interpolates from Reference frame to Video start.',
                        'back': 'End only: Interpolates from Video end back to Reference frame.'
                    };

                    modeBtns.forEach(btn => {
                        const updateStyles = () => {
                            modeBtns.forEach(b => {
                                const isActive = b === btn;
                                b.style.background = isActive ? 'var(--primary)' : 'transparent';
                                b.style.color = isActive ? 'white' : 'var(--text-dim)';
                                if (isActive) b.classList.add('active');
                                else b.classList.remove('active');
                            });
                        };

                        btn.onclick = () => {
                            updateStyles();
                            modeInput.value = btn.dataset.mode;
                            modeDesc.textContent = descs[btn.dataset.mode];
                        };

                        // Initial style
                        if (btn.dataset.mode === 'both') {
                            btn.style.background = 'var(--primary)';
                            btn.style.color = 'white';
                        } else {
                            btn.style.background = 'transparent';
                            btn.style.color = 'var(--text-dim)';
                        }
                    });
                } else {
                    previewTools.classList.add('hidden');
                    container.innerHTML = '';
                    if (this.warpPreviewImage) this.warpPreviewImage.classList.add('hidden');
                }
            };

            this.refineMethod.onchange = updateMethodParams;
            updateMethodParams();

            // Visualization Tools Binding
            const previewWarpBtn = document.getElementById('preview-warp-btn');
            const warpLayerOpacity = document.getElementById('warp-layer-opacity');
            const toggleWarpLayer = document.getElementById('toggle-warp-layer');
            const showGridToggle = document.getElementById('show-grid-toggle');
            this.warpPreviewImage = document.getElementById('warp-preview-image');
            this.isWarpLayerVisible = true;

            previewWarpBtn.onclick = async () => {
                if (!this.selectedClip) return alert("Select a clip first");
                previewWarpBtn.disabled = true;
                previewWarpBtn.textContent = '⏳ ...';
                
                try {
                    const strategy = document.getElementById('mls-strategy')?.value || 'progressive';
                    const fadeIn = parseInt(document.getElementById('fade-in-frames')?.value || 15);
                    const fadeOut = parseInt(document.getElementById('fade-out-frames')?.value || 15);
                    const alpha = (document.getElementById('mls-alpha')?.value || 100) / 100;
                    const showGrid = showGridToggle.checked;
                    
                    const res = await api.previewMls(this.videoId, {
                        source_filename: this.selectedClip,
                        frame_index: Math.round(this.videoPlayer.currentTime * this.fps),
                        method: this.refineMethod.value,
                        params: {
                            alpha: alpha,
                            show_grid: showGrid,
                            strategy: strategy,
                            fade_in_frames: fadeIn,
                            fade_out_frames: fadeOut
                        }
                    });
                    
                    if (res.url) {
                        this.warpPreviewImage.src = res.url;
                        this.warpPreviewImage.classList.remove('hidden');
                        this.isWarpLayerVisible = true;
                        toggleWarpLayer.textContent = 'Layer: On';
                        toggleWarpLayer.classList.add('btn-primary');
                        toggleWarpLayer.classList.remove('btn-outline');
                    }
                } catch (e) {
                    alert("Preview failed: " + e.message);
                } finally {
                    previewWarpBtn.disabled = false;
                    previewWarpBtn.textContent = '👁️ Preview Warp';
                }
            };

            toggleWarpLayer.onclick = () => {
                this.isWarpLayerVisible = !this.isWarpLayerVisible;
                this.warpPreviewImage.classList.toggle('hidden', !this.isWarpLayerVisible);
                toggleWarpLayer.textContent = `Layer: ${this.isWarpLayerVisible ? 'On' : 'Off'}`;
                toggleWarpLayer.classList.toggle('btn-primary', this.isWarpLayerVisible);
                toggleWarpLayer.classList.toggle('btn-outline', !this.isWarpLayerVisible);
            };

            warpLayerOpacity.oninput = (e) => {
                const val = e.target.value;
                document.getElementById('warp-opacity-val').textContent = val + '%';
                this.warpPreviewImage.style.opacity = val / 100;
            };

            const renderLoop = () => {
                if (!this.running || !this.videoPlayer) return;
                const v = this.videoPlayer;
                if (!v.classList.contains('hidden') && v.readyState >= 2) {
                    this.curFrameText.textContent = Math.round(v.currentTime * this.fps);
                    this.curTimeText.textContent = v.currentTime.toFixed(3) + 's';
                    if (v.duration) this.miniPlayhead.style.left = (v.currentTime / v.duration * 100) + '%';
                    const vRect = v.getBoundingClientRect();
                    const cRect = document.getElementById('preview-container').getBoundingClientRect();
                    const style = { width: v.clientWidth+'px', height: v.clientHeight+'px', left: (vRect.left-cRect.left)+'px', top: (vRect.top-cRect.top)+'px' };
                    Object.assign(this.canvas.style, style); 
                    Object.assign(this.keyframePhoto.style, style);
                    Object.assign(this.warpPreviewImage.style, style);
                    if (this.canvas.width !== v.videoWidth) { this.canvas.width = v.videoWidth; this.canvas.height = v.videoHeight; }
                }
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                if (this.showSkeleton && !v.classList.contains('hidden')) {
                    if (this.targetLandmarks) drawPose(this.targetLandmarks, '#fbbf24', 4);
                    if (this.currentFrameLandmarks) drawPose(this.currentFrameLandmarks, '#22c55e', 6);
                }
                requestAnimationFrame(renderLoop);
            };

            this.playBtn.onclick = () => {
                if (this.videoPlayer.paused) this.videoPlayer.play();
                else this.videoPlayer.pause();
            };

            this.videoPlayer.onplay = () => { this.playBtn.textContent = '⏸ Pause'; };
            this.videoPlayer.onpause = () => { this.playBtn.textContent = '▶ Play'; };
            this.videoPlayer.onended = () => {
                if (this.isLooping) {
                    this.videoPlayer.currentTime = 0;
                    this.videoPlayer.play();
                } else {
                    this.playBtn.textContent = '▶ Play';
                }
            };

            const loopBtn = document.getElementById('loop-toggle');
            loopBtn.onclick = () => {
                this.isLooping = !this.isLooping;
                loopBtn.textContent = `🔄 Loop: ${this.isLooping ? 'On' : 'Off'}`;
                loopBtn.classList.toggle('btn-primary', this.isLooping);
                loopBtn.classList.toggle('btn-outline', !this.isLooping);
            };

            const skelBtn = document.getElementById('skeleton-toggle');
            skelBtn.onclick = () => {
                this.showSkeleton = !this.showSkeleton;
                skelBtn.textContent = `🔘 Skeleton: ${this.showSkeleton ? 'On' : 'Off'}`;
                skelBtn.classList.toggle('btn-primary', this.showSkeleton);
                skelBtn.classList.toggle('btn-outline', !this.showSkeleton);
            };

            document.getElementById('ref-prev-frame').onclick = () => {
                this.videoPlayer.pause();
                this.videoPlayer.currentTime = Math.max(0, this.videoPlayer.currentTime - 1/this.fps);
            };

            document.getElementById('ref-next-frame').onclick = () => {
                this.videoPlayer.pause();
                this.videoPlayer.currentTime = Math.min(this.videoPlayer.duration, this.videoPlayer.currentTime + 1/this.fps);
            };

            this.miniTimeline.onclick = (e) => {
                const rect = this.miniTimeline.getBoundingClientRect();
                const pos = (e.clientX - rect.left) / rect.width;
                if (this.videoPlayer.duration) {
                    this.videoPlayer.currentTime = pos * this.videoPlayer.duration;
                }
            };
            
            this.opacitySlider.oninput = (e) => { 
                const val = e.target.value;
                document.getElementById('opacity-val').textContent = val + '%';
                this.keyframeOpacity = val / 100; 
                this.keyframePhoto.style.opacity = this.keyframeOpacity; 
            };

            const processBtn = document.getElementById('process-btn');
            processBtn.onclick = () => this.processOptimization();
            
            requestAnimationFrame(renderLoop);
        }

        loadClips();
    }

    async processOptimization() {
        const method = document.getElementById('refine-method').value;
        const status = document.getElementById('process-status');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('refine-progress-bar');
        const btn = document.getElementById('process-btn');

        if (!this.selectedClip) {
            alert("Please select a variant (e.g. Original Slice) from the left sidebar first.");
            return;
        }

        btn.disabled = true;
        btn.textContent = '⏳ Processing...';
        status.textContent = `Starting ${method.toUpperCase()} optimization...`;
        progressContainer.classList.remove('hidden');
        progressBar.style.width = '0%';

        try {
            const strategy = document.getElementById('mls-strategy')?.value || 'progressive';
            const fadeIn = parseInt(document.getElementById('fade-in-frames')?.value || 15);
            const fadeOut = parseInt(document.getElementById('fade-out-frames')?.value || 15);
            const alpha = (document.getElementById('mls-alpha')?.value || 100) / 100;
            const interpolationFactor = parseInt(document.getElementById('rife-factor')?.value || 4);
            const interpolationMode = document.getElementById('rife-mode')?.value || 'both';

            const data = {
                operation: method,
                source_filename: this.selectedClip,
                params: {
                    strategy: strategy,
                    fade_in_frames: fadeIn,
                    fade_out_frames: fadeOut,
                    alpha: alpha,
                    interpolation_factor: interpolationFactor,
                    interpolation_mode: interpolationMode
                }
            };

            // Only send manual landmarks if they match the expected count for the method
            // 33 for mls, 543 for holistic. If user hasn't edited, we let backend handle defaults.
            if (this.targetLandmarks) {
                const isHolistic = method === 'holistic';
                if ((isHolistic && this.targetLandmarks.length === 543) || (!isHolistic && this.targetLandmarks.length === 33)) {
                    data.manual_target_lms = this.targetLandmarks;
                }
            }

            const res = await api.processRefinement(this.videoId, data);
            
            if (res.status === 'started') {
                // Polling Loop
                const pollProgress = async () => {
                    const video = await api.getVideo(this.videoId);
                    const progress = video.refine_progress || 0;
                    const refineStatus = video.refine_status || 'idle';
                    
                    progressBar.style.width = `${progress}%`;
                    status.textContent = `⏳ Processing: ${progress}% (${refineStatus})`;
                    
                    if (refineStatus === 'idle' && progress === 100) {
                        status.textContent = '✅ Optimization Complete!';
                        setTimeout(() => {
                            progressContainer.classList.add('hidden');
                            btn.disabled = false;
                            btn.textContent = '🚀 Process & Save As New';
                            window.location.reload();
                        }, 1500);
                    } else {
                        setTimeout(pollProgress, 500);
                    }
                };
                pollProgress();
            } else {
                throw new Error(res.error || 'Failed to start process');
            }
        } catch (e) {
            status.textContent = '❌ Error: ' + e.message;
            btn.disabled = false;
            btn.textContent = '🚀 Retry Process';
        }
    }

    dispose() { this.running = false; }
}
