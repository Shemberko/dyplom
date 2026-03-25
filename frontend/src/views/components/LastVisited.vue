<script setup lang="ts">
import { computed, onMounted, watch } from 'vue';
import { useHistoryStore } from '@/stores/history';
import { useUserStore } from '@/stores/user'; // Додано для перевірки авторизації
import { Clock, Globe, ArrowUpRight, Users, Trash2 } from 'lucide-vue-next'; 

const historyStore = useHistoryStore();
const userStore = useUserStore();

// Надійний спосіб завантаження: перевіряємо статус і наявність даних
const loadDataIfNeeded = () => {
  if (userStore.isAuthenticated && historyStore.historyItems.length === 0) {
    historyStore.fetchHistory(7);
  }
};

// Викликаємо при появі віджета на екрані
onMounted(loadDataIfNeeded);
// А також якщо юзер щойно залогінився
watch(() => userStore.isAuthenticated, loadDataIfNeeded);

// Беремо 5 останніх візитів
const recentHistory = computed(() => historyStore.historyItems.slice(0, 5));

const getDomain = (url: string) => {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return 'вебсайт';
  }
};

const formatVisitTime = (isoDate: string) => {
  if (!isoDate) return '';
  const date = new Date(isoDate);
  const today = new Date();
  const timeString = date.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
  
  if (date.toDateString() === today.toDateString()) return `Сьогодні, ${timeString}`;
  return `${date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' })}, ${timeString}`;
};

// Функція для обробки видалення
const handleDelete = (pageId: string) => {
  historyStore.removeItem(pageId);
};
</script>

<template>
  <div class="flex flex-col bg-white/60 backdrop-blur-xl border border-white shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-[24px] overflow-hidden">
    
    <div class="px-5 py-4 sm:px-6 sm:py-5 border-b border-slate-100/80 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-purple-50 text-purple-600 rounded-lg"><Clock class="w-5 h-5" /></div>
        <h2 class="text-lg sm:text-xl font-bold text-slate-800">Останні візити</h2>
      </div>
    </div>
    
    <div class="p-4 sm:p-5 flex-grow overflow-hidden relative">
      <div v-if="historyStore.isLoading && recentHistory.length === 0" class="text-center py-8 text-slate-400">
        Завантаження...
      </div>
      <div v-if="!historyStore.isLoading && recentHistory.length === 0" class="text-center py-8 text-slate-400 font-medium">
        Історія порожня
      </div>

      <div 
        v-else 
        class="flex overflow-x-auto snap-x snap-mandatory gap-4 sm:gap-5 pb-2 hide-scrollbar h-full items-stretch"
      >
        <a 
          v-for="item in recentHistory" 
          :key="item.id" 
          :href="item.url" 
          target="_blank"
          class="group shrink-0 w-[240px] sm:w-[260px] lg:w-[280px] snap-start flex flex-col bg-white border border-slate-100 shadow-sm rounded-2xl hover:shadow-md hover:-translate-y-1 transition-all duration-300 overflow-hidden relative"
        >
          <div class="h-24 bg-slate-50 relative overflow-hidden flex items-center justify-center shrink-0">
            <img 
              v-if="item.image" 
              :src="item.image" 
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
            />
            <Globe v-else class="w-8 h-8 text-purple-200" />
            
            <div class="absolute top-2 left-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-md shadow-sm border border-white/50 flex items-center gap-1">
              <Clock class="w-3 h-3 text-purple-600" />
              <span class="text-[10px] font-bold text-slate-700">{{ formatVisitTime(item.last_visited) }}</span>
            </div>
            
            <ArrowUpRight class="absolute top-2 right-2 w-5 h-5 text-white drop-shadow-md opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>

          <div class="p-4 flex flex-col flex-grow">
            <p class="text-[10px] font-bold text-purple-500 uppercase tracking-widest mb-1 truncate">
              {{ getDomain(item.url) }}
            </p>
            <h4 class="text-sm font-bold text-slate-800 line-clamp-2 mb-2 group-hover:text-purple-600 transition-colors">
              {{ item.title }}
            </h4>
            
            <div class="mt-auto flex items-center justify-between border-t border-slate-50 pt-3">
              <div class="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                <Users class="w-3.5 h-3.5" />
                <span title="Глобальні перегляди">{{ item.visit_count }}</span>
              </div>

              <button 
                @click.prevent="handleDelete(item.id)"
                class="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 focus:outline-none"
                title="Видалити з історії"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
</style>