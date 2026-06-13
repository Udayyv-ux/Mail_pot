/**
 * Simple SPA Router
 */
const router = {
    routes: {},
    currentRoute: null,

    init() {
        // Register nav clicks
        document.querySelectorAll('[data-route]').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigate(el.getAttribute('data-route'));
            });
        });

        // Listen for back button
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.route) {
                this.showPage(e.state.route);
            }
        });

        // Parse initial route from hash or default to first
        const hash = window.location.hash.replace('#', '');
        if (hash) {
            this.navigate(hash, true);
        } else {
            const firstNav = document.querySelector('[data-route]');
            if (firstNav) this.navigate(firstNav.getAttribute('data-route'), true);
        }
    },

    on(route, callback) {
        this.routes[route] = callback;
    },

    navigate(route, replace = false) {
        if (this.currentRoute === route) return;
        
        if (replace) {
            window.history.replaceState({route}, '', `#${route}`);
        } else {
            window.history.pushState({route}, '', `#${route}`);
        }
        
        this.showPage(route);
    },

    showPage(route) {
        this.currentRoute = route;
        
        // Hide all pages
        document.querySelectorAll('.page-section').forEach(el => {
            el.classList.remove('active');
        });
        
        // Show target page
        const target = document.getElementById(`page-${route}`);
        if (target) target.classList.add('active');
        
        // Update nav active state
        document.querySelectorAll('[data-route]').forEach(el => {
            if (el.getAttribute('data-route') === route) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
        
        // Call handler
        if (this.routes[route]) {
            this.routes[route]();
        }
    }
};
