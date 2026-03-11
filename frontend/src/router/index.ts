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

export default router;