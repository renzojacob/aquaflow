import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { IonicVue } from '@ionic/vue'

import App from './App.vue'
import router from './router'
import { initTheme } from './composables/useTheme'
import { initSpotlight } from './theme/spotlight'
import { oceanPageTransition } from './theme/pageTransition'
import { setUnauthorizedHandler } from './services/http'
import { useAuthStore } from './stores/auth'

/* Fonts are bundled with the app (not loaded from Google),
   so they still work when the rider is offline. */
import '@fontsource-variable/unbounded'   // display: headings + big numbers
import '@fontsource-variable/manrope'     // text
import '@fontsource/jetbrains-mono/500.css' // codes + small labels
import '@fontsource/jetbrains-mono/600.css'

/* Core CSS required for Ionic components to work properly */
import '@ionic/vue/css/core.css'

/* Basic CSS for apps built with Ionic */
import '@ionic/vue/css/normalize.css'
import '@ionic/vue/css/structure.css'
import '@ionic/vue/css/typography.css'

/* Optional CSS utilities */
import '@ionic/vue/css/padding.css'
import '@ionic/vue/css/float-elements.css'
import '@ionic/vue/css/text-alignment.css'
import '@ionic/vue/css/text-transformation.css'
import '@ionic/vue/css/flex-utils.css'
import '@ionic/vue/css/display.css'

/* AquaFlow theme: our own light + dark tokens, then global styles */
import './theme/variables.css'
import './theme/global.css'
import './theme/tailwind.css' // Tailwind utilities (no reset), added by the team

// Set light/dark before anything shows, so there's no flash
initTheme()
initSpotlight()

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const pinia = createPinia()

const app = createApp(App)
  // no page animations if the user asked for less motion; our own fade otherwise
  .use(IonicVue, { animated: !reduceMotion, navAnimation: oceanPageTransition })
  .use(pinia)
  .use(router)

// If the server says our login expired (401), log out and go to the login screen
setUnauthorizedHandler(() => {
  useAuthStore(pinia).logout()
  router.replace({ name: 'login' })
})

// Wait for the first route to load before showing the app (avoids a flash)
router.isReady().then(() => {
  app.mount('#app')
})
