/* SPA router and page controller */
const App = {
    _currentPage: null,

    pages: {
        dashboard: DashboardPage,
        topics: TopicsPage,
        rules: RulesPage,
        messages: MessagesPage,
        live: LivePage,
        settings: SettingsPage,
    },

    init() {
        window.addEventListener('hashchange', () => this.route());
        this.route();

        // Periodically check system health for status indicator
        this._healthCheck();
        setInterval(() => this._healthCheck(), 30000);
    },

    route() {
        const hash = location.hash.replace('#/', '').replace('#', '') || 'dashboard';
        const pageName = hash.split('/')[0] || 'dashboard';

        // Destroy previous page if needed
        if (this._currentPage && this._currentPage.destroy) {
            this._currentPage.destroy();
        }

        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === pageName);
        });

        // Render page
        const page = this.pages[pageName];
        if (page) {
            this._currentPage = page;
            page.render();
        } else {
            document.getElementById('content').innerHTML = `
                <div class="empty-state">
                    <h3>Page not found</h3>
                    <p><a href="#/">Go to dashboard</a></p>
                </div>
            `;
        }
    },

    async _healthCheck() {
        try {
            const health = await API.get('/api/dashboard/system-health');
            const statusEl = document.getElementById('connection-status');
            if (!statusEl) return;

            if (health.mqtt_connected) {
                statusEl.className = 'status-indicator status-connected';
                statusEl.querySelector('.status-text').textContent = 'MQTT Connected';
            } else if (health.alert_service === 'running') {
                statusEl.className = 'status-indicator status-disconnected';
                statusEl.querySelector('.status-text').textContent = 'MQTT Disconnected';
            } else {
                statusEl.className = 'status-indicator status-disconnected';
                statusEl.querySelector('.status-text').textContent = 'Service Stopped';
            }
        } catch {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.className = 'status-indicator status-disconnected';
                statusEl.querySelector('.status-text').textContent = 'API Unreachable';
            }
        }
    }
};

// Start the app
document.addEventListener('DOMContentLoaded', () => App.init());
