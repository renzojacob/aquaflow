// Count a number up from 0 when it first appears (once), then follow changes instantly.
// Skipped completely for people who turned on "reduce motion".
import { onMounted, ref, watch } from 'vue'

const reduce = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** @param {import('vue').Ref<number> | (() => number)} source */
export function useCountUp(source, duration = 1400) {
  const read = () => (typeof source === 'function' ? source() : source.value) ?? 0
  const shown = ref(reduce ? read() : 0)
  let mounted = false
  let animated = false

  function run(to) {
    if (reduce) {
      shown.value = to
      return
    }
    const from = shown.value
    const t0 = performance.now()
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / duration)
      const eased = 1 - Math.pow(1 - p, 4)
      shown.value = Math.round(from + (to - from) * eased)
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  // Data usually arrives after the page mounts: animate the FIRST real number, once.
  function update(v) {
    if (!mounted) return
    if (!animated && v) {
      animated = true
      run(v)
    } else if (animated || reduce) {
      shown.value = v // later changes: no animation, just the new number
    }
  }
  onMounted(() => {
    mounted = true
    update(read())
  })
  watch(read, update)
  return shown
}
