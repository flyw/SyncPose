export default class Router {
    constructor(routes, container) {
        this.routes = routes;
        this.container = container;
        this.currentPage = null;
    }

    init() {
        window.addEventListener('hashchange', () => this.route());
        this.route();
    }

    async route() {
        if (this.currentPage && this.currentPage.dispose) {
            this.currentPage.dispose();
        }

        const hash = window.location.hash;
        const path = hash.split('?')[0].slice(1) || '/';
        const urlParams = new URLSearchParams(hash.split('?')[1]);
        const videoId = urlParams.get('id');

        this.updateNav(path, videoId);

        const PageClass = this.routes[path] || this.routes['/'];
        this.currentPage = new PageClass();
        this.container.innerHTML = await this.currentPage.render();
        
        if (this.currentPage.afterRender) {
            await this.currentPage.afterRender();
        }
    }

    updateNav(path, videoId) {
        const projectNavs = document.querySelectorAll('.project-nav');
        const activeProjectLabel = document.getElementById('active-project-name');
        const backBtn = document.getElementById('nav-back-btn');

        if (path === '/' || !videoId) {
            projectNavs.forEach(el => el.classList.add('hidden'));
            backBtn.classList.add('hidden');
            activeProjectLabel.textContent = '';
        } else {
            projectNavs.forEach(el => {
                el.classList.remove('hidden');
                const a = el.querySelector('a');
                const baseHash = a.getAttribute('href').split('?')[0];
                a.setAttribute('href', `${baseHash}?id=${videoId}`);
            });
            backBtn.classList.remove('hidden');
            activeProjectLabel.textContent = videoId;
        }
    }
}
