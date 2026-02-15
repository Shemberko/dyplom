// src/router/index.ts

import { createRouter, createWebHistory } from 'vue-router';
const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/pages/Home.vue') },
  { 
    path: '/recommendations', 
    name: 'Recommendations', 
    component: () => import('@/views/pages/Recommendations.vue'),
    meta: { requiresAuth: true } 
  },
  {
    path: '/statistic', 
    name: 'Statistic', 
    component: () => import('@/views/pages/Statistic.vue'),
    meta: { requiresAuth: true } 
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});


// // Глобальна навігаційна охорона з логікою SSO
// router.beforeEach(async (to, from, next) => {
//     const userStore = useUserStore();
//     const { ensureAuth } = api();
    
//     // 1. Якщо маршрут не вимагає авторизації АБО користувач вже авторизований, просто продовжуємо.
//     if (!to.meta.requiresAuth || userStore.isAuthenticated) {
//         return next();
//     }

//     // 2. Маршрут вимагає авторизації, але користувач не авторизований.
//     console.log('Потрібна авторизація. Спроба автоматичного відновлення сесії...');
    
//     try {
//         // Запускаємо повний цикл перевірки/відновлення сесії SSO
//         // (включає перевірку токена, запит профілю або повний SSO-потік через розширення)
//         await ensureAuth();
        
//         // Якщо ensureAuth() успішно завершилася, користувач тепер авторизований
//       if (userStore.isAuthenticated) {
//           console.log('SSO успішно відновлено. Продовження навігації.');
//           return next(); // Продовжуємо до цільового маршруту
//       }
        
//     } catch (error) {
//         // Якщо ensureAuth() викинула помилку (наприклад, розширення недоступне або SSO не вдалося)
//         console.warn('Автоматична авторизація не вдалася.', error);
//         userStore.logOut(); // Очищаємо залишки, якщо вони були
//     }
    
//     // 3. Якщо авторизація не вдалася, перенаправляємо на стартову сторінку (Home)
//     console.log('Відновлення сесії не вдалося. Перенаправлення на Home.');
//     return next({ name: 'Home' });
// });

export default router;