import api from '../services/api.js';

export default class RefinementPage {
    async render() {
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
        this.videoId = urlParams.get('id');
        this.video = await api.getVideo(this.videoId);

        return `
            <div class="page-container">
                <h1>Fine Refinement & Alignment</h1>
                <div class="video-container">
                    <video id="video-player" controls width="100%" src="${this.video.url}"></video>
                </div>
                <div class="refinement-controls">
                    <button id="loop-btn">Toggle Loop Playback</button>
                    <button id="optimize-btn">Optimize with RIFE & MLS</button>
                    <button id="export-btn">Final Export</button>
                </div>
                <div id="refinement-status"></div>
            </div>
        `;
    }

    async afterRender() {
        const videoPlayer = document.getElementById('video-player');
        const loopBtn = document.getElementById('loop-btn');
        const optimizeBtn = document.getElementById('optimize-btn');

        let isLooping = false;
        
        loopBtn.onclick = () => {
            isLooping = !isLooping;
            videoPlayer.loop = isLooping;
            loopBtn.innerText = isLooping ? 'Stop Loop' : 'Toggle Loop Playback';
        };

        optimizeBtn.onclick = () => {
            alert('Optimization logic (RIFE/MLS) will be called here');
            // This would call the backend service we stubbed earlier
        };
    }
}
