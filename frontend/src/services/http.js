// The ONE axios instance the whole app uses.
//  - Adds "Authorization: Bearer <token>" to every request (request interceptor).
//  - Turns every failure into one ApiError shape (response interceptor),
//    so screens never dig through raw axios errors.
import axios, { AxiosError } from 'axios'

import { env } from '@/config/env'
import { tokenStorage } from './tokenStorage'

/** @typedef {import('@/types/api').ApiError} ApiError */

export const http = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 15_000, // 15s — mobile data can be slow, but don't hang forever
  headers: { Accept: 'application/json' },
})

// ---- Request: attach the JWT ----
http.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// ---- 401 hook: the auth store (Phase 2) registers "log out + go to login" here ----
/** @type {(() => void) | null} */
let unauthorizedHandler = null

/** @param {(() => void) | null} handler */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

// ---- Response: normalize errors ----
/**
 * @param {unknown} error
 * @returns {ApiError}
 */
export function toApiError(error) {
  if (!axios.isAxiosError(error)) {
    return { kind: 'server', status: null, message: 'Something went wrong. Please try again.' }
  }

  if (error.code === AxiosError.ECONNABORTED || error.code === AxiosError.ETIMEDOUT) {
    return { kind: 'timeout', status: null, message: 'The server took too long to answer. Check your signal and try again.' }
  }
  if (!error.response) {
    return { kind: 'network', status: null, message: "Can't reach the AquaFlow server. Check your connection." }
  }

  const status = error.response.status
  const detail = error.response.data?.detail
  const text = typeof detail === 'string' ? detail : null

  switch (status) {
    case 401:
      unauthorizedHandler?.()
      return { kind: 'unauthorized', status, message: text ?? 'Your session has ended. Please log in again.', details: detail }
    case 403:
      return { kind: 'forbidden', status, message: text ?? "Your account isn't allowed to do this.", details: detail }
    case 404:
      return { kind: 'not_found', status, message: text ?? 'Not found.', details: detail }
    case 409:
      return { kind: 'conflict', status, message: text ?? 'This was changed by someone else. Refresh and try again.', details: detail }
    case 422: {
      // FastAPI validation errors: detail = [{ loc: [...], msg: "...", type: "..." }, ...]
      const first = Array.isArray(detail) ? detail[0] : undefined
      return { kind: 'validation', status, message: text ?? first?.msg ?? 'Some fields are invalid.', details: detail }
    }
    default:
      return { kind: 'server', status, message: text ?? 'Server error. Please try again.', details: detail }
  }
}

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error)),
)