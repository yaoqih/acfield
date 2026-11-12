import { createApp } from 'vue'
import App from './App.vue'
import EncoderDiagnostics from './EncoderDiagnostics.vue'
import './style.css'
createApp(location.pathname.replace(/\/$/, '') === '/encoder' ? EncoderDiagnostics : App).mount('#app')
