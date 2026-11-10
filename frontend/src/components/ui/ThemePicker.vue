<!--
  ThemePicker — choose a brand (Ocean / Forest / Sunset) and a mode (Light / Dark / Auto).
  Each brand card is a tiny preview of that look. Works for every role.
  Usage: <ThemePicker />   or   <ThemePicker compact />  (sidebar: swatches in one row)
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import { checkmark } from 'ionicons/icons'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import { useTheme } from '@/composables/useTheme'

defineProps({ compact: { type: Boolean, default: false } })

const { brand, mode, resolved, setBrand, setMode, BRANDS, MODES } = useTheme()
</script>

<template>
  <div class="tp" :class="{ 'tp--compact': compact }">
    <div class="tp__brands" role="radiogroup" aria-label="Color theme">
      <button
        v-for="b in BRANDS"
        :key="b.id"
        type="button"
        role="radio"
        class="tp__brand"
        :class="{ 'is-on': brand === b.id }"
        :aria-checked="brand === b.id"
        :aria-label="`${b.name} theme: ${b.tagline}`"
        :data-brand="b.id"
        :data-theme="resolved"
        @click="setBrand(b.id)"
      >
        <!-- mini preview: page, a card, a button, a glow -->
        <span class="tp__preview" aria-hidden="true">
          <span class="tp__sky"></span>
          <span class="tp__card"><i></i><i></i></span>
          <span class="tp__btn"></span>
        </span>
        <span class="tp__meta">
          <b>{{ b.name }}</b>
          <span v-if="!compact">{{ b.tagline }}</span>
        </span>
        <span class="tp__check" aria-hidden="true"><ion-icon :icon="checkmark" /></span>
      </button>
    </div>
    <SegmentedControl :model-value="mode" :options="MODES" label="Light or dark" block @update:model-value="setMode" />
  </div>
</template>

<style scoped>
.tp { display: grid; gap: var(--af-s3); }
.tp__brands { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }

/* Each card is scoped to ITS brand (data-brand + data-theme on the button), so the tokens
   inside show that brand's colors even when another brand is active. */
.tp__brand {
  position: relative;
  display: grid;
  gap: 8px;
  padding: 8px;
  min-height: var(--af-touch);
  border-radius: 18px;
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease), transform var(--af-dur-1) var(--af-ease);
}
.tp__brand:hover { border-color: var(--af-line-strong); }
.tp__brand:active { transform: scale(0.98); }
.tp__brand.is-on { border-color: var(--af-brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--af-brand) 22%, transparent), var(--af-shadow-2); }

.tp__preview {
  position: relative;
  display: block;
  height: 64px;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(180deg, var(--af-bd-top) 0%, var(--af-bd-mid) 55%, var(--af-bd-bot) 100%);
  border: 1px solid var(--af-line);
}
.tp__sky {
  position: absolute;
  inset: -40% -20% auto -20%;
  height: 90%;
  background: radial-gradient(60% 70% at 30% 30%, var(--af-aur-1), transparent 70%), radial-gradient(50% 60% at 80% 20%, var(--af-aur-2), transparent 70%);
}
.tp__card {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  height: 30px;
  padding: 7px 8px;
  display: grid;
  gap: 5px;
  align-content: start;
  border-radius: 8px;
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  box-shadow: inset 0 1px 0 var(--af-glass-edge), var(--af-shadow-1);
  backdrop-filter: blur(6px);
}
.tp__card i { display: block; height: 4px; border-radius: 2px; background: var(--af-ink); opacity: 0.85; width: 55%; }
.tp__card i + i { width: 35%; opacity: 0.4; }
.tp__btn {
  position: absolute;
  right: 16px;
  bottom: 17px;
  width: 24px;
  height: 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--af-brand-g1), var(--af-brand-g2) 50%, var(--af-brand-g3));
  box-shadow: var(--af-glow);
}
.tp__meta { display: grid; gap: 1px; padding: 0 2px 2px; }
.tp__meta b { font-size: 14px; font-weight: 800; }
.tp__meta span { font-size: 12px; font-weight: 600; color: var(--af-ink-2); }
.tp__check {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--af-brand);
  color: var(--af-on-brand);
  font-size: 14px;
  opacity: 0;
  transform: scale(0.6);
  transition: opacity var(--af-dur) var(--af-ease), transform var(--af-dur) var(--af-ease-spring);
}
.tp__brand.is-on .tp__check { opacity: 1; transform: none; }

/* Compact (sidebar): three small swatches in a row, names under them */
.tp--compact .tp__brands { gap: 6px; }
.tp--compact .tp__brand { padding: 5px; gap: 5px; border-radius: 14px; }
.tp--compact .tp__preview { height: 40px; border-radius: 9px; }
.tp--compact .tp__card { left: 6px; right: 6px; bottom: 6px; height: 18px; padding: 4px 5px; gap: 3px; }
.tp--compact .tp__card i { height: 3px; }
.tp--compact .tp__btn { right: 10px; bottom: 10px; width: 16px; height: 10px; }
.tp--compact .tp__meta b { font-size: 12px; }
.tp--compact .tp__check { top: 9px; right: 9px; width: 18px; height: 18px; font-size: 12px; }

@media (max-width: 360px) {
  .tp__brands { grid-template-columns: 1fr; }
  .tp__brand { grid-template-columns: 96px 1fr; align-items: center; }
}
</style>
