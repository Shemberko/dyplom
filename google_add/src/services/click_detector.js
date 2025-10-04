import WebSocketService from './comunication/web_sockets.js';
let tabId;

let keysPressed = new Set();

window.addEventListener('keydown', function(event) {
    keysPressed.add(event.key);
});

window.addEventListener('keyup', function(event) {
    keysPressed.delete(event.key);
});



const wsService = new WebSocketService("ws://localhost:8000/ws");
wsService.connect();

document.addEventListener("click", function(event) {
    const clickInfo = {
        element: event.target.tagName,
        tabId: tabId,
        give_info: keysPressed.has('Shift'),
        url: window.location.href,
        x: event.clientX,
        y: event.clientY,
        time: new Date().toISOString()
    };
    console.log("[click_detector] Click info sent:", clickInfo);

    wsService.send(JSON.stringify({ click: clickInfo }));
});