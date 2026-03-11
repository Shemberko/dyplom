<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from '@/composables/api';
import { Loader2, BarChart3, Globe, Layers, Clock } from 'lucide-vue-next';
import { Bar, Pie } from 'vue-chartjs';
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

const activityChartData = computed(() => ({
    labels: stats.value?.activity_chart.map((d: any) => d.date) || [],
    datasets: [{
        label: 'Перегляди',
        backgroundColor: '#3b82f6',
        borderRadius: 8,
        data: stats.value?.activity_chart.map((d: any) => d.count) || []
    }]
}));

const categoriesChartData = computed(() => ({
    labels: stats.value?.top_categories.map((c: any) => c.name) || [],
    datasets: [{
        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
        data: stats.value?.top_categories.map((c: any) => c.value) || []
    }]
}));

onMounted(fetchStats);
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-10 px-4">
    <div class="max-w-6xl mx-auto">
      
      <header class="mb-10">
        <h1 class="text-3xl font-extrabold text-gray-900">Ваша Аналітика</h1>
        <p class="text-gray-500">Огляд вашої активності та інтересів на основі історії переглядів.</p>
      </header>

      <div v-if="loading" class="flex flex-col items-center py-20">
        <Loader2 class="h-10 w-10 text-blue-600 animate-spin mb-4" />
        <p class="text-gray-500">Аналізуємо дані...</p>
      </div>

      <div v-else-if="error" class="text-center py-10 bg-red-50 rounded-xl border border-red-100">
        <p class="text-red-600 mb-4">{{ error }}</p>
        <button @click="fetchStats" class="px-4 py-2 bg-white text-red-600 border border-red-200 rounded-lg">Оновити</button>
      </div>

      <div v-else-if="stats" class="space-y-8">
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4">
            <div class="p-3 bg-blue-50 rounded-lg text-blue-600"><BarChart3 /></div>
            <div>
              <p class="text-sm text-gray-500">Всього візитів</p>
              <p class="text-2xl font-bold">{{ stats.summary.total_visits }}</p>
            </div>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4">
            <div class="p-3 bg-green-50 rounded-lg text-green-600"><Globe /></div>
            <div>
              <p class="text-sm text-gray-500">Унікальних сторінок</p>
              <p class="text-2xl font-bold">{{ stats.summary.unique_pages }}</p>
            </div>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4">
            <div class="p-3 bg-purple-50 rounded-lg text-purple-600"><Layers /></div>
            <div>
              <p class="text-sm text-gray-500">Категорій</p>
              <p class="text-2xl font-bold">{{ stats.summary.total_categories }}</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 class="text-lg font-bold mb-6 flex items-center">
              <Clock class="mr-2 h-5 w-5 text-gray-400" /> Активність за 7 днів
            </h3>
            <div class="h-64">
              <Bar :data="activityChartData" :options="{ maintainAspectRatio: false }" />
            </div>
          </div>

          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 class="text-lg font-bold mb-6 flex items-center">
              <Search class="mr-2 h-5 w-5 text-gray-400" /> Сфери інтересів
            </h3>
            <div class="h-64 flex justify-center">
              <Pie :data="categoriesChartData" :options="{ maintainAspectRatio: false }" />
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>