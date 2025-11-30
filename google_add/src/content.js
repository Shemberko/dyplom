// src/content.js

// Ключ для збереження стану. Інші скрипти мають перевіряти цей ключ перед записом даних.
const STORAGE_KEY = 'tracking_enabled';

// Створення стилів для наших елементів
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

  /* Кнопка спочатку прихована і з'являється при наведенні на контейнер (або крапку) */
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

// Функція ініціалізації
function init() {
  // Перевіряємо стан у сховищі при завантаженні сторінки
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення не встановлено (undefined) або true -> ввімкнено
    const isTracking = result[STORAGE_KEY] !== false; 
    
    if (isTracking) {
      createOverlay();
    } else {
      createEnableButton(); // Якщо вимкнено, показуємо кнопку для увімкнення
    }
  });
}

function createOverlay() {
  // Видаляємо, якщо вже існує, щоб не дублювати
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
  
  // Логіка кнопки вимкнення (Stop Recording)
  btn.onclick = () => {
    // Встановлюємо прапорець tracking_enabled в false
    chrome.storage.local.set({ [STORAGE_KEY]: false }, () => {
      removeOverlay();
      createEnableButton(); // Ховаємо крапку, показуємо кнопку відновлення
      console.log('Трекінг вимкнено користувачем (tracking_enabled = false)');
    });
  };

  container.appendChild(dot);
  container.appendChild(btn);
  document.body.appendChild(container);
}

// Функція для створення кнопки відновлення (Start Recording)
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