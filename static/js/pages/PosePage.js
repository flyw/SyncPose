import api from '../services/api.js';

export default class PosePage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.video = await api.getVideo(this.videoId);
        this.keyframes = await api.getKeyframes(this.videoId) || [];
        this.slices = await api.getSlices(this.videoId) || [];

        return `
            <div class="page-container dashboard-layout">
                <div class="dashboard-header">
                    <h1>Dashboard: ${this.video.name}</h1>
                    <p class="text-muted">Summary of analysis and editing progress</p>
                </div>

                <div class="dashboard-grid">
                    <!-- Pose Status -->
                    <div class="stats-card">
                        <div class="stats-icon">🦴</div>
                        <div class="stats-content">
                            <h3>Pose Data</h3>
                            <p class="status-badge completed">Ready</p>
                            <p class="small text-muted">${this.video.total_frames} frames processed</p>
                        </div>
                    </div>

                    <!-- Keyframe Status -->
                    <div class="stats-card">
                        <div class="stats-icon">⭐</div>
                        <div class="stats-content">
                            <h3>Keyframe</h3>
                            <p class="stats-number">${this.keyframes.length}</p>
                            <p class="small text-muted">${this.keyframes.length > 0 ? 'Selection completed' : 'Not set'}</p>
                        </div>
                        <button class="btn-link" onclick="window.location.hash='#/keyframe?id=${this.videoId}'">Manage</button>
                    </div>

                    <!-- Slices Status -->
                    <div class="stats-card">
                        <div class="stats-icon">🎞️</div>
                        <div class="stats-content">
                            <h3>Video Slices</h3>
                            <p class="stats-number">${this.slices.length}</p>
                            <p class="small text-muted">${this.slices.length} segments defined</p>
                        </div>
                        <button class="btn-link" onclick="window.location.hash='#/slicing?id=${this.videoId}'">Manage</button>
                    </div>
                </div>

                <div class="dashboard-details">
                    <div class="detail-section">
                        <h3>Saved Keyframe</h3>
                        <div class="keyframe-dashboard-grid">
                            ${this.keyframes.length > 0 ? this.keyframes.map(k => `
                                <div class="keyframe-card-mini" style="position: relative;">
                                    <img src="${k.image_url}" alt="Frame ${k.frame}">
                                    <span>Frame ${k.frame}</span>
                                    <button class="btn-delete-keyframe" 
                                            onclick="window.deleteKeyframe(event, ${k.frame})"
                                            style="position: absolute; top: 4px; right: 4px; background: rgba(239, 68, 68, 0.8); color: white; border: none; border-radius: 4px; padding: 2px 6px; font-size: 10px; cursor: pointer;">✕</button>
                                </div>
                            `).join('') : '<p class="text-muted">No keyframes saved yet.</p>'}
                        </div>
                    </div>

                    <div class="detail-section">
                        <h3>Action List (Slices)</h3>
                        ${this.slices.length > 0 ? `
                            <ul class="action-list">
                                ${this.slices.map(s => `
                                    <li>
                                        <span class="action-name">${s.name}</span>
                                        <span class="action-range">${s.start_frame} - ${s.end_frame}</span>
                                    </li>
                                `).join('')}
                            </ul>
                        ` : '<p class="text-muted">No slices created yet.</p>'}
                    </div>
                </div>
            </div>
        `;
    }

    async afterRender() {
        window.deleteKeyframe = async (event, frame) => {
            event.stopPropagation();
            if (confirm(`Are you sure you want to delete Keyframe ${frame}?`)) {
                // Filter out the keyframe (since we only allow one now, this will effectively empty the list)
                this.keyframes = this.keyframes.filter(k => k.frame !== frame);
                await api.saveKeyframes(this.videoId, this.keyframes);
                
                // Re-render the entire component to update the dashboard
                const container = document.getElementById('app');
                container.innerHTML = await this.render();
                await this.afterRender();
            }
        };
    }
}
