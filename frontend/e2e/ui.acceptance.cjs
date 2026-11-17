const assert = require('node:assert/strict')
const { chromium } = require('playwright')

const baseUrl = process.env.RAARA_E2E_BASE_URL || 'http://127.0.0.1:5173/'
const cases = []
function test(name, run) { cases.push({ name, run }) }

function mockApi() {
  const data = {
    nextId: 3,
    conversations: [
      {
        id: 1, title: 'Synthetic test: Attendance overview', created_at: '2026-11-14T10:00:00Z',
        updated_at: '2026-11-14T10:05:00Z', messages: [
          { id: 1, role: 'user', content: 'What does this test document say?', created_at: '2026-11-14T10:00:00Z' },
          { id: 2, role: 'assistant', content: 'Synthetic evidence summary.', structured_response: { answer: 'Synthetic evidence summary.', evidence: [], sources: [], status: 'NOT_FOUND' }, created_at: '2026-11-14T10:05:00Z' },
        ],
      },
      {
        id: 2, title: 'Synthetic test: Grading question', created_at: '2026-11-13T10:00:00Z',
        updated_at: '2026-11-13T10:05:00Z', messages: [
          { id: 3, role: 'user', content: 'How is this test grade described?', created_at: '2026-11-13T10:00:00Z' },
          { id: 4, role: 'assistant', content: 'Synthetic grade passage.', structured_response: { answer: 'Synthetic grade passage.', evidence: [], sources: [], status: 'NOT_FOUND' }, created_at: '2026-11-13T10:05:00Z' },
        ],
      },
    ],
    documents: [
      {
        document_id: 41, document_name: 'Synthetic Attendance Policy (NOT OFFICIAL)',
        document_type: 'policy', verification_status: 'unverified', processing_status: 'indexed',
        vector_sync_status: 'synced', uploaded_at: '2026-11-14T09:00:00Z', page_count: 2, chunk_count: 2,
      },
      {
        document_id: 42, document_name: 'Synthetic Grading Notes (NOT OFFICIAL)',
        document_type: 'academic_notes', verification_status: 'unverified', processing_status: 'failed',
        vector_sync_status: 'failed', uploaded_at: '2026-11-13T09:00:00Z', page_count: 1, chunk_count: 0,
      },
    ],
    deletedIds: [],
    failNextChat: false,
    nextAnswer: null,
    lastChatRequest: null,
  }

  async function fulfill(route, status, body) {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: status === 204 ? '' : JSON.stringify(body),
    })
  }

  return {
    data,
    handler: async (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname.replace(/^\/api/, '')
      const method = route.request().method()
      if (path === '/health') return fulfill(route, 200, { status: 'ok' })
      if (path === '/health/ai') return fulfill(route, 200, {
        provider: 'groq', chat_model: 'mock-ui-model', credential_configured: false,
        embedding_provider: 'local', embedding_model: 'sentence-transformers/all-MiniLM-L6-v2', embedding_dimensions: 384,
      })
      if (path === '/auth/register' && method === 'POST') return fulfill(route, 201, { username: 'test.student' })
      if (path === '/auth/login' && method === 'POST') return fulfill(route, 200, { access_token: 'mock-ui-token', token_type: 'bearer', user: { id: 7, username: 'test.student', email: 'test@example.invalid', role: 'student', is_active: true } })
      if (path === '/auth/me') return fulfill(route, 200, { id: 7, username: 'test.student', email: 'test@example.invalid', role: 'student', is_active: true })
      if (path === '/documents') return fulfill(route, 200, data.documents)
      if (path === '/conversations' && method === 'GET') {
        return fulfill(route, 200, data.conversations.map(({ messages, ...item }) => ({ ...item, message_count: messages.length, question_count: messages.filter((message) => message.role === 'user').length })))
      }
      if (path === '/conversations' && method === 'POST') {
        const request = route.request().postDataJSON()
        const conversation = {
          id: data.nextId++, title: request.title || 'New conversation', created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(), messages: [],
        }
        data.conversations.unshift(conversation)
        return fulfill(route, 201, { ...conversation, message_count: 0, question_count: 0 })
      }
      const match = path.match(/^\/conversations\/(\d+)$/)
      if (match) {
        const id = Number(match[1])
        const conversation = data.conversations.find((item) => item.id === id)
        if (!conversation) return fulfill(route, 404, { detail: 'Conversation not found.' })
        if (method === 'GET') return fulfill(route, 200, { ...conversation, message_count: conversation.messages.length, question_count: conversation.messages.filter((message) => message.role === 'user').length })
        if (method === 'PATCH') {
          conversation.title = route.request().postDataJSON().title
          return fulfill(route, 200, { ...conversation, message_count: conversation.messages.length, question_count: conversation.messages.filter((message) => message.role === 'user').length })
        }
        if (method === 'DELETE') {
          data.deletedIds.push(id)
          data.conversations = data.conversations.filter((item) => item.id !== id)
          return fulfill(route, 204, null)
        }
      }
      if (path === '/chat' && method === 'POST') {
        if (data.failNextChat) {
          data.failNextChat = false
          return fulfill(route, 503, { detail: 'Generation is unavailable.' })
        }
        const request = route.request().postDataJSON()
        data.lastChatRequest = request
        const conversation = data.conversations.find((item) => item.id === request.conversation_id)
        const answer = /^\s*(hello|hi|hey)[!. ]*$/i.test(request.question)
          ? "Hello! I'm RAARA, your academic document assistant. What would you like to know?"
          : 'Synthetic test response. No policy claim is made.'
        const status = /^\s*(hello|hi|hey)[!. ]*$/i.test(request.question) ? 'CONVERSATIONAL' : 'NOT_FOUND'
        const response = data.nextAnswer || { answer, evidence: [], sources: [], status, validation: { citation_status: 'NOT_APPLICABLE', semantic_faithfulness: 'NOT_VERIFIED', unsupported_claims_flagged: false, issues: [] } }
        data.nextAnswer = null
        if (conversation) {
          conversation.messages.push(
            { id: data.nextId++, role: 'user', content: request.question, created_at: new Date().toISOString() },
            { id: data.nextId++, role: 'assistant', content: answer, structured_response: response, created_at: new Date().toISOString() },
          )
          conversation.updated_at = new Date().toISOString()
        }
        return fulfill(route, 200, response)
      }
      return fulfill(route, 404, { detail: `Unmocked UI test request: ${method} ${path}` })
    },
  }
}

async function createPage(browser, viewport = { width: 1365, height: 900 }) {
  const page = await browser.newPage({ viewport })
  const mock = mockApi()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await page.route('**/api/**', mock.handler)
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' })
  return { page, mock, errors }
}

async function signIn(page) {
  await page.getByLabel('Username or email').fill('test.student')
  await page.getByLabel('Password').fill('test-only-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('heading', { name: 'Academic Regulatory Assistant' }).waitFor()
}

test('registration and sign-in views submit and render the dashboard', async (browser) => {
  const { page } = await createPage(browser)
  await page.getByRole('button', { name: 'Create student account' }).click()
  await page.getByLabel('Username').fill('test.student')
  await page.getByLabel('Email').fill('test@example.invalid')
  await page.getByLabel('Password').fill('test-only-password')
  await page.getByRole('button', { name: 'Create account' }).click()
  await page.getByRole('status').filter({ hasText: 'Account created' }).waitFor()
  await signIn(page)
  await page.getByText('Backend connected').first().waitFor()
  await page.close()
})

test('overview shows real workspace counts and links to recent records', async (browser) => {
  const { page, mock, errors } = await createPage(browser)
  await signIn(page)
  await page.getByRole('heading', { name: 'Academic Regulatory Assistant' }).waitFor()
  assert.match(
    await page.locator('.overview-service-meta').innerText(),
    /Groq · not configured[\s\S]*Embeddings: local · sentence-transformers\/all-MiniLM-L6-v2 · 384 dimensions/i,
  )
  await page.locator('.overview-stat-card .overview-stat-value').first().waitFor()
  const cards = page.locator('.overview-stat-card')
  assert.equal(await cards.count(), 4)
  assert.match(await cards.nth(0).innerText(), /Total documents[\s\S]*2[\s\S]*1 awaiting review · 1 failed/i)
  assert.match(await cards.nth(1).innerText(), /Total conversations[\s\S]*2/)
  assert.match(await cards.nth(2).innerText(), /Questions asked[\s\S]*2/)
  assert.match(await cards.nth(3).innerText(), /Indexed documents[\s\S]*1/)
  await page.getByRole('button', { name: /Synthetic Attendance Policy/ }).click()
  await page.getByRole('heading', { name: 'My Documents' }).waitFor()
  await page.getByRole('button', { name: 'Overview' }).click()
  await page.getByRole('button', { name: /Attendance overview/ }).click()
  await page.getByRole('heading', { name: 'AI Assistant' }).waitFor()
  assert.equal(mock.data.conversations.length, 2)
  assert.deepEqual(errors, [])
  await page.close()
})

test('greeting interaction is conversational and creates a persisted history pair', async (browser) => {
  const { page, mock, errors } = await createPage(browser)
  await signIn(page)
  await page.getByRole('button', { name: 'AI Assistant' }).click()
  await page.locator('#question').fill('hello')
  await page.getByRole('button', { name: 'Send question' }).click()
  await page.getByText(/I'm RAARA, your academic document assistant/i).waitFor()
  assert.equal(mock.data.conversations.length, 3)
  assert.equal(mock.data.conversations[0].messages.length, 2)
  assert.equal(mock.data.conversations[0].messages[1].structured_response.status, 'CONVERSATIONAL')
  assert.deepEqual(errors, [])
  await page.close()
})

test('numbered answers and document coverage notes render accessibly', async (browser) => {
  const { page, mock, errors } = await createPage(browser)
  await signIn(page)
  mock.data.nextAnswer = {
    answer: '# Synthetic summary\n1. First distinct test finding.\n2. Second distinct test finding.',
    evidence: [], sources: [], status: 'PARTIALLY_SUPPORTED',
    coverage: 'Coverage limitation: this synthetic sample includes two pages.',
  }
  await page.getByRole('button', { name: 'AI Assistant', exact: true }).click()
  await page.locator('#question').fill('Summarize the synthetic test PDF in 10 points')
  await page.getByRole('button', { name: 'Send question' }).click()
  const answer = page.locator('.assistant-message')
  await answer.getByRole('heading', { name: 'Synthetic summary' }).waitFor()
  assert.equal(await answer.locator('ol > li').count(), 2)
  await answer.getByRole('note').filter({ hasText: 'Coverage limitation' }).waitFor()
  assert.deepEqual(errors, [])
  await page.close()
})

test('assistant document selector scopes the outgoing chat request', async (browser) => {
  const { page, mock } = await createPage(browser)
  await signIn(page)
  await page.getByRole('button', { name: 'AI Assistant', exact: true }).click()
  await page.getByLabel('Limit to document').selectOption('41')
  await page.locator('#question').fill('Summarize this PDF in 10 points')
  await page.getByRole('button', { name: 'Send question' }).click()
  await page.getByText('Synthetic test response. No policy claim is made.').waitFor()
  assert.equal(mock.data.lastChatRequest.document_id, 41)
  await page.close()
})

test('history switching, refresh restoration, rename and deletion track persisted counts', async (browser) => {
  const { page, mock } = await createPage(browser)
  await signIn(page)
  await page.getByRole('button', { name: 'Chat History', exact: true }).click()
  const firstEntry = page.locator('.history-entry').filter({ hasText: 'Attendance overview' })
  await firstEntry.getByRole('button', { name: /2 messages/ }).click()
  await page.getByText('Synthetic evidence summary.').waitFor()
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: 'AI Assistant' }).waitFor()
  await page.getByText('Synthetic evidence summary.').waitFor()
  await page.getByRole('button', { name: 'Conversation history' }).click()
  const secondEntry = page.locator('.history-entry').filter({ hasText: 'Grading question' })
  await secondEntry.getByRole('button', { name: /2 messages/ }).click()
  await page.getByText('Synthetic grade passage.').waitFor()
  await page.getByRole('button', { name: 'Conversation history' }).click()
  const renameEntry = page.locator('.history-entry').filter({ hasText: 'Attendance overview' })
  await renameEntry.getByRole('button', { name: 'Rename' }).click()
  await page.getByLabel('Conversation title').fill('Renamed synthetic history')
  await page.getByRole('button', { name: 'Save' }).click()
  await page.getByText('Renamed synthetic history').waitFor()
  page.once('dialog', (dialog) => dialog.accept())
  const deleteEntry = page.locator('.history-entry').filter({ hasText: 'Grading question' })
  await deleteEntry.getByRole('button', { name: 'Delete' }).click()
  await deleteEntry.waitFor({ state: 'detached' })
  assert.deepEqual(mock.data.deletedIds, [2])
  assert.equal(mock.data.conversations.find((item) => item.id === 1).messages.length, 2)
  await page.close()
})

test('failed first chat removes only the unused conversation and new conversation stays local', async (browser) => {
  const { page, mock } = await createPage(browser)
  await signIn(page)
  await page.getByRole('button', { name: 'New conversation' }).click()
  assert.equal(mock.data.conversations.length, 2)
  mock.data.failNextChat = true
  await page.locator('#question').fill('A synthetic failing request')
  await page.getByRole('button', { name: 'Send question' }).click()
  await page.getByRole('alert').filter({ hasText: 'Generation is unavailable' }).waitFor()
  assert.equal(mock.data.conversations.length, 2)
  assert.deepEqual(mock.data.deletedIds, [3])
  await page.close()
})

test('overview is responsive at the required desktop, tablet and mobile widths', async (browser) => {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 1280, height: 900 },
    { width: 1024, height: 900 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ]) {
    const { page } = await createPage(browser, viewport)
    await signIn(page)
    await page.locator('.overview-stat-card .overview-stat-value').first().waitFor()
    const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: window.innerWidth }))
    assert.ok(widths.scroll <= widths.viewport, `horizontal overflow at ${viewport.width}px: ${JSON.stringify(widths)}`)
    if (viewport.width === 1440 || viewport.width === 390) {
      await page.screenshot({ path: `e2e/overview-${viewport.width}.png`, fullPage: true })
    }
    await page.close()
  }
})

;(async () => {
  const browser = await chromium.launch({ channel: process.env.RAARA_CHROME_CHANNEL || 'chrome', headless: true })
  let failed = 0
  try {
    for (const item of cases) {
      try {
        await item.run(browser)
        process.stdout.write(`PASS ${item.name}\n`)
      } catch (error) {
        failed += 1
        process.stderr.write(`FAIL ${item.name}: ${error.stack || error.message}\n`)
      }
    }
  } finally {
    await browser.close()
  }
  process.stdout.write(`${cases.length - failed} passed, ${failed} failed, ${cases.length} total\n`)
  if (failed) process.exitCode = 1
})().catch((error) => {
  process.stderr.write(`Unable to run UI tests: ${error.stack || error.message}\n`)
  process.exitCode = 1
})
