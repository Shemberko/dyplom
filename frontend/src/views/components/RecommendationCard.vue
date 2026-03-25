<script setup lang="ts">
import { computed } from 'vue';
import type { PageRecommendation } from '@/stores/recommendations';
import { 
  Image as ImageIcon, 
  ArrowRight, 
  FileText,
  Network,
  Sparkles,
  Flame,
  Users,    // Нова іконка для кількості візитів
  Clock     // Нова іконка для дати
} from 'lucide-vue-next'; 

const props = defineProps<{
  rec: PageRecommendation;
}>();

const formattedScore = computed(() => {
  return (props.rec.score * 100).toFixed(1) + '%';
});

const domain = computed(() => {
  try {
    return new URL(props.rec.url).hostname.replace('www.', '');
  } catch {
    return 'Зовнішній ресурс';
  }
});

// Форматування дати останнього візиту
const formattedDate = computed(() => {
  if (!props.rec.last_visited) return 'Невідомо';
  try {
    const date = new Date(props.rec.last_visited);
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date);
  } catch {
    return 'Невідомо';
  }
});

const typeInfo = computed(() => {
  switch (props.rec.type) {
    case 'text':
      return { label: 'За текстом', color: 'text-blue-600', icon: FileText };
    case 'hybrid':
      return { label: 'За графом', color: 'text-purple-600', icon: Network };
    case 'mixed':
      return { label: 'Топ збіг', color: 'text-amber-600', icon: Sparkles };
    case 'trending':
      return { label: 'Популярне', color: 'text-rose-600', icon: Flame };
    default:
      return null;
  }
});
</script>

<template>
  <a
    :href="rec.url"
    target="_blank"
    rel="noopener noreferrer"
    class="group flex flex-col bg-white/60 backdrop-blur-xl border border-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-[24px] hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:bg-white/80 hover:-translate-y-1.5 transition-all duration-300 overflow-hidden h-full cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
  >
    <div class="relative h-52 w-full overflow-hidden bg-slate-50/50">
      
      <img
        v-if="rec.image"
        :src="rec.image"
        :alt="rec.title"
        class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 ease-out"
      />
      
      <div v-else class="w-full h-full bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center group-hover:scale-105 transition-transform duration-700 relative overflow-hidden">
        <div class="absolute w-32 h-32 bg-indigo-200/40 rounded-full blur-2xl top-[-20px] left-[-20px]"></div>
        <div class="absolute w-32 h-32 bg-purple-200/40 rounded-full blur-2xl bottom-[-20px] right-[-20px]"></div>
        <ImageIcon class="w-12 h-12 relative z-10 text-indigo-300/80" stroke-width="1.5" />
      </div>

      <div 
        v-if="typeInfo" 
        class="absolute top-4 left-4 bg-white/80 backdrop-blur-md px-3 py-1.5 rounded-full shadow-sm border border-white flex items-center gap-1.5 transition-transform group-hover:scale-105"
      >
        <component :is="typeInfo.icon" class="w-3.5 h-3.5" :class="typeInfo.color" />
        <span class="text-[10px] font-bold uppercase tracking-wider" :class="typeInfo.color">
          {{ typeInfo.label }}
        </span>
      </div>

      <div class="absolute top-4 right-4 bg-white/80 backdrop-blur-md px-2.5 py-1 rounded-full shadow-sm border border-white flex items-center">
        <span class="text-xs font-black text-emerald-600" title="Відсоток релевантності">
          {{ formattedScore }}
        </span>
      </div>
    </div>

    <div class="p-6 flex flex-col flex-grow relative">
      <p class="text-[10px] font-bold text-indigo-500 mb-2 uppercase tracking-widest">
        {{ domain }}
      </p>

      <h3 class="text-lg font-bold text-slate-800 mb-3 line-clamp-2 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-indigo-600 group-hover:to-purple-600 transition-all duration-300">
        {{ rec.title }}
      </h3>

      <p v-if="rec.description" class="text-sm text-slate-500 line-clamp-3 mb-4 flex-grow leading-relaxed">
        {{ rec.description }}
      </p>
      <div v-else class="flex-grow"></div> 

      <div v-if="rec.visit_count !== undefined && rec.visit_count > 0" class="flex items-center gap-4 mb-4 text-[11px] font-medium text-slate-500">
        <div class="flex items-center gap-1.5 bg-slate-100/80 px-2 py-1 rounded-md">
          <Users class="w-3.5 h-3.5 text-slate-400" />
          <span>Переглядів: <span class="text-slate-700 font-bold">{{ rec.visit_count }}</span></span>
        </div>
        
        <div v-if="rec.last_visited" class="flex items-center gap-1.5">
          <Clock class="w-3.5 h-3.5 text-slate-400" />
          <span>{{ formattedDate }}</span>
        </div>
      </div>

      <div class="pt-4 border-t border-slate-100/80 flex items-center justify-between mt-auto">
        <span class="text-sm font-bold text-slate-400 group-hover:text-indigo-600 transition-colors flex items-center gap-2">
          Читати статтю
          <ArrowRight class="w-4 h-4 transform group-hover:translate-x-1.5 transition-transform duration-300" />
        </span>
      </div>
    </div>
  </a>
</template>