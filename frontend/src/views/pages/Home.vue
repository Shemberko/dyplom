<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';
import { api } from '@/composables/api';
import { 
  ShieldCheck, 
  Chrome, 
  ArrowRight, 
  Zap, 
  LayoutDashboard,
  CheckCircle2
} from 'lucide-vue-next';

const userStore = useUserStore();
const { isAuthenticated, user } = storeToRefs(userStore);
const { ensureAuth } = api();

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
    <div class="min-h-[calc(100vh-64px)] bg-[#FDFDFF] flex flex-col items-center justify-center px-4 py-12">
        
        <div class="max-w-4xl w-full text-center">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold uppercase tracking-wider mb-6 animate-fade-in">
                <Zap class="w-3.5 h-3.5" />
                <span>AI-powered analytics</span>
            </div>
            
            <h1 class="text-5xl md:text-7xl font-black text-slate-900 mb-8 tracking-tight leading-[1.1]">
                Аналізуйте свій час з <span class="text-indigo-600">Insights</span>
            </h1>
            
            <p class="text-lg md:text-xl text-slate-500 mb-12 max-w-2xl mx-auto leading-relaxed">
                Розумний помічник, який допомагає оптимізувати вашу активність у браузері та надає персоналізовані рекомендації на основі вашої поведінки.
            </p>

            <div v-if="isAuthenticated" class="space-y-6 animate-slide-up">
                <div class="inline-flex items-center gap-3 p-2 pr-6 bg-white border border-slate-100 rounded-2xl shadow-sm">
                    <div class="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-indigo-600">
                        <ShieldCheck class="w-6 h-6" />
                    </div>
                    <div class="text-left">
                        <p class="text-xs text-slate-400 font-bold uppercase">Авторизовано як</p>
                        <p class="text-sm font-bold text-slate-900">{{ user.email }}</p>
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <router-link to="/recommendations" class="group flex items-center gap-2 px-8 py-4 bg-slate-900 text-white rounded-2xl font-bold transition-all hover:bg-indigo-600 hover:shadow-xl hover:shadow-indigo-100">
                        Перейти до рекомендацій
                        <ArrowRight class="w-4 h-4 transition-transform group-hover:translate-x-1" />
                    </router-link>
                </div>
            </div>

            <div v-else class="max-w-2xl mx-auto animate-slide-up">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10 text-left">
                    <div class="p-5 bg-white border border-slate-50 rounded-2xl shadow-sm">
                        <div class="w-10 h-10 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-4">
                            <Chrome class="w-5 h-5" />
                        </div>
                        <h3 class="font-bold text-slate-900 mb-2">Встановіть розширення</h3>
                        <p class="text-sm text-slate-500 leading-relaxed">Для роботи сервісу необхідне Chrome Extension, яке збирає дані.</p>
                    </div>
                    <div class="p-5 bg-white border border-slate-50 rounded-2xl shadow-sm">
                        <div class="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center mb-4">
                            <ShieldCheck class="w-5 h-5" />
                        </div>
                        <h3 class="font-bold text-slate-900 mb-2">Безпечний вхід</h3>
                        <p class="text-sm text-slate-500 leading-relaxed">Ми використовуємо SSO через розширення для максимальної безпеки.</p>
                    </div>
                </div>

                <button @click="handleLoginClick" class="w-full sm:w-auto px-10 py-5 bg-indigo-600 text-white rounded-2xl font-black text-lg shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:-translate-y-1 transition-all active:scale-95">
                    Увійти через Chrome Extension
                </button>
                
                <p class="mt-6 text-sm text-slate-400 flex items-center justify-center gap-2">
                    <CheckCircle2 class="w-4 h-4 text-emerald-500" />
                    Без паролів. Тільки ваш Google Account.
                </p>
            </div>
        </div>

        <div class="absolute top-0 left-1/2 -translate-x-1/2 -z-10 w-full max-w-6xl h-full opacity-30 pointer-events-none">
            <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-200 blur-[120px] rounded-full"></div>
            <div class="absolute bottom-[10%] right-[-5%] w-[30%] h-[30%] bg-blue-100 blur-[100px] rounded-full"></div>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in {
    animation: fadeIn 0.8s ease-out;
}
.animate-slide-up {
    animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>