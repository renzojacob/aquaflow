<!--
  ReasonSheet — bottom sheet that asks WHY before rejecting or cancelling.
  The reason is required because the customer sees it.
  Usage: <ReasonSheet :is-open="open" title="Reject AF-1061?" confirm-label="Reject order"
           :presets="['Out of stock', 'Outside delivery area']" @close="open = false" @confirm="doReject" />
-->
<script setup>
import { ref, watch } from 'vue'
import { IonContent, IonModal } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import TextField from '@/components/form/TextField.vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  title: { type: String, required: true },
  message: { type: String, default: 'The customer will see this reason.' },
  confirmLabel: { type: String, required: true },
  presets: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'confirm'])

const reason = ref('')
const error = ref('')

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      reason.value = ''
      error.value = ''
    }
  },
)

function submit() {
  if (reason.value.trim().length < 3) {
    error.value = 'Pick or type a reason.'
    return
  }
  emit('confirm', reason.value.trim())
}
</script>

<template>
  <ion-modal :is-open="isOpen" :breakpoints="[0, 0.7, 1]" :initial-breakpoint="0.7" @did-dismiss="emit('close')">
    <ion-content>
      <form class="sheet" novalidate @submit.prevent="submit">
        <header>
          <h2 class="af-h2">{{ title }}</h2>
          <p class="af-small">{{ message }}</p>
        </header>

        <div v-if="presets.length" class="chips" role="group" aria-label="Common reasons">
          <button v-for="p in presets" :key="p" type="button" class="chip" :aria-pressed="reason === p" @click="(reason = p), (error = '')">
            {{ p }}
          </button>
        </div>

        <TextField v-model="reason" label="Reason" required multiline :maxlength="160" :error="error" />

        <div class="actions">
          <AppButton variant="secondary" @click="emit('close')">Go back</AppButton>
          <AppButton type="submit" variant="danger" :loading="busy">{{ confirmLabel }}</AppButton>
        </div>
      </form>
    </ion-content>
  </ion-modal>
</template>

<style scoped>
.sheet { display: grid; gap: var(--af-s4); padding: var(--af-s6) var(--af-s4) var(--af-s6); max-width: 560px; margin: 0 auto; }
.sheet header { display: grid; gap: 6px; }
.sheet h2, .sheet p { margin: 0; }
.chips { display: flex; flex-wrap: wrap; gap: var(--af-s2); }
.chip {
  min-height: 44px;
  padding: 0 16px;
  border-radius: var(--af-r-pill);
  border: 1.5px solid var(--af-line-strong);
  background: var(--af-surface);
  color: var(--af-ink);
  font: 700 14px var(--af-font);
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease);
}
.chip:hover { border-color: var(--af-danger); }
.chip[aria-pressed='true'] { border-color: var(--af-danger); background: var(--af-danger-tint); color: var(--af-danger); }
.actions { display: flex; justify-content: flex-end; gap: var(--af-s2); flex-wrap: wrap; }
</style>
