const API_BASE = '/api'
const TOKEN_KEY = 'raara.access_token'

let unauthorizedHandler = () => {}

export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function getStoredToken() {
  return window.sessionStorage.getItem(TOKEN_KEY)
}

export function storeToken(token) {
  if (token) window.sessionStorage.setItem(TOKEN_KEY, token)
  else window.sessionStorage.removeItem(TOKEN_KEY)
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler || (() => {})
}

export async function apiRequest(path, { method = 'GET', body, token = getStoredToken(), headers = {}, onUploadProgress, ...options } = {}) {
  const requestHeaders = new Headers(headers)
  if (token) requestHeaders.set('Authorization', `Bearer ${token}`)
  if (body != null && !(body instanceof FormData)) requestHeaders.set('Content-Type', 'application/json')
  requestHeaders.set('Accept', 'application/json')
  if (body instanceof FormData && typeof onUploadProgress === 'function') {
    return uploadWithProgress(path, { method, body, token, headers: requestHeaders, onUploadProgress })
  }
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      method,
      headers: requestHeaders,
      body: body == null ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Could not reach RAARA. Check your connection and try again.', 0)
  }
  if (response.status === 204) return null
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) unauthorizedHandler()
    const detail = payload?.detail
    const message = typeof detail === 'string' ? detail : detail?.message || `Request failed (${response.status}).`
    throw new ApiError(message, response.status, detail)
  }
  return payload
}

function uploadWithProgress(path, { method, body, token, headers, onUploadProgress }) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open(method, `${API_BASE}${path}`)
    headers.forEach((value, key) => request.setRequestHeader(key, value))
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onUploadProgress(Math.round((event.loaded / event.total) * 100))
    }
    request.onerror = () => reject(new ApiError('Could not reach RAARA. Check your connection and try again.', 0))
    request.onload = () => {
      if (request.status === 204) return resolve(null)
      let payload = null
      try { payload = JSON.parse(request.responseText) } catch { /* Keep malformed responses generic. */ }
      if (request.status < 200 || request.status >= 300) {
        if (request.status === 401 && token) unauthorizedHandler()
        const detail = payload?.detail
        const message = typeof detail === 'string' ? detail : detail?.message || `Request failed (${request.status}).`
        return reject(new ApiError(message, request.status, detail))
      }
      resolve(payload)
    }
    request.send(body)
  })
}

export function createIdempotencyKey() {
  return window.crypto.randomUUID()
}

export function formatApiError(error) {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'You do not have permission to perform this action.'
    if (error.status === 404) return 'This item is no longer available.'
    if (error.status === 409) return error.message || 'This request conflicts with the current state.'
    if (error.status === 503) return error.message || 'This service is temporarily unavailable. Please try again.'
  }
  return error?.message || 'Something went wrong. Please try again.'
}

