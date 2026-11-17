import { afterEach, beforeEach, describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, apiRequest, createIdempotencyKey, formatApiError, getStoredToken, setUnauthorizedHandler, storeToken } from './api.js'

let calls
let stored
let originalFetch
let originalXHR

beforeEach(() => {
  calls = []
  stored = null
  originalFetch = globalThis.fetch
  originalXHR = globalThis.XMLHttpRequest
  globalThis.window = {
    sessionStorage: { getItem: () => stored, setItem: (_key, value) => { stored = value }, removeItem: () => { stored = null } },
    crypto: { randomUUID: () => 'b7bc9ad7-9111-43ec-9bce-4d153988dd01' },
  }
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init })
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  setUnauthorizedHandler(null)
})

afterEach(() => { globalThis.fetch = originalFetch; globalThis.XMLHttpRequest = originalXHR; setUnauthorizedHandler(null) })

describe('central API client', () => {
  it('reports upload progress and preserves bearer auth in multipart requests', async () => {
    let uploaded, request
    class MockXHR {
      constructor() { request = this; this.upload = {}; this.headers = {}; this.status = 201; this.responseText = '{"ok":true}' }
      open(method, url) { this.method = method; this.url = url }
      setRequestHeader(key, value) { this.headers[key] = value }
      send(body) { this.body = body; this.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 }); this.onload() }
    }
    globalThis.XMLHttpRequest = MockXHR
    storeToken('upload-token')
    const form = new FormData()
    form.set('file', new Blob(['synthetic pdf']))
    const result = await apiRequest('/documents/upload', {
      method: 'POST', body: form, onUploadProgress: (value) => { uploaded = value },
    })
    assert.equal(result.ok, true)
    assert.equal(uploaded, 50)
    assert.equal(request.url, '/api/documents/upload')
    assert.equal(request.headers.authorization, 'Bearer upload-token')
    assert.equal(request.headers['content-type'], undefined)
    assert.equal(request.body, form)
  })

  it('stores and clears the session token', () => {
    storeToken('secret-token')
    assert.equal(getStoredToken(), 'secret-token')
    storeToken(null)
    assert.equal(getStoredToken(), null)
  })

  it('attaches bearer credentials and serializes JSON bodies', async () => {
    storeToken('jwt-value')
    await apiRequest('/chat', { method: 'POST', body: { question: 'Attendance?' } })
    assert.equal(calls[0].url, '/api/chat')
    assert.equal(calls[0].init.headers.get('Authorization'), 'Bearer jwt-value')
    assert.equal(calls[0].init.headers.get('Content-Type'), 'application/json')
    assert.deepEqual(JSON.parse(calls[0].init.body), { question: 'Attendance?' })
  })

  it('does not attach a stale token to public registration or login calls', async () => {
    storeToken('stale-token')
    await apiRequest('/auth/login', { method: 'POST', token: null, body: { identifier: 'student', password: 'test' } })
    assert.equal(calls[0].init.headers.has('Authorization'), false)
  })

  it('preserves browser-generated multipart boundaries for PDF uploads', async () => {
    const form = new FormData()
    form.set('document_type', 'policy')
    await apiRequest('/documents/upload', { method: 'POST', body: form })
    assert.equal(calls[0].init.headers.has('Content-Type'), false)
    assert.equal(calls[0].init.body, form)
  })

  it('notifies auth state on an authenticated 401 and returns safe server errors', async () => {
    let unauthorized = 0
    storeToken('jwt-value')
    setUnauthorizedHandler(() => { unauthorized += 1 })
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Session expired.' }), { status: 401 })
    await assert.rejects(apiRequest('/conversations'), (error) => error instanceof ApiError && error.status === 401 && error.message === 'Session expired.')
    assert.equal(unauthorized, 1)
    assert.match(formatApiError(new ApiError('Unavailable.', 503)), /Unavailable/)
  })

  it('generates one UUID key that callers can retain for an idempotent retry', () => {
    const key = createIdempotencyKey()
    assert.equal(key, 'b7bc9ad7-9111-43ec-9bce-4d153988dd01')
  })

  it('reports a useful connection error without leaking implementation details', async () => {
    globalThis.fetch = async () => { throw new Error('socket failed') }
    await assert.rejects(apiRequest('/health', { token: null }), /Could not reach RAARA/)
  })
})
