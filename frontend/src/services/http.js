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
  const body = error.response.data
  const detail = body?.detail
  const text = typeof detail === 'string' ? detail : null

  switch (status) {
    case 400: {
      // Django REST Framework validation errors come back shaped like
      // { "password": ["This password is too common."], "email": [...] }
      // — not { detail: "..." } — so pull the first field's first message out.
      const message = text ?? firstFieldError(body) ?? 'Some fields are invalid. Please check your entries.'
      return { kind: 'validation', status, message, details: body }
    }
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
      return { kind: 'server', status, message: text ?? firstFieldError(body) ?? 'Server error. Please try again.', details: detail }
  }
}

/**
 * Pull the first readable message out of a DRF field-error body, e.g.
 * { "password": ["This password is too common."] } -> "This password is too common."
 * { "non_field_errors": ["..."] } also works. Returns null if the shape doesn't match.
 */
function firstFieldError(body) {
  if (!body || typeof body !== 'object') return null
  for (const value of Object.values(body)) {
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
    if (typeof value === 'string') return value
  }
  return null
}

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error)),
)