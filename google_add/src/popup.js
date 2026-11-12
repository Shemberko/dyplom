const DOMAIN_LIST_ID = 'domain-list';
const INPUT_ID = 'domain-input';
const ADD_BTN_ID = 'add-btn';
const STORAGE_KEY = 'ignored_domains';

document.addEventListener('DOMContentLoaded', () => {
    renderList();

    document.getElementById(ADD_BTN_ID).addEventListener('click', () => {
        const input = document.getElementById(INPUT_ID);
        const domain = input.value.trim().toLowerCase();
        
        if (domain) {
            addDomain(domain);
            input.value = '';
        }
    });
});

function showNotification(message) {
    const notif = document.getElementById('notification');
    notif.textContent = message;
    notif.style.display = 'block';
    
    // Скидаємо анімацію
    notif.style.animation = 'none';
    notif.offsetHeight; // trigger reflow
    notif.style.animation = 'fadeInOut 2.5s ease-in-out forwards';
    
    setTimeout(() => {
        notif.style.display = 'none';
    }, 2500);
}

function renderList() {
    chrome.storage.local.get([STORAGE_KEY], (res) => {
        const list = res[STORAGE_KEY] || [];
        const container = document.getElementById(DOMAIN_LIST_ID);
        
        if (list.length === 0) {
            container.innerHTML = '<div class="empty-state">Список порожній</div>';
            return;
        }

        container.innerHTML = '';
        list.forEach(domain => {
            const div = document.createElement('div');
            div.className = 'item';
            div.innerHTML = `
                <span>${domain}</span>
                <button class="remove-btn" data-domain="${domain}">✕</button>
            `;
            container.appendChild(div);
        });

        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.onclick = () => removeDomain(btn.dataset.domain);
        });
    });
}

function addDomain(domain) {
    chrome.storage.local.get([STORAGE_KEY], (res) => {
        const list = res[STORAGE_KEY] || [];
        if (!list.includes(domain)) {
            list.push(domain);
            chrome.storage.local.set({ [STORAGE_KEY]: list }, () => {
                renderList();
                showNotification(`Домен ${domain} додано`);
            });
        } else {
            showNotification(`Домен ${domain} вже у списку`);
        }
    });
}

function removeDomain(domain) {
    chrome.storage.local.get([STORAGE_KEY], (res) => {
        const list = res[STORAGE_KEY] || [];
        const newList = list.filter(d => d !== domain);
        chrome.storage.local.set({ [STORAGE_KEY]: newList }, renderList);
    });
}