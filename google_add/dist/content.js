const o="tracking_enabled",r=document.createElement("style");r.textContent=`
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
`;function i(){chrome.storage.local.get([o],e=>{e[o]!==!1?c():d()})}function c(){a(),document.head.appendChild(r);const e=document.createElement("div");e.className="my-ext-container",e.id="my-ext-ui";const t=document.createElement("div");t.className="my-ext-dot",t.title="Запис даних активний";const n=document.createElement("button");n.className="my-ext-toggle-btn",n.innerText="Вимкнути",n.onclick=()=>{chrome.storage.local.set({[o]:!1},()=>{a(),d(),console.log("Трекінг вимкнено користувачем (tracking_enabled = false)")})},e.appendChild(t),e.appendChild(n),document.body.appendChild(e)}function d(){if(document.getElementById("my-ext-enable-btn"))return;const e=document.createElement("button");e.id="my-ext-enable-btn",e.innerText="🔴",e.title="Увімкнути запис даних",e.style.cssText=`
    position: fixed;
    top: 0;
    left: 0;
    z-index: 2147483647;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 10px;
    opacity: 0.3;
  `,e.onclick=()=>{chrome.storage.local.set({[o]:!0},()=>{e.remove(),c(),console.log("Трекінг увімкнено (tracking_enabled = true)")})},document.body.appendChild(e)}function a(){const e=document.getElementById("my-ext-ui");e&&e.remove()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",i):i();
