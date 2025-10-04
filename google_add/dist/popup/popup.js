chrome.storage.local.get("activityLog", (data) => {
  const log = data.activityLog || [];
  const adviceEl = document.getElementById("advice");
  console.log("[popup] Activity log:", log);

  if (log.length > 20) {
    adviceEl.textContent = "Ви були дуже активні. Можливо, час на каву?";
  } else if (log.length > 5) {
    adviceEl.textContent = "Хороший темп! Продовжуйте!";
  } else {
    adviceEl.textContent = "Схоже, ви тільки почали. Бажаю продуктивного дня!";
  }
});
