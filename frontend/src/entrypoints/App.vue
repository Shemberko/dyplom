<script setup lang="ts">
import { onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import { useRouter } from 'vue-router'; 
// import Notification from './components/Notification.vue';

const userStore = useUserStore();
const router = useRouter();

userStore.initializeAuth(); 
</script>

<template>
  <div id="app-container">
    
    <header class="app-header">
      <nav>
        <router-link to="/">Головна</router-link>
        
        <router-link v-if="userStore.isAuthenticated" to="/recommendations">Рекомендації</router-link>
        
        <button v-if="userStore.isAuthenticated" @click="userStore.logOut()">
          Вийти ({{ userStore.user.email }})
        </button>
      </nav>
    </header>

    <main class="app-main">
      <router-view />
    </main>

    <!-- <Notification /> -->
  </div>
</template>

<style scoped>
</style>