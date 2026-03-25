<script setup lang="ts">
import { onMounted, watch } from 'vue'; // Повертаємо watch
import { useUserStore } from '@/stores/user';
import { useStatsStore } from '@/stores/stats';
import { useRecommendationStore } from '@/stores/recommendations'; // Підключаємо стор
import { useHistoryStore } from '@/stores/history';               // Підключаємо стор
import { storeToRefs } from 'pinia';
import { api } from '@/composables/api';

import TopRecommendationsWidget from '../components/TopRecommendationsWidget.vue';
import LastVisited from '../components/LastVisited.vue';

import { 
    ShieldCheck, 
    Chrome, 
    ArrowRight, 
    CheckCircle2,
    Sparkles,
    Users,    
    Activity  
} from 'lucide-vue-next';

const userStore = useUserStore();
const statsStore = useStatsStore(); 
const recommendationStore = useRecommendationStore();
const historyStore = useHistoryStore();

const { isAuthenticated, user } = storeToRefs(userStore);
const { ensureAuth } = api();

onMounted(() => {
    statsStore.fetchStats();
});

watch(isAuthenticated, (isAuth) => {
    if (isAuth) {
        if (recommendationStore.rawRecommendations.length === 0) {
            recommendationStore.fetchNextBatch();
        }
        if (historyStore.historyItems.length === 0) {
            historyStore.fetchHistory(7);
        }
    }
}, { immediate: true }); // immediate: true гарантує, що перевірка спрацює одразу при завантаженні

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
    <div class="relative min-h-[calc(100vh-64px)] bg-[#F8FAFC] flex flex-col items-center justify-start px-4 py-12 overflow-hidden z-0">
        
        <div class="absolute inset-0 w-full h-full pointer-events-none -z-10 overflow-hidden fixed">
            <div class="absolute top-[-10%] left-[10%] w-[400px] md:w-[600px] h-[400px] md:h-[600px] bg-indigo-300/40 rounded-full mix-blend-multiply filter blur-[100px] opacity-70 animate-blob"></div>
            <div class="absolute top-[20%] right-[-5%] w-[350px] md:w-[500px] h-[350px] md:h-[500px] bg-purple-300/40 rounded-full mix-blend-multiply filter blur-[100px] opacity-70 animate-blob animation-delay-2000"></div>
            <div class="absolute bottom-[-10%] left-[20%] w-[400px] md:w-[550px] h-[400px] md:h-[550px] bg-blue-300/40 rounded-full mix-blend-multiply filter blur-[100px] opacity-70 animate-blob animation-delay-4000"></div>
        </div>

        <div class="max-w-4xl w-full text-center relative z-10 mb-12">
            <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/60 backdrop-blur-md border border-white/80 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] text-indigo-600 text-xs font-bold uppercase tracking-wider mb-6 animate-fade-in hover:scale-105 transition-transform cursor-default">
                <Sparkles class="w-3.5 h-3.5 text-indigo-500" />
                <span>AI-powered analytics</span>
            </div>
            
            <h1 class="text-4xl md:text-6xl font-black text-slate-900 mb-6 tracking-tight leading-[1.1] animate-slide-up" style="animation-delay: 0.1s; animation-fill-mode: both;">
                Аналізуйте свій час з <br class="hidden md:block"/>
                <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 pb-2">Insights</span>
            </h1>

            <p class="text-lg md:text-xl text-slate-600 mb-8 max-w-2xl mx-auto leading-relaxed animate-slide-up" style="animation-delay: 0.2s; animation-fill-mode: both;">
                Розумний помічник, який допомагає оптимізувати вашу активність у браузері та надає персоналізовані рекомендації.
                <span v-if="statsStore.totalUsers > 0" class="block mt-3 text-base md:text-lg font-medium text-slate-700">
                    Нам вже довіряють <span class="text-indigo-600 font-bold">{{ statsStore.totalUsers }}</span> користувачів, 
                    які разом проаналізували понад <span class="text-purple-600 font-bold">{{ statsStore.totalPages }}</span> сторінок.
                </span>
            </p>
            
            <div v-if="isAuthenticated" class="inline-flex items-center gap-3 p-2 pr-6 bg-white/50 backdrop-blur-md border border-white shadow-sm rounded-full mx-auto animate-slide-up" style="animation-delay: 0.3s; animation-fill-mode: both;">
                <div class="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600">
                    <ShieldCheck class="w-4 h-4" />
                </div>
                <span class="text-sm font-bold text-slate-700">{{ user.email }}</span>
            </div>
        </div>

        <div v-if="isAuthenticated" class="w-full max-w-7xl relative z-10 animate-slide-up" style="animation-delay: 0.4s; animation-fill-mode: both;">
            <div class="flex flex-col gap-8 md:gap-10">
                <TopRecommendationsWidget class="w-full min-w-0" />
                <LastVisited class="w-full min-w-0" />
            </div>
        </div>

        <div v-else class="max-w-2xl w-full mx-auto relative z-10 animate-slide-up" style="animation-delay: 0.4s; animation-fill-mode: both;">
            
            <div v-if="statsStore.totalUsers > 0" class="flex flex-wrap justify-center gap-4 mb-10">
                <div class="flex items-center gap-3 px-5 py-3 bg-white/60 backdrop-blur-md border border-white rounded-2xl shadow-sm hover:-translate-y-1 hover:shadow-md transition-all">
                    <div class="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                        <Users class="w-5 h-5" />
                    </div>
                    <div class="text-left">
                        <div class="text-xl font-black text-slate-800 leading-none">{{ statsStore.totalUsers }}</div>
                        <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-1">Користувачів</div>
                    </div>
                </div>
                
                <div class="flex items-center gap-3 px-5 py-3 bg-white/60 backdrop-blur-md border border-white rounded-2xl shadow-sm hover:-translate-y-1 hover:shadow-md transition-all">
                    <div class="p-2 bg-purple-50 text-purple-600 rounded-lg">
                        <Activity class="w-5 h-5" />
                    </div>
                    <div class="text-left">
                        <div class="text-xl font-black text-slate-800 leading-none">{{ statsStore.totalPages }}</div>
                        <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-1">Проаналізованих сторінок</div>
                    </div>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-10 text-left">
                <div class="group p-6 bg-white/60 backdrop-blur-xl border border-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-3xl transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgb(0,0,0,0.1)] hover:bg-white/80">
                    <div class="w-12 h-12 bg-blue-50/80 text-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
                        <Chrome class="w-6 h-6" />
                    </div>
                    <h3 class="font-bold text-slate-900 text-lg mb-2">Встановіть розширення</h3>
                    <p class="text-sm text-slate-500 leading-relaxed">Для роботи сервісу необхідне Chrome Extension, яке збирає дані для аналізу.</p>
                </div>
                
                <div class="group p-6 bg-white/60 backdrop-blur-xl border border-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-3xl transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgb(0,0,0,0.1)] hover:bg-white/80">
                    <div class="w-12 h-12 bg-emerald-50/80 text-emerald-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
                        <ShieldCheck class="w-6 h-6" />
                    </div>
                    <h3 class="font-bold text-slate-900 text-lg mb-2">Безпечний вхід</h3>
                    <p class="text-sm text-slate-500 leading-relaxed">Ми використовуємо SSO через розширення для максимальної безпеки ваших даних.</p>
                </div>
            </div>

            <div class="flex justify-center">
                <button @click="handleLoginClick" class="group relative w-full sm:w-auto px-10 py-4 bg-indigo-600 text-white rounded-2xl font-bold text-lg overflow-hidden transition-all hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/30 active:scale-95">
                    <span class="absolute inset-0 w-full h-full bg-gradient-to-r from-indigo-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out"></span>
                    <span class="relative z-10 flex items-center justify-center gap-2">
                        Увійти через Chrome Extension
                        <ArrowRight class="w-5 h-5 opacity-0 -ml-5 group-hover:opacity-100 group-hover:ml-0 transition-all duration-300" />
                    </span>
                </button>
            </div>
            
            <p class="mt-6 text-sm text-slate-500 flex items-center justify-center gap-2 font-medium">
                <CheckCircle2 class="w-4 h-4 text-emerald-500" />
                Без паролів. Тільки ваш Google Account.
            </p>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.8s ease-out; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-blob { animation: blob 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); }
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }

@keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
}
</style>