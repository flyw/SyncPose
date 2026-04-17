import Router from './router.js';
import ResourcePage from './pages/ResourcePage.js';
import PosePage from './pages/PosePage.js';
import KeyframePage from './pages/KeyframePage.js';
import SlicingPage from './pages/SlicingPage.js';
import RefinementPage from './pages/RefinementPage.js';

const routes = {
    '/': ResourcePage,
    '/pose': PosePage,
    '/keyframe': KeyframePage,
    '/slicing': SlicingPage,
    '/refinement': RefinementPage
};

const router = new Router(routes, document.getElementById('app'));
router.init();
