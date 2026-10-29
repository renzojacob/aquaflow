<!--
  OrderAdminPanel — everything the dispatcher needs about one order, plus the next actions.
  Used in the desktop split view (right side) and in the phone detail page.
  Emits "changed" with the updated order after any action.
-->
<script setup>
import { computed, ref, watch } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import ReasonSheet from '@/components/dispatcher/ReasonSheet.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { DISPATCHER_NEXT, MAX_ATTEMPTS } from '@/constants/orderStatus'
import { showToast } from '@/composables/useToast'
import { getOrderForStaff, runOrderAction } from '@/services/dispatcherService'
import { PERIODS, containers, dateTimeOf, friendlyDay, peso } from '@/utils/format'

const props = defineProps({
  orderId: { type: String, required: true },
})
const emit = defineEmits(['changed'])

const order = ref(null)
const loading = ref(true)
const error = ref(null)
const busyAction = ref('')
const sheet = ref(null) // 'reject' | 'cancel' | null

const REJECT_REASONS = ['Outside delivery area', 'Not enough stock today', 'Duplicate order', 'Could not reach customer']
const CANCEL_REASONS = ['Customer asked to cancel', 'Not enough stock', 'Vehicle problem', 'Could not reach customer']

async function load() {
  loading.value = !order.value || order.value.id !== props.orderId
  error.value = null
  try {
    order.value = await getOrderForStaff(props.orderId)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
watch(() => props.orderId, load, { immediate: true })

const actions = computed(() => {
  if (!order.value) return []
  const list = DISPATCHER_NEXT[order.value.status] ?? []
  // A failed delivery is re-planned only once
  return list.filter((a) => a.action !== 'replan' || order.value.attempts < MAX_ATTEMPTS)
})

const DONE_TEXT = {
  confirm: 'confirmed',
  prepare: 'is being prepared',
  ready: 'is ready for pickup',
  reject: 'rejected',
  cancel: 'cancelled',
  replan: 'will go on the next trip',
}

async function run(action, reason = '') {
  busyAction.value = action
  try {
    order.value = await runOrderAction(order.value.id, action, reason)
    sheet.value = null
    showToast(`${order.value.code} ${DONE_TEXT[action]}`, 'success')
    emit('changed', order.value)
  } catch (e) {
    showToast(e.message, 'danger')
    if (e.kind === 'conflict') {
      await load()
      emit('changed', order.value)
    }
  } finally {
    busyAction.value = ''
  }
}

function onAction(a) {
  if (a.action === 'reject' || a.action === 'cancel') sheet.value = a.action
  else run(a.action)
}
</script>

<template>
  <div class="panel">
    <SkeletonList v-if="loading" :rows="5" :avatar="false" />

    <div v-else-if="error" class="err" role="alert">
      <b>Couldn't load this order</b>
      <p>{{ error.message }}</p>
      <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
    </div>

    <template v-else-if="order">
      <header class="head">
        <div>
          <p class="af-small">{{ order.code }} · placed {{ dateTimeOf(order.created_at) }}</p>
          <h2 class="af-h2">{{ order.customer.name }}</h2>
          <a class="phone" :href="`tel:${order.customer.phone}`">{{ order.customer.phone }}</a>
        </div>
        <StatusPill :status="order.status" />
      </header>

      <!-- Next actions -->
      <div v-if="actions.length" class="actions">
        <AppButton
          v-for="a in actions"
          :key="a.action"
          :variant="a.variant"
          :size="a.variant === 'primary' ? 'lg' : 'md'"
          :loading="busyAction === a.action"
          :disabled="!!busyAction && busyAction !== a.action"
          @click="onAction(a)"
        >
          {{ a.label }}
        </AppButton>
      </div>
      <p v-if="order.status === 'ready_for_pickup'" class="hint">Next: assign it to a trip in <b>Plan deliveries</b>.</p>
      <p v-if="order.status === 'out_for_delivery' && order.trip" class="hint">On trip {{ order.trip.code }} with {{ order.trip.rider_name }}.</p>

      <!-- Key facts -->
      <dl class="facts">
        <div><dt>Containers</dt><dd class="big">{{ order.quantity }}</dd></div>
        <div><dt>Empties back</dt><dd class="big">{{ order.empties_to_return }}</dd></div>
        <div><dt>When</dt><dd>{{ friendlyDay(order.delivery_date) }}<br />{{ PERIODS[order.period].label }}</dd></div>
        <div><dt>Collect</dt><dd>{{ peso(order.total) }}<br /><span class="af-small">cash</span></dd></div>
      </dl>

      <section class="block">
        <h3 class="af-caption">Deliver to</h3>
        <p class="addr">
          <b>{{ order.address.street }}, {{ order.address.barangay }}</b><br />
          <i>{{ order.address.landmark }}</i>
        </p>
        <p v-if="order.notes" class="note">“{{ order.notes }}”</p>
        <MapPicker :model-value="order.address" readonly height="180px" :zoom="16" />
      </section>

      <section class="block">
        <h3 class="af-caption">History</h3>
        <OrderTimeline :order="order" staff />
      </section>

      <p class="af-small foot">{{ containers(order.quantity) }} · attempt {{ Math.max(order.attempts, 1) }} of {{ MAX_ATTEMPTS }}</p>
    </template>

    <ReasonSheet
      :is-open="sheet === 'reject'"
      :title="`Reject ${order?.code}?`"
      confirm-label="Reject order"
      :presets="REJECT_REASONS"
      :busy="busyAction === 'reject'"
      @close="sheet = null"
      @confirm="(r) => run('reject', r)"
    />
    <ReasonSheet
      :is-open="sheet === 'cancel'"
      :title="`Cancel ${order?.code}?`"
      message="The customer will see this reason. Reserved stock is released."
      confirm-label="Cancel order"
      :presets="CANCEL_REASONS"
      :busy="busyAction === 'cancel'"
      @close="sheet = null"
      @confirm="(r) => run('cancel', r)"
    />
  </div>
</template>

<style scoped>
.panel { display: grid; gap: var(--af-s5); align-content: start; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--af-s3); flex-wrap: wrap; }
.head p, .head h2 { margin: 0; }
.head h2 { margin-top: 6px; }
.phone { display: inline-flex; align-items: center; min-height: 32px; margin-top: 2px; color: var(--af-primary); font-weight: 750; text-decoration: none; font-variant-numeric: tabular-nums; }
.phone:hover { text-decoration: underline; text-underline-offset: 3px; }

.actions { display: flex; gap: var(--af-s2); flex-wrap: wrap; align-items: center; }
.hint { margin: 0; padding: 12px 16px; border-radius: var(--af-r-sm); background: var(--af-primary-tint); color: var(--af-primary); border: 1px solid color-mix(in srgb, var(--af-primary) 25%, transparent); font-size: 14px; font-weight: 600; }

.facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--af-s2); margin: 0; }
.facts > div { padding: var(--af-s3) var(--af-s4); border-radius: var(--af-r-sm); background: var(--af-surface-2); border: 1px solid var(--af-line); min-width: 0; }
.facts dt { font-family: var(--af-mono); font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--af-ink-2); }
.facts dd { margin: 6px 0 0; font-size: 14px; font-weight: 650; font-variant-numeric: tabular-nums; }
.facts dd.big { font-family: var(--af-display); font-size: 30px; font-weight: 700; letter-spacing: -0.03em; line-height: 1; }

.block { display: grid; gap: var(--af-s3); }
.block h3 { margin: 0; }
.addr { margin: 0; line-height: 1.55; }
.note { margin: 0; padding: 12px 16px; border: 1px solid color-mix(in srgb, var(--af-amber) 40%, transparent); background: var(--af-amber-tint); color: var(--af-ink); border-radius: var(--af-r-sm); font-size: 14px; line-height: 1.5; }
.foot { margin: 0; }

.err { display: grid; gap: var(--af-s2); justify-items: start; }
.err b { color: var(--af-danger); font-weight: 800; }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 520px) {
  .facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
