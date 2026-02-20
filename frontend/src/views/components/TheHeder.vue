<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { LogOut, Home, Lightbulb, User } from 'lucide-vue-next';

const userStore = useUserStore();
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
    <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
      
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Lightbulb class="text-white w-5 h-5" />
        </div>
        <span class="font-bold text-xl tracking-tight text-gray-900 hidden sm:block">
          Insights
        </span>
      </div>

      <nav class="flex items-center gap-1 sm:gap-4">
        <router-link 
          to="/" 
          class="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors hover:bg-gray-100 text-gray-600 hover:text-gray-900"
          active-class="bg-blue-50 !text-blue-600"
        >
          <Home class="w-4 h-4" />
          <span class="hidden md:block">Головна</span>
        </router-link>

        <router-link 
          v-if="userStore.isAuthenticated" 
          to="/recommendations" 
          class="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors hover:bg-gray-100 text-gray-600 hover:text-gray-900"
          active-class="bg-blue-50 !text-blue-600"
        >
          <Lightbulb class="w-4 h-4" />
          <span class="hidden md:block">Рекомендації</span>
        </router-link>
      </nav>

      <div v-if="userStore.isAuthenticated" class="flex items-center gap-3 ml-2 border-l pl-4 border-gray-100">
        <div class="hidden lg:flex flex-col items-end">
          <span class="text-xs font-bold text-gray-900 truncate max-w-[150px]">
            {{ userStore.user?.email }}
          </span>
          <span class="text-[10px] text-gray-400 uppercase tracking-widest">Користувач</span>
        </div>
        
        <button 
          @click="userStore.logOut()" 
          class="p-2.5 rounded-xl bg-gray-50 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-all active:scale-95 shadow-sm"
          title="Вийти"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </div>
  </header>
</template>