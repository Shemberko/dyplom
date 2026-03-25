<script setup lang="ts">
import { computed, onMounted, watch } from 'vue';
import { useRecommendationStore } from '@/stores/recommendations';
import { useUserStore } from '@/stores/user';
import { Compass, ArrowRight } from 'lucide-vue-next';
import RecommendationCard from './RecommendationCard.vue';

const recommendationStore = useRecommendationStore();
const userStore = useUserStore();

const loadDataIfNeeded = () => {
  if (userStore.isAuthenticated && recommendationStore.rawRecommendations.length === 0) {
    recommendationStore.fetchNextBatch();
  }
};

onMounted(loadDataIfNeeded);
watch(() => userStore.isAuthenticated, loadDataIfNeeded);

const topRecommendations = computed(() => recommendationStore.displayRecommendations.slice(0, 5));
</script>

<template>
  <div class="flex flex-col bg-white/60 backdrop-blur-xl border border-white shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-[24px] overflow-hidden">
    
    <div class="px-5 py-4 sm:px-6 sm:py-5 border-b border-slate-100/80 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><Compass class="w-5 h-5" /></div>
        <h2 class="text-lg sm:text-xl font-bold text-slate-800">Топ рекомендацій</h2>
      </div>

      <router-link 
        to="/recommendations" 
        class="hidden sm:flex items-center gap-1.5 text-sm font-bold text-indigo-600 hover:text-indigo-700 transition-colors group"
      >
        Всі рекомендації 
        <ArrowRight class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
      </router-link>
    </div>
    
    <div class="p-4 sm:p-5 flex-grow overflow-hidden">
      <div v-if="recommendationStore.isLoading && topRecommendations.length === 0" class="text-center py-8 text-slate-400">
        Завантаження...
      </div>
      
      <div 
        v-else 
        class="flex overflow-x-auto snap-x snap-mandatory gap-4 sm:gap-5 pb-2 hide-scrollbar h-full items-stretch"
      >
        <div 
          v-for="rec in topRecommendations" 
          :key="rec.id" 
          class="shrink-0 w-[260px] sm:w-[280px] lg:w-[300px] snap-start h-auto flex"
        >
          <RecommendationCard 
            :rec="rec" 
            class="w-full h-full"
          />
        </div>
      </div>
    </div>
    
    <div class="sm:hidden p-4 bg-slate-50/50 border-t border-slate-100/50 mt-auto">
      <router-link to="/recommendations" class="w-full py-2 flex items-center justify-center gap-2 text-sm font-bold text-indigo-600 hover:text-indigo-700 transition-colors">
        Всі рекомендації <ArrowRight class="w-4 h-4" />
      </router-link>
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