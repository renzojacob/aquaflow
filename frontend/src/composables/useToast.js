// Short message at the bottom of the screen ("Order placed").
import { toastController } from '@ionic/vue'

/**
 * @param {string} message
 * @param {'success' | 'danger' | 'info'} [tone]
 */
export async function showToast(message, tone = 'info') {
  const toast = await toastController.create({
    message,
    duration: 2600,
    position: 'bottom',
    color: tone === 'info' ? 'secondary' : tone,
    buttons: [{ text: 'OK', role: 'cancel' }],
  })
  await toast.present()
}
