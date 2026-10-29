// Page change animation: the old page fades out, then the new one rises in.
// (Our pages are see-through glass over the ocean, so they must never overlap.)
import { createAnimation } from '@ionic/vue'

export function oceanPageTransition(_baseEl, opts) {
  const entering = createAnimation()
    .addElement(opts.enteringEl)
    .beforeRemoveClass('ion-page-invisible')
    .fromTo('opacity', '0', '1')
    .fromTo('transform', 'translateY(14px) scale(0.99)', 'translateY(0) scale(1)')
    .delay(110)
    .duration(240)
    .easing('cubic-bezier(0.16, 1, 0.3, 1)')

  const root = createAnimation().addAnimation(entering)

  if (opts.leavingEl) {
    root.addAnimation(
      createAnimation()
        .addElement(opts.leavingEl)
        .fromTo('opacity', '1', '0')
        .duration(120)
        .easing('ease-in'),
    )
  }
  return root
}
