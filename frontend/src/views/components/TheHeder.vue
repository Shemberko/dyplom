<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { 
  LogOut, 
  Home, 
  Lightbulb, 
  PieChart // Додано нову іконку для статистики
} from 'lucide-vue-next';

const userStore = useUserStore();
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white/60 backdrop-blur-xl border-b border-white shadow-[0_4px_30px_rgb(0,0,0,0.03)] transition-all duration-300">
    <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
      
      <router-link to="/" class="flex items-center gap-3 group transition-transform duration-300 hover:scale-[1.02] active:scale-95">
        <div class="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30 group-hover:shadow-indigo-500/50 transition-shadow">
          <Lightbulb class="text-white w-5 h-5" />
        </div>
        <span class="font-black text-xl tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 hidden sm:block">
          Insights
        </span>
      </router-link>

      <nav class="flex items-center gap-1 sm:gap-2 absolute left-1/2 -translate-x-1/2">
        <router-link 
          to="/" 
          class="group flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 text-slate-500 hover:bg-white/50 hover:text-indigo-600 hover:shadow-sm"
          active-class="!bg-white/80 !text-indigo-600 shadow-[0_2px_10px_rgb(0,0,0,0.04)] border border-white"
        >
          <Home class="w-4 h-4 transition-transform group-hover:scale-110" />
          <span class="hidden md:block">Головна</span>
        </router-link>

        <router-link 
          v-if="userStore.isAuthenticated" 
          to="/recommendations" 
          class="group flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 text-slate-500 hover:bg-white/50 hover:text-indigo-600 hover:shadow-sm"
          active-class="!bg-white/80 !text-indigo-600 shadow-[0_2px_10px_rgb(0,0,0,0.04)] border border-white"
        >
          <Lightbulb class="w-4 h-4 transition-transform group-hover:scale-110" />
          <span class="hidden md:block">Рекомендації</span>
        </router-link>

        <router-link 
          v-if="userStore.isAuthenticated" 
          to="/statistic" 
          class="group flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 text-slate-500 hover:bg-white/50 hover:text-indigo-600 hover:shadow-sm"
          active-class="!bg-white/80 !text-indigo-600 shadow-[0_2px_10px_rgb(0,0,0,0.04)] border border-white"
        >
          <PieChart class="w-4 h-4 transition-transform group-hover:scale-110" />
          <span class="hidden md:block">Статистика</span>
        </router-link>
      </nav>

      <div class="flex items-center gap-4">
        <div v-if="userStore.isAuthenticated" class="flex items-center gap-3">
          <div class="hidden lg:flex flex-col items-end">
            <span class="text-xs font-bold text-slate-800 truncate max-w-[150px]">
              {{ userStore.user?.email }}
            </span>
            <span class="text-[9px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Користувач</span>
          </div>
          
          <div class="hidden lg:block w-px h-8 bg-slate-200/60 mx-1"></div>
        </div>
        <div v-else class="w-[38px] h-[38px]"></div>
      </div>

    </div>
  </header>
</template>