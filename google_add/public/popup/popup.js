const DOMAIN_LIST_ID = 'domain-list';
const INPUT_ID = 'domain-input';
const ADD_BTN_ID = 'add-btn';
const STORAGE_KEY = 'ignored_domains';

const statusEl = (() => {
  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;right:12px;bottom:12px;background:#0b74de;color:white;padding:6px 10px;border-radius:6px;box-shadow:0 4px 12px rgba(11,116,222,0.18);display:none;font-size:13px;z-index:9999';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(el));
  return {
	show: (txt) => { el.textContent = txt; el.style.display = 'block'; setTimeout(()=>el.style.display='none', 1800); }
  };
})();

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

	// allow Enter to add
	document.getElementById(INPUT_ID).addEventListener('keydown', (e) => {
		if (e.key === 'Enter') document.getElementById(ADD_BTN_ID).click();
	});
});

function renderList() {
	chrome.storage.local.get([STORAGE_KEY], (res) => {
		const list = res[STORAGE_KEY] || [];
		const container = document.getElementById(DOMAIN_LIST_ID);

		if (!container) return;

		if (list.length === 0) {
			container.innerHTML = '<div class="empty-state">Список порожній</div>';
			return;
		}

		container.innerHTML = '';
		list.forEach(domain => {
			const div = document.createElement('div');
			div.className = 'item';
			const span = document.createElement('span');
			span.textContent = domain;
			span.style.wordBreak = 'break-all';
			const btn = document.createElement('button');
			btn.className = 'remove-btn';
			btn.textContent = '✕';
			btn.title = 'Видалити';
			btn.onclick = () => removeDomain(domain);
			div.appendChild(span);
			div.appendChild(btn);
			container.appendChild(div);
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
				statusEl.show('Домен додано');
			});
		} else {
			statusEl.show('Домен уже в списку');
		}
	});
}

function removeDomain(domain) {
	chrome.storage.local.get([STORAGE_KEY], (res) => {
		const list = res[STORAGE_KEY] || [];
		const newList = list.filter(d => d !== domain);
		chrome.storage.local.set({ [STORAGE_KEY]: newList }, () => {
			renderList();
			statusEl.show('Домен видалено');
		});
	});
}
