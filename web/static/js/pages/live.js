/* Live MQTT message feed via WebSocket */
const LivePage = {
    _ws: null,
    _paused: false,
    _messages: [],
    _maxMessages: 500,
    _topicFilter: '',

    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Live Feed</h2>
                <div class="flex gap-8">
                    <input type="text" class="form-input" id="live-topic-filter"
                           placeholder="Filter by topic..." style="width:200px;"
                           oninput="LivePage._topicFilter = this.value.trim()">
                    <button class="btn btn-sm" id="live-pause-btn" onclick="LivePage.togglePause()">Pause</button>
                    <button class="btn btn-sm" onclick="LivePage.clear()">Clear</button>
                </div>
            </div>
            <div id="live-status" style="margin-bottom: 12px; font-size: 13px; color: var(--color-text-muted);">
                Connecting...
            </div>
            <div class="live-feed" id="live-feed">
                <div class="empty-state">
                    <div class="empty-state-icon">&#9679;</div>
                    <h3>Waiting for messages...</h3>
                    <p>Messages will stream here in real time.</p>
                </div>
            </div>
        `;
        this._messages = [];
        this._paused = false;
        this._connect();
    },

    _connect() {
        if (this._ws) {
            this._ws.close();
        }

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/api/messages/live`;
        this._ws = new WebSocket(url);

        this._ws.onopen = () => {
            const status = document.getElementById('live-status');
            if (status) {
                status.innerHTML = '<span class="text-success">Connected</span> — streaming messages';
            }
        };

        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._onMessage(msg);
            } catch (e) {
                // Ignore parse errors
            }
        };

        this._ws.onclose = () => {
            const status = document.getElementById('live-status');
            if (status) {
                status.innerHTML = '<span class="text-danger">Disconnected</span> — reconnecting in 3s...';
            }
            setTimeout(() => {
                if (document.getElementById('live-feed')) {
                    this._connect();
                }
            }, 3000);
        };

        this._ws.onerror = () => {
            // onclose will fire after this
        };
    },

    _onMessage(msg) {
        // Apply topic filter
        if (this._topicFilter && !msg.topic.includes(this._topicFilter)) {
            return;
        }

        this._messages.unshift(msg);
        if (this._messages.length > this._maxMessages) {
            this._messages.pop();
        }

        if (!this._paused) {
            this._renderMessage(msg);
        }
    },

    _renderMessage(msg) {
        const feed = document.getElementById('live-feed');
        if (!feed) return;

        // Remove empty state if present
        const empty = feed.querySelector('.empty-state');
        if (empty) empty.remove();

        const now = new Date();
        const time = now.toLocaleTimeString();

        const el = document.createElement('div');
        el.className = 'live-message';
        el.innerHTML = `
            <span class="live-time">${time}</span>
            <span class="live-topic">${API.escapeHtml(msg.topic)}</span>
            <span class="live-payload">${API.escapeHtml(msg.payload)}</span>
        `;

        feed.insertBefore(el, feed.firstChild);

        // Limit DOM nodes
        while (feed.children.length > this._maxMessages) {
            feed.removeChild(feed.lastChild);
        }
    },

    togglePause() {
        this._paused = !this._paused;
        const btn = document.getElementById('live-pause-btn');
        if (btn) {
            btn.textContent = this._paused ? 'Resume' : 'Pause';
            btn.classList.toggle('btn-primary', this._paused);
        }

        // If resuming, render any buffered messages
        if (!this._paused) {
            const feed = document.getElementById('live-feed');
            if (feed) feed.innerHTML = '';
            this._messages.forEach(msg => this._renderMessage(msg));
        }
    },

    clear() {
        this._messages = [];
        const feed = document.getElementById('live-feed');
        if (feed) {
            feed.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9679;</div>
                    <h3>Waiting for messages...</h3>
                    <p>Messages will stream here in real time.</p>
                </div>
            `;
        }
    },

    destroy() {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
    }
};
