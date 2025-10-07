export default class WebSocketService {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.reconnectInterval = 3000;
        this.shouldReconnect = true;
    }

    connect() {
        console.log("[WebSocket] Connecting to", this.url);
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log("[WebSocket] Connected");
        };

        this.socket.onmessage = (event) => {
            console.log("[WebSocket] Message:", event.data);
        };

        this.socket.onerror = (error) => {
            console.error("[WebSocket] Error:", error);
        };

        this.socket.onclose = (event) => {
            console.warn("[WebSocket] Disconnected:", event.reason || "no reason");

            if (this.shouldReconnect) {
                console.log(`[WebSocket] Reconnecting in ${this.reconnectInterval / 1000}s...`);
                setTimeout(() => this.connect(), this.reconnectInterval);
            }
        };
    }

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(data);
        } else {
            console.warn("[WebSocket] Not connected, message skipped:", data);
        }
    }

    close() {
        this.shouldReconnect = false;
        if (this.socket) {
            this.socket.close();
        }
    }
}
