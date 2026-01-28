<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';
import { api } from '@/composables/api';

const userStore = useUserStore();
const { isAuthenticated, user } = storeToRefs(userStore);
const { ensureAuth } = api();

// Приклад: функція, яка може бути викликана для ініціації SSO з кнопки
const handleLoginClick = async () => {
    try {
        await ensureAuth();
        console.log('Авторизація ініційована успішно.');
    } catch (e) {
        console.error('Не вдалося ініціювати вхід:', e);
    }
};
</script>

<template>
    <div class="home-container">
        <h1>Ласкаво просимо до User Activity Advisor!</h1>
        
        <div v-if="isAuthenticated" class="welcome-message">
            <p>Ви успішно авторизовані як **{{ user.email }}**.</p>
            <p>Перейдіть до <router-link to="/recommendations">Рекомендацій</router-link> або подивіться наші налаштування.</p>
        </div>

        <div v-else class="sso-guide">
            <h2>Для доступу до ваших даних потрібна авторизація</h2>
            <p>Наш сервіс використовує **Chrome Extension** для безпечного входу (SSO).</p>
            
            <ol>
                <li>Переконайтеся, що ви встановили наше розширення.</li>
                <li>Натисніть кнопку нижче, щоб **почати вхід** через розширення.</li>
            </ol>
            
            <button @click="handleLoginClick" class="login-button">
                Увійти через Chrome Extension
            </button>
        </div>
        
    </div>
</template>

<style scoped>
.home-container {
    max-width: 800px;
    margin: 40px auto;
    padding: 20px;
    text-align: center;
}
.sso-guide {
    margin-top: 30px;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: #f9f9f9;
}
.login-button {
    padding: 10px 20px;
    background-color: #42b883;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1.1em;
    margin-top: 15px;
}
</style>
