const API_BASE = '/api/v1';

export default {
    async listVideos() {
        const res = await fetch(`${API_BASE}/resources/`);
        return res.json();
    },
    async uploadVideo(formData) {
        const res = await fetch(`${API_BASE}/resources/upload`, {
            method: 'POST',
            body: formData
        });
        return res.json();
    },
    async getVideo(id) {
        const res = await fetch(`${API_BASE}/resources/${id}`);
        return res.json();
    },
    async deleteVideo(id) {
        const res = await fetch(`${API_BASE}/resources/${id}`, {
            method: 'DELETE'
        });
        return res.json();
    },
    async startAnalysis(id) {
        const res = await fetch(`${API_BASE}/resources/${id}/analyze`, {
            method: 'POST'
        });
        return res.json();
    },
    async deletePoseData(id) {
        const res = await fetch(`${API_BASE}/resources/${id}/pose`, {
            method: 'DELETE'
        });
        return res.json();
    },
    async getStatus(id) {
        const res = await fetch(`${API_BASE}/resources/${id}`);
        return res.json();
    },
    async saveKeyframes(id, keyframes) {
        const res = await fetch(`${API_BASE}/keyframes/${id}/keyframes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(keyframes)
        });
        return res.json();
    },
    async getKeyframes(id) {
        const res = await fetch(`${API_BASE}/keyframes/${id}/keyframes`);
        return res.json();
    },
    async saveKeyframeImage(id, frameIndex) {
        const res = await fetch(`${API_BASE}/keyframes/${id}/save_frame/${frameIndex}`, {
            method: 'POST'
        });
        return res.json();
    },
    async saveSlices(id, slices) {
        const res = await fetch(`${API_BASE}/slicing/${id}/slices`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(slices)
        });
        return res.json();
    },
    async getSlices(id) {
        const res = await fetch(`${API_BASE}/slicing/${id}/slices`);
        return res.json();
    },
    async exportSlice(id, data) {
        const res = await fetch(`${API_BASE}/slicing/${id}/export`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return res.json();
    },
    async getClips(id) {
        const res = await fetch(`${API_BASE}/refinement/${id}/clips`);
        return res.json();
    },
    async processRefinement(id, data) {
        const res = await fetch(`${API_BASE}/refinement/${id}/process`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return res.json();
    },
    async deleteClip(id, filename) {
        const res = await fetch(`${API_BASE}/refinement/${id}/clips/${filename}`, {
            method: 'DELETE'
        });
        return res.json();
    },
    async updateClipRemarks(id, filename, remarks) {
        const res = await fetch(`${API_BASE}/refinement/${id}/clips/${filename}/remarks`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({remarks: remarks})
        });
        return res.json();
    },
    async previewMls(id, data) {
        const res = await fetch(`${API_BASE}/refinement/${id}/preview_mls`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return res.json();
    },
    async getAnalysis(id, threshold = 92.0) {
        const res = await fetch(`${API_BASE}/analysis/${id}?threshold=${threshold}`);
        return res.json();
    },
    async reSync(id, frameIndex, threshold = 92.0) {
        const res = await fetch(`${API_BASE}/analysis/${id}/re-sync`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({frame_index: frameIndex, threshold: threshold})
        });
        return res.json();
    }
};
