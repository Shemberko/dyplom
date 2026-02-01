import { createApp } from 'vue';
import { createPinia } from 'pinia'; // Якщо ви використовуєте Pinia
import App from './App.vue';
import router from '../router/index'; // <-- Імпорт створеного роутера
import './style.css'; // Ваш головний файл стилів
const app = createApp(App);
app.use(createPinia()); // Встановлення Pinia
app.use(router); // <-- Підключення Vue Router
app.mount('#app');
