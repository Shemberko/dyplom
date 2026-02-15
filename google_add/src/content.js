const STORAGE_KEY = 'tracking_enabled';

const style = document.createElement('style');
style.textContent = `
  .my-ext-container {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 2147483647; /* Максимальний z-index */
    display: flex;
    align-items: center;
    font-family: Arial, sans-serif;
    background: rgba(0, 0, 0, 0.1);
    padding: 2px;
    border-bottom-right-radius: 5px;
    transition: opacity 0.3s;
  }

  .my-ext-container:hover {
    background: rgba(0, 0, 0, 0.8);
  }

  .my-ext-dot {
    width: 7px;
    height: 7px;
    background-color: red;
    border-radius: 50%;
    margin: 5px;
    animation: my-ext-blink 1s infinite;
  }

  .my-ext-toggle-btn {
    display: none;
    font-size: 10px;
    color: white;
    background: #333;
    border: 1px solid #555;
    cursor: pointer;
    margin-left: 5px;
    padding: 2px 5px;
    border-radius: 3px;
  }

  .my-ext-container:hover .my-ext-toggle-btn {
    display: block;
  }

  @keyframes my-ext-blink {
    0% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 1; }
  }
`;

function init() {
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    const isTracking = result[STORAGE_KEY] !== false; 
    
    if (isTracking) {
      createOverlay();
    } else {
      createEnableButton();
    }
  });
}

function createOverlay() {
  removeOverlay();

  document.head.appendChild(style);

  const container = document.createElement('div');
  container.className = 'my-ext-container';
  container.id = 'my-ext-ui';

  const dot = document.createElement('div');
  dot.className = 'my-ext-dot';
  dot.title = 'Запис даних активний';

  const btn = document.createElement('button');
  btn.className = 'my-ext-toggle-btn';
  btn.innerText = 'Вимкнути';
  
  btn.onclick = () => {
    chrome.storage.local.set({ [STORAGE_KEY]: false }, () => {
      removeOverlay();
      createEnableButton();
      console.log('Трекінг вимкнено користувачем (tracking_enabled = false)');
    });
  };

  container.appendChild(dot);
  container.appendChild(btn);
  document.body.appendChild(container);
}

function createEnableButton() {
  if (document.getElementById('my-ext-enable-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'my-ext-enable-btn';
  btn.innerText = '🔴';
  btn.title = 'Увімкнути запис даних';
  btn.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    z-index: 2147483647;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 10px;
    opacity: 0.3;
  `;
  
  btn.onclick = () => {
    // Встановлюємо прапорець tracking_enabled в true
    chrome.storage.local.set({ [STORAGE_KEY]: true }, () => {
      btn.remove();
      createOverlay(); // Повертаємо крапку
      console.log('Трекінг увімкнено (tracking_enabled = true)');
    });
  };

  document.body.appendChild(btn);
}

function removeOverlay() {
  const existing = document.getElementById('my-ext-ui');
  if (existing) existing.remove();
}

// Запуск
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}


const FRONTEND_ORIGIN = 'http://localhost:5173'; 

window.addEventListener("message", (event) => {

     if (event.origin !== FRONTEND_ORIGIN) {
        console.warn(`Content Script: Повідомлення проігноровано. Очікується: ${FRONTEND_ORIGIN}, Отримано: ${event.origin}`);
        return;
    }
    
    if (event.origin !== FRONTEND_ORIGIN || !event.data || event.data.action !== "REQUEST_SSO_FROM_FRONTEND") {
        return;
    }
    console.log("Content Script: Отримано запит на SSO токен від фронтенду.");
    chrome.runtime.sendMessage({ action: "REQUEST_SSO_TOKEN" }, (response) => {
        
        if (chrome.runtime.lastError) {
            console.error("Content Script Error:", chrome.runtime.lastError.message);
            response = { error: chrome.runtime.lastError.message || "Помилка зв'язку з Background Worker." };
        }

        console.log("Content Script: Надсилаємо відповідь SSO токена назад до фронтенду.", response);
        window.postMessage({ 
            action: "SSO_RESPONSE_TO_FRONTEND", 
            ...response 
        }, event.origin); 
    });
});