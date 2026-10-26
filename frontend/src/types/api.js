// Shapes of the data our backend sends, written as JSDoc comments.
// This file has no runtime code. VS Code reads these comments and gives
// autocomplete + warnings when we tag variables with them.
// Rule: when a backend Pydantic schema changes, update its @typedef here too.

/**
 * Mirrors backend/app/schemas/health.py -> HealthResponse
 * @typedef {Object} HealthResponse
 * @property {'ok' | 'degraded'} status
 * @property {string} app
 * @property {string} version
 * @property {string} environment
 * @property {'up' | 'down'} database
 * @property {string | null} database_error
 * @property {string} server_time  ISO 8601, UTC
 */

/**
 * Every failed request becomes this one shape, so screens handle errors the same way.
 * @typedef {'network' | 'timeout' | 'unauthorized' | 'forbidden' | 'not_found' | 'validation' | 'conflict' | 'server'} ApiErrorKind
 */

/**
 * @typedef {Object} ApiError
 * @property {ApiErrorKind} kind
 * @property {number | null} status
 * @property {string} message  safe to show to the user
 * @property {unknown} [details]  raw backend detail, for debugging / field errors
 */

export {}