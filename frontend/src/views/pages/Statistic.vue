<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '@/composables/api';
import { Loader2, BarChart3, Globe, Layers, Clock, Search, RefreshCcw } from 'lucide-vue-next';
import { Bar, Doughnut } from 'vue-chartjs'; // Замінили Pie на Doughnut
import { 
  Chart as ChartJS, Title, Tooltip, Legend, BarElement, 
  CategoryScale, LinearScale, ArcElement 
} from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement);

const { getData } = api();
const loading = ref(true);
const error = ref<string | null>(null);
const stats = ref<any>(null);
const STATS_URL = '/statistic';

const fetchStats = async () => {
    loading.value = true;
    error.value = null;
    try {
        const response = await getData(STATS_URL);
        console.log(response)
        stats.value = response;
    } catch (e: any) {
        error.value = e.message || "Не вдалося завантажити статистику.";
    } finally {
        loading.value = false;
    }
};

// Налаштування для графіка активності (Bar Chart)
const activityChartData = computed(() => {
    const data = stats.value?.activity_chart || [];
    return {
        labels: data.map((d: any) => d.date) || [],
        datasets: [{
            label: 'Перегляди',
            backgroundColor: '#6366f1', // Indigo 500
            hoverBackgroundColor: '#8b5cf6', // Purple 500
            borderRadius: 6,
            borderSkipped: false,
            data: data.map((d: any) => d.count) || []
        }]
    };
});

// Налаштування для графіка категорій (Doughnut Chart)
const categoriesChartData = computed(() => {
    const data = stats.value?.top_categories || [];
    return {
        labels: data.map((c: any) => c.name) || [],
        datasets: [{
            // Нова преміальна палітра кольорів
            backgroundColor: ['#6366f1', '#8b5cf6', '#ec4899', '#14b8a6', '#f59e0b'],
            borderWidth: 0, // Прибираємо білі рамки між секторами
            hoverOffset: 6,
            data: data.map((c: any) => c.value) || []
        }]
    };
});

// Опції для графіків, щоб вони виглядали сучасно
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom' as const,
            labels: {
                usePointStyle: true,
                padding: 20,
                color: '#64748b',
                font: { family: 'inherit', size: 12 }
            }
        }
    }
};

const barOptions = {
    ...chartOptions,
    scales: {
        y: { 
            beginAtZero: true, 
            grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
            border: { dash: [4, 4] }
        },
        x: { 
            grid: { display: false, drawBorder: false }
        }
    }
};

const doughnutOptions = {
    ...chartOptions,
    cutout: '75%', // Робить "дірку" всередині, перетворюючи Pie на Doughnut
};

onMounted(fetchStats);
</script>

<template>
  <div class="relative min-h-screen w-full bg-[#F8FAFC] overflow-hidden z-0">
    
    <div class="fixed inset-0 w-full h-full pointer-events-none -z-10">
        <div class="absolute top-[10%] left-[-10%] w-[500px] h-[500px] bg-blue-200/40 rounded-full mix-blend-multiply filter blur-[120px] animate-blob"></div>
        <div class="absolute bottom-[-10%] right-[-5%] w-[600px] h-[600px] bg-indigo-200/40 rounded-full mix-blend-multiply filter blur-[120px] animate-blob animation-delay-2000"></div>
    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-12 relative z-10">
      
      <header class="mb-10 text-center md:text-left animate-fade-in-up">
        <h1 class="text-4xl font-black text-slate-900 mb-2 tracking-tight">
          Ваша <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">Аналітика</span>
        </h1>
      </header>

      <div v-if="loading" class="flex flex-col items-center justify-center py-32 animate-fade-in-up">
        <div class="w-20 h-20 mb-6 bg-white/50 backdrop-blur-md rounded-3xl flex items-center justify-center shadow-sm border border-white">
            <Loader2 class="w-8 h-8 opacity-50 text-indigo-600 animate-spin" />
        </div>
        <p class="text-lg font-medium text-slate-400">Аналізуємо дані...</p>
      </div>

      <div v-else-if="error" class="text-center py-16 bg-red-50/80 backdrop-blur-md rounded-[24px] border border-red-100 shadow-sm max-w-2xl mx-auto animate-fade-in-up">
        <p class="text-red-600 mb-6 font-medium">{{ error }}</p>
        <button @click="fetchStats" class="group flex items-center gap-2 mx-auto px-6 py-3 bg-white text-red-600 border border-red-200 rounded-xl hover:bg-red-600 hover:text-white transition-all shadow-sm">
            <RefreshCcw class="w-4 h-4 transition-transform group-hover:rotate-180 duration-500" />
            Оновити
        </button>
      </div>

      <div v-else-if="stats" class="space-y-8 animate-fade-in-up" style="animation-delay: 0.1s; animation-fill-mode: both;">
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="group bg-white/60 backdrop-blur-xl p-6 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 transition-all duration-300 flex items-center space-x-5">
            <div class="p-4 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl text-blue-600 shadow-inner group-hover:scale-110 transition-transform">
                <BarChart3 class="w-6 h-6" />
            </div>
            <div>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Всього візитів</p>
              <p class="text-3xl font-black text-slate-800">{{ stats.summary.total_visits }}</p>
            </div>
          </div>
          
          <div class="group bg-white/60 backdrop-blur-xl p-6 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 transition-all duration-300 flex items-center space-x-5">
            <div class="p-4 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-2xl text-emerald-600 shadow-inner group-hover:scale-110 transition-transform">
                <Globe class="w-6 h-6" />
            </div>
            <div>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Унікальних сторінок</p>
              <p class="text-3xl font-black text-slate-800">{{ stats.summary.unique_pages }}</p>
            </div>
          </div>
          
          <div class="group bg-white/60 backdrop-blur-xl p-6 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 transition-all duration-300 flex items-center space-x-5">
            <div class="p-4 bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl text-purple-600 shadow-inner group-hover:scale-110 transition-transform">
                <Layers class="w-6 h-6" />
            </div>
            <div>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Категорій</p>
              <p class="text-3xl font-black text-slate-800">{{ stats.summary.total_categories }}</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          <div class="bg-white/60 backdrop-blur-xl p-6 md:p-8 rounded-[32px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white transition-all hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]">
            <div class="flex items-center gap-3 mb-8">
                <div class="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-500">
                    <Clock class="h-5 w-5" />
                </div>
                <h3 class="text-xl font-bold text-slate-800">Активність за 7 днів</h3>
            </div>
            <div class="h-72 w-full">
              <Bar :data="activityChartData" :options="barOptions" />
            </div>
          </div>

          <div class="bg-white/60 backdrop-blur-xl p-6 md:p-8 rounded-[32px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white transition-all hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]">
            <div class="flex items-center gap-3 mb-8">
                <div class="w-10 h-10 rounded-full bg-purple-50 flex items-center justify-center text-purple-500">
                    <Search class="h-5 w-5" />
                </div>
                <h3 class="text-xl font-bold text-slate-800">Сфери інтересів</h3>
            </div>
            <div class="h-72 w-full flex justify-center relative">
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-[-30px]">
                  <span class="text-xs font-bold text-slate-400 uppercase tracking-widest">Топ</span>
                  <span class="text-2xl font-black text-slate-800">
                    {{ stats.top_categories && stats.top_categories.length > 0 ? stats.top_categories[0].name.split(' ')[0] : '' }}
                  </span>
              </div>
              <Doughnut :data="categoriesChartData" :options="doughnutOptions" />
            </div>
          </div>
          
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-up {
    animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-blob {
    animation: blob 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1);
}
.animation-delay-2000 {
    animation-delay: 2s;
}

@keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
}
</style>