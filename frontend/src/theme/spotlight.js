// Cursor spotlight: tells the card under the mouse where the mouse is,
// so its ::after light (global.css) can follow it. Desktop only, purely visual.
export function initSpotlight() {
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
  let frame = 0
  document.addEventListener(
    'pointermove',
    (e) => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const el = e.target instanceof Element ? e.target.closest('.af-card, .af-spot') : null
        if (!el) return
        const r = el.getBoundingClientRect()
        el.style.setProperty('--mx', `${e.clientX - r.left}px`)
        el.style.setProperty('--my', `${e.clientY - r.top}px`)
      })
    },
    { passive: true },
  )
}
