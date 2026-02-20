const i="tracking_enabled",a=document.createElement("style");a.textContent=`
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
`;function n(){document.head.appendChild(a),chrome.storage.local.get([i],e=>{const t=e[i]!==!1;c(t)})}function c(e){let t=document.getElementById("my-ext-indicator");t||(t=document.createElement("div"),t.id="my-ext-indicator",t.className="my-ext-indicator",document.body.appendChild(t)),t.className=e?"my-ext-indicator my-ext-active":"my-ext-indicator my-ext-inactive",t.title=e?"Запис активний (Натисніть, щоб вимкнути)":"Запис вимкнено (Натисніть, щоб увімкнути)",t.onclick=r=>{r.preventDefault();const o=!e;chrome.storage.local.set({[i]:o},()=>{console.log(`Трекінг ${o?"увімкнено":"вимкнено"}`),c(o)})}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",n):n();const d="http://localhost:5173";window.addEventListener("message",e=>{e.origin!==d||!e.data||e.data.action!=="REQUEST_SSO_FROM_FRONTEND"||chrome.runtime.sendMessage({action:"REQUEST_SSO_TOKEN"},t=>{chrome.runtime.lastError&&(t={error:chrome.runtime.lastError.message}),window.postMessage({action:"SSO_RESPONSE_TO_FRONTEND",...t},e.origin)})});
