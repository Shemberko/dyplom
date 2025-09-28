const overlay = document.createElement('div');
overlay.style.position = 'fixed';
overlay.style.top = '0';
overlay.style.left = '0';
overlay.style.width = '100%';
overlay.style.height = '100%';
overlay.style.background = 'rgba(0,0,0,0)';
overlay.style.zIndex = '999999';
overlay.style.pointerEvents = 'none';

let saved_info
let keysPressed = new Set();

window.addEventListener('keydown', function(event) {
  keysPressed.add(event.key);
});

window.addEventListener('keyup', function(event) {
  keysPressed.delete(event.key);
});

window.addEventListener('click', function(event) {
  const isShiftTabClick =
    keysPressed.has('Shift') &&
    keysPressed.has("\\");

  if (isShiftTabClick) {
    const target = event.target;
    const info = {
      classList :Array.from(target.classList || []),
      name: target.name || null,
      value: target.value || null,
      textContent: (target.textContent || '').slice(0, 100),
      ariaLabel: target.getAttribute ? target.getAttribute('aria-label') : null,
      role: target.getAttribute ? target.getAttribute('role') : null,
      timestamp: Date.now(),
      pageUrl: window.location.href,
      outerHTML: target.outerHTML || null,
      innerHTML: target.innerHTML || null,
    };
    if (info.styles) {
      info.styles = Object.fromEntries(Array.from(info.styles).map(key => [key, info.styles.getPropertyValue(key)]));
    }

    chrome.storage.local.get(["ExplenationRequests"], (result) => {
      const log = result.ExplenationRequests || [];
      // Avoid duplicates by checking if a similar entry already exists
      const isDuplicate = log.some(entry =>
      entry.outerHTML === info.outerHTML &&
      entry.innerHTML === info.innerHTML &&
      entry.pageUrl === info.pageUrl &&
      entry.timestamp > Date.now() - 60000
      );
      if (!isDuplicate) {
      log.push(info);
      chrome.storage.local.set({ ExplenationRequests: log });
      localStorage.setItem("ExplenationRequests", JSON.stringify(log));
      console.log("[background]Activity logged:", info);
      } else {
      console.log("[background]Duplicate activity ignored:", info);
      }
    });
    console.log("[AI trigger] Комбінація Shift + Tab + Click активована");
  }
  else {
    console.log("[AI trigger] Клік без Shift + Tab, ігноруємо");
  }

});

document.body.appendChild(overlay);
