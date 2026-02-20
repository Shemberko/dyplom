const STORAGE_KEY = 'tracking_enabled';

const style = document.createElement('style');
style.textContent = `
  .my-ext-indicator {
    position: fixed;
    top: 5px;
    left: 5px;
    z-index: 2147483647;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    cursor: pointer;
    transition: opacity 0.3s, background-color 0.3s;
  }

  /* Стан: Увімкнено (Червоне з анімацією) */
  .my-ext-active {
    background-color: #ff0000;
    box-shadow: 0 0 3px #ff0000;
    animation: my-ext-blink 1.2s infinite;
  }

  /* Стан: Вимкнено (Сіре напівпрозоре) */
  .my-ext-inactive {
    background-color: #555;
    opacity: 0.4;
  }

  .my-ext-inactive:hover {
    opacity: 0.8;
  }

  @keyframes my-ext-blink {
    0% { opacity: 1; }
    50% { opacity: 0.3; }
    100% { opacity: 1; }
  }
`;

function init() {
  document.head.appendChild(style);
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    const isTracking = result[STORAGE_KEY] !== false;
    renderIndicator(isTracking);
  });
}

function renderIndicator(isActive) {
  let el = document.getElementById('my-ext-indicator');
  
  if (!el) {
    el = document.createElement('div');
    el.id = 'my-ext-indicator';
    el.className = 'my-ext-indicator';
    document.body.appendChild(el);
  }

  el.className = isActive ? 'my-ext-indicator my-ext-active' : 'my-ext-indicator my-ext-inactive';
  el.title = isActive ? 'Запис активний (Натисніть, щоб вимкнути)' : 'Запис вимкнено (Натисніть, щоб увімкнути)';

  el.onclick = (e) => {
    e.preventDefault();
    const newState = !isActive;
    chrome.storage.local.set({ [STORAGE_KEY]: newState }, () => {
      console.log(`Трекінг ${newState ? 'увімкнено' : 'вимкнено'}`);
      renderIndicator(newState);
    });
  };
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

const FRONTEND_ORIGIN = 'http://localhost:5173'; 

window.addEventListener("message", (event) => {
    if (event.origin !== FRONTEND_ORIGIN || !event.data || event.data.action !== "REQUEST_SSO_FROM_FRONTEND") {
        return;
    }
    
    chrome.runtime.sendMessage({ action: "REQUEST_SSO_TOKEN" }, (response) => {
        if (chrome.runtime.lastError) {
            response = { error: chrome.runtime.lastError.message };
        }
        window.postMessage({ 
            action: "SSO_RESPONSE_TO_FRONTEND", 
            ...response 
        }, event.origin); 
    });
});