<!--
  DeliverySheet — the two steps that move an order on the road, until the Rider app exists:
    mode="dispatch": pick who carries it, then "Send out"
    mode="deliver":  count the empties collected, then "Mark as delivered"
  Emits confirm with { rider_id } or { empties_collected }.
-->
<script setup>
import { ref, watch } from 'vue'
import { IonContent, IonIcon, IonModal } from '@ionic/vue'
import { bicycleOutline, checkmarkCircle } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import { linesText } from '@/constants/cart'
import { listRiders } from '@/services/dispatcherService'
import { containers, initials, peso } from '@/utils/format'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  mode: { type: String, default: 'dispatch' }, // dispatch | deliver
  order: { type: Object, default: null },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'confirm'])

const riders = ref([])
const riderId = ref('')
const empties = ref(0)
const loadingRiders = ref(false)
const riderError = ref('')

watch(
  () => props.isOpen,
  async (open) => {
    if (!open || !props.order) return
    empties.value = props.order.empties_to_return ?? 0
    if (props.mode !== 'dispatch') return
    loadingRiders.value = true
    riderError.value = ''
    try {
      riders.value = await listRiders()
      // Default: the rider with the fewest orders out right now
      riderId.value = [...riders.value].sort((a, b) => a.on_road - b.on_road)[0]?.id ?? ''
    } catch (e) {
      riderError.value = e.message
    } finally {
      loadingRiders.value = false
    }
  },
)

function submit() {
  emit('confirm', props.mode === 'dispatch' ? { rider_id: riderId.value || undefined } : { empties_collected: empties.value })
}
</script>

<template>
  <ion-modal :is-open="isOpen" :breakpoints="[0, 0.75, 1]" :initial-breakpoint="0.75" @did-dismiss="emit('close')">
    <ion-content>
      <form v-if="order" class="sheet" novalidate @submit.prevent="submit">
        <header>
          <h2 class="af-h2">{{ mode === 'dispatch' ? `Send ${order.code} out` : `Deliver ${order.code}` }}</h2>
          <p class="af-small">
            {{ order.customer?.name }}: {{ linesText(order) }} to {{ order.address.barangay }}. Collect {{ peso(order.total) }} in cash.
          </p>
        </header>

        <template v-if="mode === 'dispatch'">
          <p class="lbl" id="rider-lbl">Who is bringing it?</p>
          <p v-if="loadingRiders" class="af-small">Loading riders…</p>
          <p v-else-if="riderError" class="af-small err">{{ riderError }}</p>
          <div v-else class="riders" role="radiogroup" aria-labelledby="rider-lbl">
            <button
              v-for="r in riders"
              :key="r.id"
              type="button"
              role="radio"
              class="rider"
              :aria-checked="riderId === r.id"
              @click="riderId = r.id"
            >
              <span class="rider__av" aria-hidden="true">{{ initials(r.name) }}</span>
              <span class="rider__text">
                <b>{{ r.name }}</b>
                <span>{{ r.on_road ? `${r.on_road} order${r.on_road > 1 ? 's' : ''} out now` : 'Free now' }}</span>
              </span>
              <ion-icon v-if="riderId === r.id" :icon="checkmarkCircle" class="rider__tick" aria-hidden="true" />
            </button>
            <button type="button" role="radio" class="rider" :aria-checked="riderId === ''" @click="riderId = ''">
              <span class="rider__av rider__av--none" aria-hidden="true"><ion-icon :icon="bicycleOutline" /></span>
              <span class="rider__text"><b>Don't name a rider</b><span>The customer won't see who is coming</span></span>
              <ion-icon v-if="riderId === ''" :icon="checkmarkCircle" class="rider__tick" aria-hidden="true" />
            </button>
          </div>
          <p v-if="!riders.length && !loadingRiders" class="af-small">No rider accounts yet. The owner can add riders on the Users screen.</p>
        </template>

        <template v-else>
          <p class="lbl">Empty containers collected</p>
          <div class="emp">
            <QuantityStepper v-model="empties" :min="0" :max="50" label="Empty containers collected" unit="empties" />
            <p class="af-small">The customer said {{ order.empties_to_return }}. Change it if the rider got a different number.</p>
          </div>
        </template>

        <div class="actions">
          <AppButton variant="secondary" @click="emit('close')">Go back</AppButton>
          <AppButton type="submit" :loading="busy">{{ mode === 'dispatch' ? 'Send out for delivery' : 'Mark as delivered' }}</AppButton>
        </div>
      </form>
    </ion-content>
  </ion-modal>
</template>

<style scoped>
.sheet { display: grid; gap: 16px; padding: 32px 16px; max-width: 560px; margin: 0 auto; }
.sheet header { display: grid; gap: 6px; }
.sheet h2, .sheet p { margin: 0; }
.lbl { font-size: 14px; font-weight: 800; }
.err { color: var(--af-danger); }
.riders { display: grid; gap: 8px; }
.rider {
  display: grid;
  grid-template-columns: 44px 1fr 22px;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 18px;
  border: 1.5px solid var(--af-line);
  background: var(--af-surface-2);
  color: var(--af-ink);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
}
.rider[aria-checked='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); }
.rider__av { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: linear-gradient(140deg, #b9b4ff, #4fe0d2); color: #04161d; font-weight: 800; }
.rider__av--none { background: var(--af-surface-3); color: var(--af-ink-2); font-size: 20px; }
.rider__text { display: grid; gap: 2px; }
.rider__text b { font-size: 15px; font-weight: 800; }
.rider__text span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); }
.rider__tick { color: var(--af-primary); font-size: 22px; }
.emp { display: grid; justify-items: center; gap: 12px; padding: 16px; border-radius: 20px; background: var(--af-surface-2); text-align: center; }
.actions { display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
</style>
