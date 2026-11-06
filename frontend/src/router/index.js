// All screens and who may open them.
// We import createRouter from '@ionic/vue-router' (not 'vue-router')
// so Ionic can animate page transitions and keep the back button working.
//
// SECURITY NOTE for the panel: these guards only decide which screens to SHOW.
// The FastAPI backend checks the user's role on every request; that is the real protection.
import { createRouter, createWebHistory } from '@ionic/vue-router'

import RoleShell from '@/components/layout/RoleShell.vue'
import RiderDonePage from '@/views/rider/RiderDonePage.vue'
import RiderSyncPage from '@/views/rider/RiderSyncPage.vue'
import RiderTripPage from '@/views/rider/RiderTripPage.vue'
import { useAuthStore } from '@/stores/auth'

const soon = () => import('@/views/shared/ComingSoonPage.vue')
const more = () => import('@/views/shared/MorePage.vue')

/** Placeholder route for a screen built in a later phase. */
const placeholder = (path, title, phase, planned) => ({ path, component: soon, meta: { title, phase, planned } })

const routes = [
  { path: '/', redirect: '/login' },

  // ---------- Public ----------
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginPage.vue'), meta: { public: true, guestOnly: true } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterPage.vue'), meta: { public: true, guestOnly: true } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/auth/ForgotPasswordPage.vue'), meta: { public: true, guestOnly: true } },
  { path: '/design', name: 'design', component: () => import('@/views/DesignPage.vue'), meta: { public: true } },
  { path: '/health-check', name: 'health-check', component: () => import('@/views/HealthCheckPage.vue'), meta: { public: true } },

  // ---------- Customer (Phase 3) ----------
  {
    path: '/customer/',
    component: RoleShell,
    meta: { role: 'customer' },
    children: [
      { path: '', redirect: '/customer/home' },
      { path: 'home', component: () => import('@/views/customer/HomePage.vue') },
      { path: 'order', component: () => import('@/views/customer/NewOrderPage.vue') },
      { path: 'orders', component: () => import('@/views/customer/OrdersPage.vue') },
      { path: 'orders/:id', component: () => import('@/views/customer/OrderDetailPage.vue') },
      { path: 'profile', component: () => import('@/views/customer/ProfilePage.vue') },
    ],
  },

  // ---------- Dispatcher (Phase 4) ----------
  {
    path: '/dispatcher/',
    component: RoleShell,
    meta: { role: 'dispatcher' },
    children: [
      { path: '', redirect: '/dispatcher/orders' },
      { path: 'orders', component: () => import('@/views/dispatcher/OrdersQueuePage.vue') },
      { path: 'orders/:id', component: () => import('@/views/dispatcher/OrderAdminPage.vue') },
      { path: 'plan', component: () => import('@/views/dispatcher/PlanPage.vue') },
      { path: 'stock', component: () => import('@/views/dispatcher/StockPage.vue') },
      { path: 'conflicts', component: () => import('@/views/dispatcher/ConflictsPage.vue') },
      { path: 'more', component: more },
    ],
  },

  // ---------- Rider (Phase 5) ----------
  {
    path: '/rider/',
    component: RoleShell,
    meta: { role: 'rider' },
    children: [
      { path: '', redirect: '/rider/trip' },
      // Bundled with the app, not loaded on demand: a rider with no signal must still be able
      // to open every rider screen (Feature B)
      { path: 'trip', component: RiderTripPage },
      { path: 'done', component: RiderDonePage },
      { path: 'sync', component: RiderSyncPage },
      { path: 'more', component: more },
    ],
  },

  // ---------- Owner (Phase 6) ----------
  {
    path: '/owner/',
    component: RoleShell,
    meta: { role: 'owner' },
    children: [
      { path: '', redirect: '/owner/dashboard' },
      { path: 'dashboard', component: () => import('@/views/owner/OwnerDashboardPage.vue') },
      { path: 'queue', component: () => import('@/views/dispatcher/OrdersQueuePage.vue') },
      { path: 'queue/:id', component: () => import('@/views/dispatcher/OrderAdminPage.vue') },
      { path: 'stock', component: () => import('@/views/dispatcher/StockPage.vue') },
      placeholder('forecast', 'Forecasting', 6, ['Forecast vs actual chart', 'Backtest error: naive, weekday average, Holt-Winters', 'Peak weekday × hour heatmap', 'Preparation recommendation and trips needed']),
      placeholder('supplies', 'Stock & supplies', 6, ['Caps, seals, filters: days left', 'Restock alerts']),
      { path: 'reports', component: () => import('@/views/owner/ReportsPage.vue') },
      { path: 'users', component: () => import('@/views/owner/UsersPage.vue') },
      { path: 'vehicles', component: () => import('@/views/owner/VehiclesPage.vue') },
      { path: 'products', component: () => import('@/views/owner/ProductsPage.vue') },
      { path: 'service-area', component: () => import('@/views/owner/ServiceAreaPage.vue') },
      { path: 'more', component: more },
    ],
  },

  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  // Logged-in users don't need the login/register screens
  if (to.meta.guestOnly && auth.isLoggedIn) return auth.homePath
  if (to.meta.public) return true

  // Everything else needs a login
  if (!auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }

  // ...and the right role
  const needed = to.matched.find((r) => r.meta.role)?.meta.role
  if (needed && needed !== auth.role) return auth.homePath

  return true
})

export default router
