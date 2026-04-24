import api from '../services/api.js';

export default class ResourcePage {
    async render() {
        return `
            <div class="page-container">
                <div class="upload-container">
                    <div class="upload-header">
                        <h2>Create New Project</h2>
                        <p>Upload a video to start your pose alignment project.</p>
                    </div>
                    <div class="upload-form">
                        <div class="input-group">
                            <label for="project-name">Project Name</label>
                            <input type="text" id="project-name" placeholder="e.g. Actor_A_Take_01">
                        </div>
                        <div class="input-group">
                            <label>Video File</label>
                            <div id="drop-zone" class="drop-zone">
                                <span class="drop-zone-icon">📁</span>
                                <span class="drop-zone-text">Click or drag & drop video file here</span>
                                <input type="file" id="video-upload" accept="video/*" style="display: none">
                                <div id="file-info" class="selected-file-info"></div>
                            </div>
                        </div>
                        <div class="upload-submit-container">
                            <button id="upload-btn">Create Project</button>
                        </div>
                    </div>
                </div>

                <div class="section-header">
                    <h2>Your Projects</h2>
                </div>

                <div id="video-list" class="video-list">
                    <p>Loading projects...</p>
                </div>
            </div>
        `;
    }

    async afterRender() {
        const uploadBtn = document.getElementById('upload-btn');
        const videoUpload = document.getElementById('video-upload');
        const projectNameInput = document.getElementById('project-name');
        const videoList = document.getElementById('video-list');
        const dropZone = document.getElementById('drop-zone');
        const fileInfo = document.getElementById('file-info');

        // Drag and drop handling
        dropZone.onclick = () => videoUpload.click();

        dropZone.ondragover = (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        };

        dropZone.ondragleave = () => {
            dropZone.classList.remove('dragover');
        };

        dropZone.ondrop = (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                videoUpload.files = e.dataTransfer.files;
                updateFileInfo();
            }
        };

        const updateFileInfo = () => {
            const file = videoUpload.files[0];
            if (file) {
                fileInfo.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
                if (!projectNameInput.value) {
                    projectNameInput.value = file.name.split('.')[0];
                }
            }
        };

        videoUpload.onchange = updateFileInfo;

        const loadVideos = async () => {
            const videos = await api.listVideos();
            if (videos.length === 0) {
                videoList.innerHTML = '<p>No projects found. Upload a video to get started.</p>';
                return;
            }
            videoList.innerHTML = videos.map(v => `
                <div class="project-card">
                    <div class="project-preview">
                        <img src="${v.thumbnail_url}" alt="Thumbnail">
                    </div>
                    <div class="project-info">
                        <h3>${v.name}</h3>
                        <div class="project-meta">
                            <span>${v.file_size}</span>
                        </div>
                        <div style="margin-bottom: 0.5rem;">
                            <span class="status-badge ${v.status}">${v.status}</span>
                        </div>
                        ${v.status === 'analyzing' ? `
                            <div class="progress-container">
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: ${v.progress}%"></div>
                                </div>
                                <div style="display:flex; justify-content:space-between; margin-top:4px">
                                    <small style="color:var(--text-muted)">Analyzing...</small>
                                    <small>${v.progress}%</small>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="project-actions">
                        <div class="secondary-actions">
                            <button class="btn-link" onclick="window.previewVideo('${v.url}')">
                                <span>👁️</span> Preview
                            </button>
                            
                            <button class="btn-link danger" onclick="window.deleteProject('${v.id}', '${v.name}')">
                                <span>🗑️</span> Delete Project
                            </button>

                            ${v.status === 'completed' ? `
                                <button class="btn-link" style="color: var(--text-muted)" onclick="window.deletePose('${v.id}')">
                                    <span>🧹</span> Clear Pose Data
                                </button>
                            ` : ''}
                        </div>

                        <div class="primary-actions">
                            ${v.status === 'completed' ? `
                                <button onclick="window.enterAnalysis('${v.id}')">Enter Analysis</button>
                            ` : `
                                ${v.status === 'analyzing' ? `
                                    <button disabled>Analyzing ${v.progress}%...</button>
                                ` : `
                                    <button class="btn-success" onclick="window.startPose('${v.id}')">Extract Pose</button>
                                `}
                            `}
                        </div>
                    </div>
                </div>
            `).join('');
        };

        window.previewVideo = (path) => {
            window.open(path, '_blank');
        };

        window.startPose = async (id) => {
            await api.startAnalysis(id);
            loadVideos();
        };

        window.deletePose = async (id) => {
            if (confirm('Are you sure you want to delete the pose data? This cannot be undone.')) {
                await api.deletePoseData(id);
                loadVideos();
            }
        };

        window.deleteProject = async (id, name) => {
            if (confirm(`Are you sure you want to delete project "${name}"? ALL data including video, pose, and refined clips will be permanently removed.`)) {
                await api.deleteVideo(id);
                loadVideos();
            }
        };

        window.enterAnalysis = (id) => {
            window.location.hash = '#/pose?id=' + id;
        };

        uploadBtn.onclick = async () => {
            const name = projectNameInput.value;
            const file = videoUpload.files[0];
            if (!name || !file) return alert('Enter project name and select a file');
            
            const formData = new FormData();
            formData.append('name', name);
            formData.append('file', file);
            
            uploadBtn.disabled = true;
            uploadBtn.innerText = 'Uploading...';
            
            try {
                await api.uploadVideo(formData);
                projectNameInput.value = '';
                videoUpload.value = '';
                loadVideos();
            } catch (e) {
                alert('Upload failed');
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.innerText = 'Upload & Create Project';
            }
        };

        loadVideos();
    }
}
