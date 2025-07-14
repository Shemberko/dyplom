const overlay = document.createElement('div');
overlay.style.position = 'fixed';
overlay.style.top = '0';
overlay.style.left = '0';
overlay.style.width = '100%';
overlay.style.height = '100%';
overlay.style.background = 'rgba(0,0,0,0)';
overlay.style.zIndex = '999999';
overlay.style.pointerEvents = 'none';

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
    event.preventDefault();
    console.log("[AI trigger] Комбінація Shift + Tab + Click активована");
  }
  else {
    console.log("[AI trigger] Клік без Shift + Tab, ігноруємо");
  }
});

document.body.appendChild(overlay);
