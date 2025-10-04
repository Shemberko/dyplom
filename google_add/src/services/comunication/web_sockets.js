class MessageService {
    connect() {}
    send(msg) {}
    onMessage(callback) {}
    disconnect() {}
}

// WebSocket реалізація
export default class WebSocketService extends MessageService {
    constructor(url) {
        super();
        this.url = url;
        this.socket = null;
        this.messageCallbacks = [];
    }

    connect() {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
        };

        this.socket.onmessage = (event) => {
            this.messageCallbacks.forEach(cb => cb(event.data));
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
        };
    }

    send(msg) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(msg);
        } else {
            console.warn('WebSocket is not open. Message not sent.');
        }
    }

    onMessage(cb) {
        this.messageCallbacks.push(cb);
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}
