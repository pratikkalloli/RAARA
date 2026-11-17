import React, { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { apiRequest, createIdempotencyKey, formatApiError, getStoredToken, setUnauthorizedHandler, storeToken } from './api.js'

const STATUS = {
  SUPPORTED: 'Evidence supported',
  PARTIALLY_SUPPORTED: 'Partially supported',
  NOT_FOUND: 'Not found in available documents',
  CONFLICTING_SOURCES: 'Conflicting sources',
  CONVERSATIONAL: 'Conversation',
}
const ACTIVE_CONVERSATION_KEY = 'raara.active_conversation_id'

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: '⌂' },
  { path: '/assistant', label: 'AI Assistant', icon: '✦' },
  { path: '/documents', label: 'My Documents', icon: '▤' },
  { path: '/history', label: 'Chat History', icon: '◷' },
  { path: '/profile', label: 'Profile', icon: '◉' },
]

export default function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [token, setToken] = useState(getStoredToken())
  const [user, setUser] = useState(null)
  const [auth, setAuth] = useState(token ? 'checking' : 'signed-out')
  const [health, setHealth] = useState('checking')
  const [aiConfig, setAiConfig] = useState(null)

  const go = useCallback((next) => {
    if (window.location.pathname !== next) window.history.pushState({}, '', next)
    setPath(next)
  }, [])

  const logout = useCallback(() => {
    storeToken(null)
    window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
    setToken(null)
    setUser(null)
    setAuth('signed-out')
    go('/login')
  }, [go])

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  useEffect(() => {
    if (!token) {
      setAuth('signed-out')
      setUser(null)
      return undefined
    }
    let active = true
    setAuth('checking')
    apiRequest('/auth/me', { token })
      .then((profile) => {
        if (active) {
          setUser(profile)
          setAuth('signed-in')
        }
      })
      .catch((err) => {
        if (!active) return
        if (err.status === 401) logout()
        else setAuth('unavailable')
      })
    return () => { active = false }
  }, [token, logout])

  useEffect(() => {
    let active = true
    const check = async () => {
      try {
        const [basic, provider] = await Promise.all([
          apiRequest('/health', { token: null }),
          apiRequest('/health/ai', { token: null }),
        ])
        if (active) {
          setHealth(basic?.status === 'ok' ? 'connected' : 'unavailable')
          setAiConfig(provider)
        }
      } catch {
        if (active) setHealth('unavailable')
      }
    }
    check()
    const timer = window.setInterval(check, 30000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])

  useEffect(() => {
    if (auth === 'signed-in' && user && (path === '/login' || path === '/register')) {
      go(user.role === 'admin' ? '/admin' : '/')
    }
  }, [auth, user, path, go])

  if (auth === 'checking') return <div className="center-state" role="status">Checking your session…</div>
  if (auth === 'unavailable') return <div className="center-state">Could not verify your session. <button className="button primary" onClick={logout}>Return to sign in</button></div>
  if (!user) {
    return <AuthPage mode={path === '/register' ? 'register' : 'login'} go={go} health={health} onLogin={(data) => {
      storeToken(data.access_token)
      setToken(data.access_token)
      setUser(data.user)
      setAuth('signed-in')
      go(data.user.role === 'admin' ? '/admin' : '/')
    }} />
  }
  if (path === '/admin' && user.role !== 'admin') go('/')
  return <Dashboard user={user} admin={user.role === 'admin'} path={path} go={go} health={health} aiConfig={aiConfig} logout={logout} />
}

function AuthPage({ mode, go, health, onLogin }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function submit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)
    const form = new FormData(event.currentTarget)
    try {
      if (mode === 'register') {
        await apiRequest('/auth/register', {
          method: 'POST', token: null,
          body: { username: form.get('username'), email: form.get('email'), password: form.get('password') },
        })
        setNotice('Account created. Sign in with your new credentials.')
        go('/login')
      } else {
        onLogin(await apiRequest('/auth/login', {
          method: 'POST', token: null,
          body: { identifier: form.get('identifier'), password: form.get('password') },
        }))
      }
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setBusy(false)
    }
  }

  return <main className="auth-screen">
    <section className="auth-card">
      <Brand href="/login" onClick={(event) => { event.preventDefault(); go('/login') }} />
      <p className="eyebrow">ACADEMIC KNOWLEDGE WORKSPACE</p>
      <h1>{mode === 'login' ? 'Welcome back' : 'Create your student account'}</h1>
      <p className="auth-copy">{mode === 'login' ? 'Sign in to your academic documents and conversations.' : 'Registration creates a student account. Administrator accounts are provisioned separately.'}</p>
      {error && <Alert>{error}</Alert>}
      {notice && <div className="alert success" role="status">{notice}</div>}
      <form className="stack-form" onSubmit={submit}>
        {mode === 'register' ? <>
          <label>Username<input name="username" autoComplete="username" minLength="3" maxLength="32" required /></label>
          <label>Email<input name="email" type="email" autoComplete="email" maxLength="254" required /></label>
        </> : <label>Username or email<input name="identifier" autoComplete="username" required /></label>}
        <label>Password<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 12 : undefined} required /></label>
        <button className="button primary full" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
      </form>
      <p className="auth-switch">{mode === 'login' ? 'New to RAARA?' : 'Already registered?'} <button className="text-button" onClick={() => { setError(''); go(mode === 'login' ? '/register' : '/login') }}>{mode === 'login' ? 'Create student account' : 'Sign in'}</button></p>
      <ServiceStatus health={health} />
    </section>
  </main>
}

function Dashboard({ user, admin, path, go, health, aiConfig, logout }) {
  const [conversations, setConversations] = useState([])
  const [documents, setDocuments] = useState([])
  const [conversationLoadState, setConversationLoadState] = useState('loading')
  const [documentLoadState, setDocumentLoadState] = useState('loading')
  const [pending, setPending] = useState([])
  const [activeId, setActiveId] = useState(null)
  const initialConversationId = useRef(Number(window.sessionStorage.getItem(ACTIVE_CONVERSATION_KEY)) || null)
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [chatBusy, setChatBusy] = useState(false)
  const [question, setQuestion] = useState('')
  const [promptType, setPromptType] = useState('C')
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [retry, setRetry] = useState(null)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(null)
  const [uploadMsg, setUploadMsg] = useState('')
  const [search, setSearch] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [titleDraft, setTitleDraft] = useState('')
  const [reviewNote, setReviewNote] = useState('')
  const [reviewBusy, setReviewBusy] = useState(null)
  const [syncErrors, setSyncErrors] = useState({})
  const uploadForm = useRef(null)

  const refreshConversations = useCallback(async () => {
    setConversationLoadState('loading')
    try {
      const result = await apiRequest('/conversations')
      setConversations(result)
      setConversationLoadState('loaded')
      return result
    } catch (err) {
      setConversationLoadState('error')
      throw err
    }
  }, [])
  const refreshDocuments = useCallback(async () => {
    setDocumentLoadState('loading')
    try {
      const result = await apiRequest('/documents')
      setDocuments(result)
      setDocumentLoadState('loaded')
      return result
    } catch (err) {
      setDocumentLoadState('error')
      throw err
    }
  }, [])
  const refreshPending = useCallback(async () => {
    const result = await apiRequest('/admin/documents/pending')
    setPending(result)
    return result
  }, [])

  useEffect(() => {
    let active = true
    setBusy(true)
    const work = admin
      ? [refreshDocuments(), refreshPending(), refreshConversations()]
      : [refreshConversations(), refreshDocuments()]
    Promise.all(work).catch((err) => { if (active) setError(formatApiError(err)) }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [admin, refreshConversations, refreshDocuments, refreshPending])

  useEffect(() => {
    const conversationId = initialConversationId.current
    if (admin || !conversationId) return undefined
    let active = true
    apiRequest(`/conversations/${conversationId}`)
      .then((detail) => {
        if (!active) return
        setActiveId(detail.id)
        setMessages(detail.messages || [])
      })
      .catch(() => {
        if (!active) return
        window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
        initialConversationId.current = null
      })
    return () => { active = false }
  }, [admin])

  async function createConversation(title = '') {
    const created = await apiRequest('/conversations', {
      method: 'POST',
      body: { title: title.slice(0, 80) || undefined },
    })
    setActiveId(created.id)
    window.sessionStorage.setItem(ACTIVE_CONVERSATION_KEY, String(created.id))
    setMessages([])
    setRetry(null)
    go('/assistant')
    await refreshConversations()
    return created
  }

  async function refreshOverview() {
    setError('')
    setBusy(true)
    try {
      await Promise.all([refreshDocuments(), refreshConversations()])
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setBusy(false)
    }
  }

  async function openConversation(id) {
    if (chatBusy) return
    setBusy(true)
    setError('')
    try {
      const detail = await apiRequest(`/conversations/${id}`)
      setActiveId(detail.id)
      window.sessionStorage.setItem(ACTIVE_CONVERSATION_KEY, String(detail.id))
      setMessages(detail.messages || [])
      setRetry(null)
      setChatError('')
      go('/assistant')
    } catch (err) {
      setError(formatApiError(err))
      setActiveId(null)
      window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
      setMessages([])
      await refreshConversations().catch(() => {})
    } finally {
      setBusy(false)
    }
  }

  async function renameConversation(id) {
    const title = titleDraft.trim()
    if (!title) return
    try {
      const updated = await apiRequest(`/conversations/${id}`, { method: 'PATCH', body: { title } })
      setConversations((items) => items.map((item) => item.id === id ? { ...item, ...updated } : item))
      setEditingId(null)
      setTitleDraft('')
    } catch (err) {
      setError(formatApiError(err))
    }
  }

  async function deleteConversation(item) {
    if (chatBusy || !window.confirm(`Delete “${item.title}” and its messages? This cannot be undone.`)) return
    try {
      await apiRequest(`/conversations/${item.id}`, { method: 'DELETE' })
      setConversations((items) => items.filter((conversation) => conversation.id !== item.id))
      if (activeId === item.id) {
        setActiveId(null)
        setMessages([])
        window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
      }
    } catch (err) {
      setError(formatApiError(err))
    }
  }

  async function send(event, isRetry = false) {
    event?.preventDefault()
    const text = isRetry ? retry?.question : question.trim()
    if (!text || chatBusy) return
    let request = isRetry ? retry : null
    let createdConversationId = null
    setChatBusy(true)
    setChatError('')
    try {
      if (!activeId) {
        const conversation = await createConversation(text)
        createdConversationId = conversation.id
        request = { question: text, conversation_id: conversation.id, idempotency_key: createIdempotencyKey(), document_id: selectedDocumentId ? Number(selectedDocumentId) : undefined }
      } else if (!request || request.conversation_id !== activeId || request.question !== text) {
        request = { question: text, conversation_id: activeId, idempotency_key: createIdempotencyKey(), document_id: selectedDocumentId ? Number(selectedDocumentId) : undefined }
      }
      setRetry(request)
      const answer = await apiRequest('/chat', {
        method: 'POST',
        body: {
          question: text,
          prompt_type: promptType,
          document_id: request.document_id,
          conversation_id: request.conversation_id,
          idempotency_key: request.idempotency_key,
        },
      })
      setMessages((items) => [
        ...items,
        { role: 'user', content: text },
        { role: 'assistant', content: answer.answer, structured_response: answer },
      ])
      setQuestion('')
      setRetry(null)
      await refreshConversations()
    } catch (err) {
      if (createdConversationId !== null) {
        try {
          const detail = await apiRequest(`/conversations/${createdConversationId}`)
          if (detail.message_count === 0) {
            await apiRequest(`/conversations/${createdConversationId}`, { method: 'DELETE' })
            setActiveId(null)
            setMessages([])
            window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
            await refreshConversations()
          }
        } catch {
          // If the server cannot be reached, retain the conversation for a safe retry.
        }
      }
      setChatError(formatApiError(err))
    } finally {
      setChatBusy(false)
    }
  }

  async function upload(event) {
    event.preventDefault()
    setUploadMsg('')
    setUploadProgress(0)
    const form = event.currentTarget
    const file = form.elements.file.files?.[0]
    if (!file) return
    if ((!file.type || file.type !== 'application/pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
      setUploadMsg('Choose a PDF file. Other file types are not accepted.')
      setUploadProgress(null)
      return
    }
    if (!file.size) {
      setUploadMsg('This PDF is empty. Choose a readable PDF with extractable text.')
      setUploadProgress(null)
      return
    }
    setUploadBusy(true)
    try {
      const result = await apiRequest('/documents/upload', {
        method: 'POST', body: new FormData(form), onUploadProgress: setUploadProgress,
      })
      setUploadProgress(100)
      setUploadMsg(`${result.document_name} uploaded and indexed. Review status: ${result.verification_status}.`)
      form.reset()
      await refreshDocuments()
    } catch (err) {
      setUploadMsg(formatApiError(err))
      setUploadProgress(null)
      // Leave the selected file in place so the user can retry after a recoverable failure.
    } finally {
      setUploadBusy(false)
    }
  }

  async function deleteDocument(document) {
    if (!window.confirm(`Delete “${document.document_name}” and its indexed passages? This cannot be undone.`)) return
    try {
      await apiRequest(`/documents/${document.document_id}`, { method: 'DELETE' })
      setDocuments((items) => items.filter((item) => item.document_id !== document.document_id))
      setPending((items) => items.filter((item) => item.document_id !== document.document_id))
    } catch (err) {
      setError(formatApiError(err))
    }
  }

  async function decide(id, decision) {
    setReviewBusy(id)
    setError('')
    try {
      await apiRequest(`/admin/documents/${id}/verification`, {
        method: 'POST', body: { decision, review_note: reviewNote || null },
      })
      setReviewNote('')
      await Promise.all([refreshPending(), refreshDocuments()])
    } catch (err) {
      if (err.status === 503 && err.detail?.document_id) {
        setSyncErrors((items) => ({ ...items, [id]: `${err.message} Retry synchronization below.` }))
      } else setError(formatApiError(err))
      await refreshPending().catch(() => {})
    } finally {
      setReviewBusy(null)
    }
  }

  async function retrySync(id) {
    setReviewBusy(id)
    try {
      await apiRequest(`/admin/documents/${id}/verification/retry-sync`, { method: 'POST' })
      setSyncErrors((items) => ({ ...items, [id]: '' }))
      await Promise.all([refreshPending(), refreshDocuments()])
    } catch (err) {
      setSyncErrors((items) => ({ ...items, [id]: formatApiError(err) }))
    } finally {
      setReviewBusy(null)
    }
  }

  const activeConversation = conversations.find((item) => item.id === activeId)
  const visibleConversations = conversations.filter((item) => `${item.title} ${item.updated_at}`.toLowerCase().includes(search.toLowerCase()))
  const currentView = path === '/admin' && admin ? 'admin' : ['/', '/assistant', '/documents', '/history', '/profile'].includes(path) ? path : '/'

  function startNewConversation() {
    setActiveId(null)
    setMessages([])
    setRetry(null)
    setChatError('')
    window.sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY)
    go('/assistant')
  }

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Main navigation">
      <Brand href="/" onClick={(event) => { event.preventDefault(); go('/') }} />
      <nav className="sidebar-navigation" aria-label="Workspace">
        <div className="sidebar-label">WORKSPACE</div>
        {NAV_ITEMS.map((item) => <button key={item.path} className={`nav-link ${currentView === item.path ? 'active' : ''}`} aria-current={currentView === item.path ? 'page' : undefined} onClick={() => go(item.path)}>
          <span className="nav-icon" aria-hidden="true">{item.icon}</span>{item.label}
        </button>)}
        {admin && <><div className="sidebar-label admin-label">ADMINISTRATION</div><button className={`nav-link ${currentView === 'admin' ? 'active' : ''}`} aria-current={currentView === 'admin' ? 'page' : undefined} onClick={() => go('/admin')}><span className="nav-icon" aria-hidden="true">✓</span>Admin Panel</button></>}
      </nav>
      <button className="button primary sidebar-new" disabled={chatBusy} onClick={startNewConversation}>＋ New conversation</button>
      <div className="sidebar-note"><span className="sidebar-note-icon" aria-hidden="true">✦</span><p>Academic guidance grounded in documents available to your account.</p></div>
      <div className="sidebar-footer"><ServiceStatus health={health} compact /></div>
    </aside>

    <main className="workspace">
      <header className="topbar">
        <div className="breadcrumb">Workspace <span>/</span> {viewLabel(currentView)}</div>
        <div className="topbar-user"><span className="user-avatar" aria-hidden="true">{user.username?.[0]?.toUpperCase() || 'U'}</span><span>{user.username}<small>{admin ? 'Administrator' : 'Student'}</small></span><button className="button quiet small" onClick={logout}>Sign out</button></div>
      </header>
      <div className="dashboard-content">
        {error && <Alert>{error}</Alert>}
        {currentView === '/' && <OverviewView user={user} health={health} aiConfig={aiConfig} conversations={conversations} documents={documents} busy={busy} conversationLoadState={conversationLoadState} documentLoadState={documentLoadState} go={go} openConversation={openConversation} startNewConversation={startNewConversation} refreshOverview={refreshOverview} />}
        {currentView === '/assistant' && <AssistantView activeConversation={activeConversation} messages={messages} documents={documents} selectedDocumentId={selectedDocumentId} setSelectedDocumentId={setSelectedDocumentId} question={question} setQuestion={setQuestion} send={send} chatBusy={chatBusy} chatError={chatError} retry={retry} promptType={promptType} setPromptType={setPromptType} go={go} />}
        {currentView === '/documents' && <DocumentsView documents={documents} busy={busy} upload={upload} uploadForm={uploadForm} uploadBusy={uploadBusy} uploadProgress={uploadProgress} uploadMsg={uploadMsg} deleteDocument={deleteDocument} />}
        {currentView === '/history' && <HistoryView conversations={visibleConversations} allCount={conversations.length} search={search} setSearch={setSearch} busy={busy} activeId={activeId} openConversation={openConversation} deleteConversation={deleteConversation} editingId={editingId} setEditingId={setEditingId} titleDraft={titleDraft} setTitleDraft={setTitleDraft} renameConversation={renameConversation} chatBusy={chatBusy} />}
        {currentView === '/profile' && <ProfileView user={user} aiConfig={aiConfig} health={health} />}
        {currentView === 'admin' && <AdminView documents={documents} pending={pending} busy={busy} reviewNote={reviewNote} setReviewNote={setReviewNote} reviewBusy={reviewBusy} decide={decide} deleteDocument={deleteDocument} syncErrors={syncErrors} retrySync={retrySync} health={health} aiConfig={aiConfig} />}
        <footer className="page-footer"><span>RAARA · Retrieval-Augmented Academic Regulated Assistant</span><span>Administrator review does not establish official authenticity</span></footer>
      </div>
    </main>
  </div>
}

function OverviewView({
  user,
  health,
  aiConfig,
  conversations,
  documents,
  busy,
  conversationLoadState,
  documentLoadState,
  go,
  openConversation,
  startNewConversation,
  refreshOverview,
}) {
  const displayName = user.display_name || user.full_name || user.username || 'there'
  const firstName = String(displayName).trim().split(/\s+/)[0] || 'there'
  const currentHour = new Date().getHours()
  const greeting = currentHour < 12 ? 'Good morning' : currentHour < 17 ? 'Good afternoon' : 'Good evening'
  const documentStatsAvailable = documentLoadState === 'loaded'
  const conversationStatsAvailable = conversationLoadState === 'loaded'
  const indexedDocuments = documents.filter((document) =>
    document.processing_status === 'indexed' && document.vector_sync_status === 'synced'
  )
  const failedDocuments = documents.filter((document) =>
    ['failed', 'error'].includes(String(document.processing_status).toLowerCase())
  )
  const processingDocuments = documents.filter((document) =>
    ['pending', 'processing'].includes(String(document.processing_status).toLowerCase())
      || document.vector_sync_status === 'pending'
  )
  const pendingReviewDocuments = documents.filter((document) =>
    document.verification_status === 'unverified'
      && document.processing_status === 'indexed'
      && document.vector_sync_status === 'synced'
  )
  const questionCountAvailable = conversationStatsAvailable
    && conversations.every((conversation) => Number.isInteger(conversation.question_count))
  const questionsAsked = conversations.reduce((total, conversation) =>
    total + (Number.isInteger(conversation.question_count) ? conversation.question_count : 0), 0
  )
  const indexDescription = documentStatsAvailable
    ? `${processingDocuments.length} processing · ${failedDocuments.length} failed`
    : 'Index details unavailable'

  return <div className="overview-page">
    <section className="overview-hero">
      <div className="overview-hero-main">
        <p className="overview-kicker"><span className="overview-kicker-mark">R</span> RAARA · {greeting}, {firstName}</p>
        <h1>Academic Regulatory Assistant</h1>
        <p className="overview-hero-copy">Your academic knowledge, organized and ready to explore.</p>
        <div className="overview-hero-actions">
          <button className="button primary overview-primary-action" onClick={() => go('/assistant')}>
            <OverviewIcon name="spark" /> Ask RAARA
          </button>
          <button className="button secondary overview-secondary-action" onClick={() => go('/documents')}>
            <OverviewIcon name="upload" /> Upload PDF
          </button>
        </div>
      </div>
      <aside className="overview-service-card" aria-label="System status">
        <div className="overview-service-heading">
          <span className="overview-service-symbol"><OverviewIcon name="status" /></span>
          <div><span className="overview-service-label">SYSTEM STATUS</span><strong>Workspace services</strong></div>
        </div>
        <div className="overview-service-row">
          <ServiceStatus health={health} />
          <span className={`overview-live-indicator ${health}`} aria-hidden="true" />
        </div>
        <div className="overview-service-meta">
          <span>AI provider</span>
          <strong>{aiConfig
            ? `${humanizeProvider(aiConfig.provider)} · ${aiConfig.credential_configured ? 'configured' : 'not configured'}`
            : 'Configuration unavailable'}</strong>
          {aiConfig && <small>{embeddingSummary(aiConfig)}</small>}
        </div>
        <p className="overview-service-note">Provider availability is checked when you ask a question.</p>
        <div className="overview-service-index">
          <span>Indexed documents</span>
          <strong>{documentStatsAvailable ? indexedDocuments.length : '—'}</strong>
          <small>{indexDescription}</small>
        </div>
      </aside>
    </section>

    <section className="overview-stats" aria-label="Workspace statistics">
      <OverviewStatCard
        title="Total documents"
        value={documentStatsAvailable ? documents.length : null}
        loading={documentLoadState === 'loading'}
        description={documentStatsAvailable
          ? `${pendingReviewDocuments.length} awaiting review · ${failedDocuments.length} failed`
          : 'From your document library'}
        icon="document"
        tone="blue"
      />
      <OverviewStatCard
        title="Total conversations"
        value={conversationStatsAvailable ? conversations.length : null}
        loading={conversationLoadState === 'loading'}
        description="Saved to your account"
        icon="conversation"
        tone="violet"
      />
      <OverviewStatCard
        title="Questions asked"
        value={questionCountAvailable ? questionsAsked : null}
        loading={conversationLoadState === 'loading'}
        description={questionCountAvailable ? 'Persisted user messages' : 'Question count unavailable'}
        icon="question"
        tone="green"
      />
      <OverviewStatCard
        title="Indexed documents"
        value={documentStatsAvailable ? indexedDocuments.length : null}
        loading={documentLoadState === 'loading'}
        description={indexDescription}
        icon="indexed"
        tone="amber"
      />
    </section>

    <section className="overview-section overview-recent-section">
      <div className="overview-section-heading">
        <div>
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h2>Recent activity</h2>
          <p>Pick up where you left off.</p>
        </div>
        <button className="button quiet overview-refresh" onClick={refreshOverview} disabled={busy}>
          <OverviewIcon name="refresh" /> {busy ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <div className="overview-recent-grid">
        <section className="overview-content-card" aria-labelledby="overview-documents-title">
          <div className="overview-content-heading">
            <div className="overview-content-title">
              <span className="overview-heading-icon documents"><OverviewIcon name="document" /></span>
              <div><h3 id="overview-documents-title">Recent documents</h3><p>Your uploaded academic files</p></div>
            </div>
            <button className="overview-link" onClick={() => go('/documents')}>View all <span aria-hidden="true">→</span></button>
          </div>
          {documentLoadState === 'loading' && documents.length === 0
            ? <OverviewListSkeleton />
            : documentLoadState === 'error'
              ? <OverviewUnavailable message="Your documents could not be loaded." onRetry={refreshOverview} />
              : documents.length === 0
                ? <OverviewEmptyState
                    icon="document"
                    title="Your library is ready when you are"
                    message="Upload a PDF to build a private, evidence-backed academic library."
                    action="Upload your first PDF"
                    onClick={() => go('/documents')}
                  />
                : <div className="overview-record-list">
                    {documents.slice(0, 4).map((document) => <OverviewDocumentRow
                      key={document.document_id}
                      document={document}
                      onOpen={() => go('/documents')}
                    />)}
                  </div>}
        </section>

        <section className="overview-content-card" aria-labelledby="overview-conversations-title">
          <div className="overview-content-heading">
            <div className="overview-content-title">
              <span className="overview-heading-icon conversations"><OverviewIcon name="conversation" /></span>
              <div><h3 id="overview-conversations-title">Recent conversations</h3><p>Your latest questions and answers</p></div>
            </div>
            <button className="overview-link" onClick={() => go('/history')}>View all <span aria-hidden="true">→</span></button>
          </div>
          {conversationLoadState === 'loading' && conversations.length === 0
            ? <OverviewListSkeleton />
            : conversationLoadState === 'error'
              ? <OverviewUnavailable message="Your conversations could not be loaded." onRetry={refreshOverview} />
              : conversations.length === 0
                ? <OverviewEmptyState
                    icon="conversation"
                    title="Start your first conversation"
                    message="Ask about the academic documents available in your account."
                    action="Ask RAARA"
                    onClick={startNewConversation}
                  />
                : <div className="overview-record-list">
                    {conversations.slice(0, 4).map((conversation) => <OverviewConversationRow
                      key={conversation.id}
                      conversation={conversation}
                      onOpen={() => openConversation(conversation.id)}
                    />)}
                  </div>}
        </section>
      </div>
    </section>

    <section className="overview-section overview-quick-section">
      <div className="overview-section-heading compact-heading">
        <div><p className="eyebrow">SHORTCUTS</p><h2>Quick actions</h2></div>
      </div>
      <div className="overview-quick-grid">
        <OverviewQuickAction icon="spark" title="Ask a question" detail="Get answers grounded in your files" onClick={() => go('/assistant')} />
        <OverviewQuickAction icon="upload" title="Upload a PDF" detail="Add a document to your library" onClick={() => go('/documents')} />
        <OverviewQuickAction icon="document" title="Browse documents" detail="Review your uploads and status" onClick={() => go('/documents')} />
        <OverviewQuickAction icon="history" title="View chat history" detail="Return to a saved conversation" onClick={() => go('/history')} />
      </div>
    </section>

    <section className="overview-how-it-works">
      <div className="overview-how-heading">
        <p className="eyebrow">A SIMPLE WORKFLOW</p>
        <h2>From document to answer</h2>
        <p>Bring your academic material. RAARA helps you explore what it says.</p>
      </div>
      <div className="overview-workflow-steps">
        <OverviewWorkflowStep number="01" title="Upload a PDF" detail="Add an academic document to your private library." />
        <OverviewWorkflowStep number="02" title="Content is indexed" detail="RAARA extracts text and prepares it for retrieval." />
        <OverviewWorkflowStep number="03" title="Ask naturally" detail="Use plain language to explore the document." />
        <OverviewWorkflowStep number="04" title="Review the evidence" detail="Answers show supporting passages and source metadata." />
      </div>
    </section>
  </div>
}

function OverviewStatCard({ title, value, description, icon, tone, loading }) {
  return <article className={`overview-stat-card ${tone}`}>
    <div className="overview-stat-topline">
      <span className="overview-stat-icon"><OverviewIcon name={icon} /></span>
      <span className="overview-stat-caption">{title}</span>
    </div>
    {loading
      ? <span className="overview-stat-skeleton" aria-label={`Loading ${title.toLowerCase()}`} />
      : <strong className="overview-stat-value">{value ?? '—'}</strong>}
    <p>{loading ? 'Loading your data…' : description}</p>
  </article>
}

function OverviewDocumentRow({ document, onOpen }) {
  return <button className="overview-record-row" onClick={onOpen} title={document.document_name}>
    <span className="overview-record-icon document"><OverviewIcon name="document" /></span>
    <span className="overview-record-main">
      <strong>{document.document_name}</strong>
      <small>{humanizeStatus(document.document_type || 'document')} · Uploaded {formatDateTime(document.uploaded_at)}</small>
    </span>
    <span className="overview-record-status">
      <span className={`overview-processing-status ${String(document.processing_status).toLowerCase()}`}>{humanizeStatus(document.processing_status)}</span>
      <Badge status={document.verification_status} />
    </span>
    <span className="overview-record-arrow" aria-hidden="true">→</span>
  </button>
}

function OverviewConversationRow({ conversation, onOpen }) {
  return <button className="overview-record-row" onClick={onOpen} title={conversation.title}>
    <span className="overview-record-icon conversation"><OverviewIcon name="conversation" /></span>
    <span className="overview-record-main">
      <strong>{conversation.title || 'Untitled conversation'}</strong>
      <small>{conversation.message_count} messages · Updated {formatDateTime(conversation.updated_at)}</small>
    </span>
    <span className="overview-conversation-count">{conversation.question_count ?? '—'} <small>questions</small></span>
    <span className="overview-record-arrow" aria-hidden="true">→</span>
  </button>
}

function OverviewQuickAction({ icon, title, detail, onClick }) {
  return <button className="overview-quick-action" onClick={onClick}>
    <span className="overview-quick-icon"><OverviewIcon name={icon} /></span>
    <span className="overview-quick-copy"><strong>{title}</strong><small>{detail}</small></span>
    <span className="overview-record-arrow" aria-hidden="true">→</span>
  </button>
}

function OverviewWorkflowStep({ number, title, detail }) {
  return <article className="overview-workflow-step">
    <span className="overview-step-number">{number}</span>
    <div><h3>{title}</h3><p>{detail}</p></div>
  </article>
}

function OverviewEmptyState({ icon, title, message, action, onClick }) {
  return <div className="overview-empty-state">
    <span className="overview-empty-icon"><OverviewIcon name={icon} /></span>
    <h4>{title}</h4>
    <p>{message}</p>
    <button className="button secondary" onClick={onClick}>{action}</button>
  </div>
}

function OverviewUnavailable({ message, onRetry }) {
  return <div className="overview-unavailable" role="status">
    <p>{message} Your other workspace data is still available.</p>
    <button className="text-button" onClick={onRetry}>Try again</button>
  </div>
}

function OverviewListSkeleton() {
  return <div className="overview-skeleton-list" aria-label="Loading recent activity">
    {[0, 1, 2].map((item) => <div className="overview-skeleton-row" key={item}><i/><span><b/><em/></span><i/></div>)}
  </div>
}

function OverviewIcon({ name }) {
  const common = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }
  const shapes = {
    document: <><path d="M7 3.75h7l4 4V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.75a1 1 0 0 1 1-1Z"/><path d="M14 4v4h4M9 13h6M9 16.5h6"/></>,
    conversation: <><path d="M5 5.5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-7l-5 3v-3H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2Z"/><path d="M7.5 10h9M7.5 13.5h6"/></>,
    question: <><circle cx="12" cy="12" r="9"/><path d="M9.7 9a2.4 2.4 0 1 1 4.2 1.6c-1.3 1.1-1.9 1.5-1.9 3M12 17.4h.01"/></>,
    indexed: <><path d="m5 12.5 4.2 4.2L19.5 6.5"/><path d="M20 12a8 8 0 1 1-4.7-7.3"/></>,
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z"/></>,
    upload: <><path d="M12 15V4M8 8l4-4 4 4"/><path d="M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5"/></>,
    history: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/><path d="M4.5 5.5 3 8V4h4"/></>,
    status: <><path d="M12 3 20 6v5.4c0 4.4-3.1 7.8-8 9.6-4.9-1.8-8-5.2-8-9.6V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
    refresh: <><path d="M20 7v5h-5"/><path d="M4.7 10A7.5 7.5 0 0 1 18 7l2 5M4 17v-5h5"/><path d="M19.3 14A7.5 7.5 0 0 1 6 17l-2-5"/></>,
  }
  return <svg {...common}>{shapes[name] || shapes.document}</svg>
}

function AssistantView({ activeConversation, messages, documents, selectedDocumentId, setSelectedDocumentId, question, setQuestion, send, chatBusy, chatError, retry, promptType, setPromptType, go }) {
  const indexedDocuments = documents.filter((document) => document.processing_status === 'indexed' && document.vector_sync_status === 'synced')
  return <>
    <section className="page-heading"><p className="eyebrow">GROUNDED QUESTION ANSWERING</p><div className="heading-with-action"><div><h1>AI Assistant</h1><p className="page-description">Answers are limited to retrieved passages and include their source metadata.</p></div><button className="button secondary" onClick={() => go('/history')}>Conversation history</button></div></section>
    <section className="panel chat-panel full-chat-panel">
      <div className="panel-heading"><div><p className="eyebrow">CURRENT CONVERSATION</p><h2>{activeConversation?.title || 'New conversation'}</h2></div><div className="assistant-options"><label className="prompt-select">Limit to document<select value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(event.target.value)}><option value="">All available documents</option>{indexedDocuments.map((document) => <option key={document.document_id} value={document.document_id}>{document.document_name}</option>)}</select></label><label className="prompt-select">Prompt configuration<select value={promptType} onChange={(event) => setPromptType(event.target.value)}><option value="A">A · Basic</option><option value="B">B · Role-based</option><option value="C">C · Evidence-constrained</option></select></label></div></div>
      <div className="message-list" aria-live="polite">{messages.length === 0 ? <div className="empty-state chat-empty"><h3>What would you like to understand?</h3><p>Upload a PDF first, then ask a question about its contents. Unverified uploads are always labeled.</p><button className="button secondary" onClick={() => go('/documents')}>Open document library</button></div> : messages.map((message, index) => message.role === 'user' ? <div className="message user-message" key={`${message.id || index}-user`}><span className="message-role">You</span><p>{message.content}</p></div> : <AnswerCard key={`${message.id || index}-assistant`} result={message.structured_response} content={message.content}/>)}</div>
      {chatError && <div className="alert error" role="alert">{chatError}{retry && <button className="button secondary small" onClick={(event) => send(event, true)} disabled={chatBusy}>Retry same question</button>}</div>}
      <form className="question-form" onSubmit={send}><label className="sr-only" htmlFor="question">Your academic question</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} maxLength="4000" rows="3" placeholder="Ask about attendance, examinations, grading…" disabled={chatBusy}/><div className="row-between"><span className="muted">Press Ctrl+Enter to send · Shift+Enter for a new line</span><button className="button primary" disabled={chatBusy || !question.trim()}>{chatBusy ? 'Searching documents…' : 'Send question'}</button></div></form>
    </section>
  </>
}

function DocumentsView({ documents, busy, upload, uploadForm, uploadBusy, uploadProgress, uploadMsg, deleteDocument }) {
  return <>
    <section className="page-heading"><p className="eyebrow">DOCUMENT LIBRARY</p><h1>My Documents</h1><p className="page-description">Upload PDFs to create a private evidence collection. Uploaded documents remain unverified until reviewed.</p></section>
    <section className="panel upload-panel full-panel"><div className="panel-heading"><div><h2>Upload an academic PDF</h2><p className="muted">Text extraction only. Scanned PDFs without extractable text are not OCR processed.</p></div></div>
      <form ref={uploadForm} className="stack-form compact" onSubmit={upload}><label>PDF file<input name="file" type="file" accept="application/pdf,.pdf" required/></label><label>Document name (optional)<input name="document_name" maxLength="255" placeholder="Use the PDF filename"/></label><div className="form-grid"><label>Academic year<input name="academic_year" maxLength="32" placeholder="2026–27"/></label><label>Version<input name="version" maxLength="32" defaultValue="1"/></label></div><input type="hidden" name="document_type" value="policy"/><input type="hidden" name="source_type" value="uploaded"/><button className="button primary" disabled={uploadBusy}>{uploadBusy ? 'Uploading and indexing…' : 'Upload PDF'}</button></form>
      {uploadProgress !== null && <div className="upload-progress" role="status"><span>{uploadProgress < 100 ? `Uploading PDF: ${uploadProgress}%` : 'PDF sent; the server is processing and indexing it…'}</span><progress max="100" value={uploadProgress}/></div>}
      {uploadMsg && <div className={uploadProgress === null ? 'alert error' : 'notice'} role="status">{uploadMsg}{uploadProgress === null && uploadForm.current?.elements.file.files?.length > 0 && <button type="button" className="button secondary small" onClick={() => uploadForm.current?.requestSubmit()} disabled={uploadBusy}>Retry upload</button>}</div>}
    </section>
    <section className="section-heading"><div><p className="eyebrow">PRIVATE LIBRARY</p><h2>Uploaded documents</h2></div></section>
    {busy && documents.length === 0 ? <div className="panel empty-state">Loading documents…</div> : documents.length === 0 ? <div className="panel empty-state"><h3>Your library is empty</h3><p>Upload a synthetic or authorized academic PDF to get started.</p></div> : <div className="document-grid">{documents.map((document) => <DocumentCard key={document.document_id} document={document} onDelete={deleteDocument}/>)}</div>}
  </>
}

function HistoryView({ conversations, allCount, search, setSearch, busy, activeId, openConversation, deleteConversation, editingId, setEditingId, titleDraft, setTitleDraft, renameConversation, chatBusy }) {
  return <>
    <section className="page-heading"><p className="eyebrow">SAVED WORK</p><h1>Chat History</h1><p className="page-description">Your conversations and structured answers are saved to your account.</p></section>
    <label className="history-search">Search conversations<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title" /></label>
    {busy && allCount === 0 ? <div className="panel empty-state">Loading conversations…</div> : allCount === 0 ? <div className="panel empty-state"><h3>No saved conversations</h3><p>Questions you ask in the AI assistant will appear here.</p></div> : conversations.length === 0 ? <div className="panel empty-state">No conversations match “{search}”.</div> : <div className="panel history-table">{conversations.map((item) => <article className={`history-entry ${activeId === item.id ? 'selected' : ''}`} key={item.id}>
      <div className="history-entry-main">{editingId === item.id ? <form className="rename-form" onSubmit={(event) => { event.preventDefault(); renameConversation(item.id) }}><label className="sr-only" htmlFor={`title-${item.id}`}>Conversation title</label><input id={`title-${item.id}`} value={titleDraft} maxLength="160" onChange={(event) => setTitleDraft(event.target.value)} autoFocus/><button className="button primary small">Save</button><button type="button" className="button quiet small" onClick={() => setEditingId(null)}>Cancel</button></form> : <><button className="history-open" disabled={chatBusy} onClick={() => openConversation(item.id)}><strong>{item.title}</strong><small>{item.message_count} messages · Updated {formatDate(item.updated_at)}</small></button><div className="history-actions"><button className="button quiet small" onClick={() => { setEditingId(item.id); setTitleDraft(item.title) }}>Rename</button><button className="button danger small" disabled={chatBusy} onClick={() => deleteConversation(item)}>Delete</button></div></>}</div>
    </article>)}</div>}
  </>
}

function ProfileView({ user, aiConfig, health }) {
  return <>
    <section className="page-heading"><p className="eyebrow">ACCOUNT</p><h1>Profile</h1><p className="page-description">Your authenticated RAARA account and current service configuration.</p></section>
    <section className="panel profile-panel"><div className="profile-avatar">{user.username?.[0]?.toUpperCase() || 'U'}</div><dl className="metadata-list profile-meta"><div><dt>Username</dt><dd>{user.username}</dd></div><div><dt>Email</dt><dd>{user.email}</dd></div><div><dt>Role</dt><dd>{user.role === 'admin' ? 'Administrator' : 'Student'}</dd></div><div><dt>Account status</dt><dd>{user.is_active ? 'Active' : 'Inactive'}</dd></div></dl></section>
    <section className="panel profile-panel"><h2>Service status</h2><ServiceStatus health={health}/><p className="muted">{aiConfig ? `${humanizeProvider(aiConfig.provider)} chat · ${aiConfig.chat_model} · ${aiConfig.credential_configured ? 'credential configured' : 'credential missing'} · API availability not checked` : 'AI provider configuration could not be loaded.'}</p>{aiConfig && <p className="muted">{embeddingSummary(aiConfig)}</p>}<p className="verification-note">RAARA never sends provider credentials to the browser.</p></section>
  </>
}

function AdminView({ documents, pending, busy, reviewNote, setReviewNote, reviewBusy, decide, deleteDocument, syncErrors, retrySync, health, aiConfig }) {
  const failed = documents.filter((document) => ['failed', 'error'].includes(String(document.processing_status).toLowerCase()))
  return <>
    <section className="page-heading"><p className="eyebrow">ADMINISTRATION</p><h1>Admin Panel</h1><p className="page-description">Review indexed uploads and monitor operational status. Administrator review does not prove that a document is an official university regulation.</p></section>
    <section className="panel admin-health"><div><h2>Operational health</h2><ServiceStatus health={health}/></div><p className="muted">{aiConfig ? `${humanizeProvider(aiConfig.provider)} chat · ${aiConfig.chat_model} · credential ${aiConfig.credential_configured ? 'configured' : 'missing'} · API availability not checked` : 'AI provider status unavailable'}{aiConfig && <><br/>{embeddingSummary(aiConfig)}</>}</p></section>
    <div className="section-heading"><div><p className="eyebrow">REVIEW QUEUE</p><h2>Pending documents ({pending.length})</h2></div><button className="button secondary" onClick={() => window.location.reload()}>Refresh</button></div>
    {busy && documents.length === 0 ? <div className="panel empty-state">Loading documents…</div> : documents.length === 0 ? <div className="panel empty-state">No documents are currently indexed.</div> : <div className="document-grid">{documents.map((document) => <article className="panel document-card admin-document-card" key={document.document_id}>
      <div className="row-between"><h3>{document.document_name}</h3><Badge status={document.verification_status}/></div><DocumentMetadata document={document}/>
      {document.verification_status === 'unverified' && document.processing_status === 'indexed' && <><label className="review-note-label">Review note (optional)<textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} maxLength="2000" rows="2"/></label><div className="button-row"><button className="button primary" disabled={reviewBusy === document.document_id} onClick={() => decide(document.document_id, 'verified')}>Mark reviewed</button><button className="button danger" disabled={reviewBusy === document.document_id} onClick={() => decide(document.document_id, 'rejected')}>Reject</button></div></>}
      {syncErrors[document.document_id] && <div className="alert error">{syncErrors[document.document_id]}<button className="button secondary small" disabled={reviewBusy === document.document_id} onClick={() => retrySync(document.document_id)}>Retry synchronization</button></div>}
      <button className="button danger small" disabled={reviewBusy === document.document_id} onClick={() => deleteDocument(document)}>Delete document</button>
    </article>)}</div>}
    <section className="panel admin-jobs"><h2>Failed processing jobs</h2>{failed.length ? failed.map((document) => <div className="recent-row static-row" key={document.document_id}><span><strong>{document.document_name}</strong><small>{document.processing_status}</small></span><span>Re-upload the original PDF to retry the synchronous ingestion.</span></div>) : <p className="muted">No failed jobs are recorded. Failed uploads currently roll back instead of creating a durable job record; retry is available from the student upload form while the selected file remains present.</p>}</section>
  </>
}

function DocumentCard({ document, onDelete }) {
  return <article className="panel document-card"><div className="row-between"><h3>{document.document_name}</h3><Badge status={document.verification_status}/></div><DocumentMetadata document={document}/><div className="document-card-footer"><span className={`processing-badge ${document.processing_status}`}>{humanizeStatus(document.processing_status)} · {humanizeStatus(document.vector_sync_status)} vectors</span><button className="button danger small" onClick={() => onDelete(document)}>Delete</button></div></article>
}

function DocumentMetadata({ document }) {
  return <dl className="metadata-list"><div><dt>Type</dt><dd>{document.document_type || 'Document'}</dd></div><div><dt>Academic year</dt><dd>{document.academic_year || 'Not specified'}</dd></div><div><dt>Version</dt><dd>{document.version || 'Not specified'}</dd></div><div><dt>Effective date</dt><dd>{document.effective_date || 'Not specified'}</dd></div><div><dt>Pages / chunks</dt><dd>{document.page_count ?? '—'} / {document.chunk_count ?? '—'}</dd></div><div><dt>Source</dt><dd>{document.source_type || 'Unknown'}</dd></div>{document.uploaded_by_username && <div><dt>Uploaded by</dt><dd>{document.uploaded_by_username}</dd></div>}{document.review_note && <div><dt>Review note</dt><dd>{document.review_note}</dd></div>}</dl>
}

function AnswerCard({ result, content }) {
  const [copied, setCopied] = useState(false)
  const status = result?.status || 'NOT_FOUND'
  const sources = Array.isArray(result?.sources) ? result.sources : []
  const evidence = Array.isArray(result?.evidence) ? result.evidence : []
  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(result?.answer || content || '')
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }
  return <article className="message assistant-message">
    <div className="row-between"><span className="message-role">RAARA</span><div className="answer-actions"><span className={`answer-status ${status.toLowerCase()}`}>{STATUS[status] || status}</span><button className="button quiet small" onClick={copyAnswer} aria-label="Copy RAARA answer">{copied ? 'Copied' : 'Copy answer'}</button></div></div>
    <AnswerText text={result?.answer || content || 'No answer was returned.'} />
    {result?.coverage && <p className="answer-coverage" role="note"><strong>Coverage note</strong>{result.coverage}</p>}
    {sources.length > 0 && <div className="evidence-list"><h4>Retrieved sources</h4>{sources.map((source, index) => <div className="evidence-item" key={`${source.document_id || source.document}-${index}`}><strong>{source.document || source.document_name || 'Source'}</strong><span>Pages {(source.pages || (source.page != null ? [source.page] : [])).join(', ') || 'not provided'}{source.sections?.length ? ` · ${source.sections.join(', ')}` : source.section ? ` · ${source.section}` : ''}</span><small>{source.verification_status === 'verified' ? 'Administrator reviewed' : `Unverified or status unavailable${source.verification_status ? ` (${source.verification_status})` : ''}`}</small></div>)}</div>}
    {evidence.length > 0 && <details className="evidence-details"><summary>View supporting passages ({evidence.length})</summary>{evidence.map((item, index) => <blockquote key={item.passage_id || index}>{item.text}<footer>{item.document || 'Source'}{item.page != null ? ` · p. ${item.page}` : ''}{item.section ? ` · ${item.section}` : ''}{item.verification_status !== 'verified' ? ' · unverified' : ''}</footer></blockquote>)}</details>}
    <p className="verification-note">Administrator review is not proof of official university authenticity. Check original documents for consequential decisions.</p>
  </article>
}

function AnswerText({ text }) {
  const blocks = []
  let ordered = []
  let unordered = []
  let paragraph = []
  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: 'paragraph', lines: paragraph })
    paragraph = []
  }
  const flushLists = () => {
    if (ordered.length) blocks.push({ type: 'ordered', lines: ordered })
    if (unordered.length) blocks.push({ type: 'unordered', lines: unordered })
    ordered = []
    unordered = []
  }
  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim()
    const numbered = line.match(/^\d+[.)]\s+(.+)$/)
    const bullet = line.match(/^[-*•]\s+(.+)$/)
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (!line) { flushParagraph(); flushLists(); continue }
    if (numbered) { flushParagraph(); if (unordered.length) flushLists(); ordered.push(numbered[1]); continue }
    if (bullet) { flushParagraph(); if (ordered.length) flushLists(); unordered.push(bullet[1]); continue }
    if (heading) { flushParagraph(); flushLists(); blocks.push({ type: 'heading', text: heading[1] }); continue }
    flushLists()
    paragraph.push(line)
  }
  flushParagraph(); flushLists()
  return <div className="assistant-answer">{blocks.map((block, index) => {
    if (block.type === 'heading') return <h3 key={index}>{block.text}</h3>
    if (block.type === 'ordered') return <ol key={index}>{block.lines.map((item, line) => <li key={line}>{item}</li>)}</ol>
    if (block.type === 'unordered') return <ul key={index}>{block.lines.map((item, line) => <li key={line}>{item}</li>)}</ul>
    return <p key={index}>{block.lines.join(' ')}</p>
  })}</div>
}

function Brand({ href = '/', onClick }) {
  return <a className="brand" href={href} onClick={onClick}><span className="brand-mark">R</span><span className="brand-name">RAARA</span></a>
}

function ServiceStatus({ health, compact = false }) {
  const label = health === 'connected' ? 'Backend connected' : health === 'checking' ? 'Checking connection' : 'Backend unavailable'
  return <span className={`service-status ${compact ? 'compact' : ''}`}><i className={`status-dot ${health}`} aria-hidden="true"/><span>{label}</span></span>
}

function Badge({ status }) {
  const labels = { verified: 'Admin reviewed', unverified: 'Unverified', rejected: 'Rejected' }
  return <span className={`status-badge ${status || 'unknown'}`}>{labels[status] || status || 'Unknown status'}</span>
}

function Alert({ children }) { return <div className="alert error" role="alert">{children}</div> }

function viewLabel(path) {
  return ({ '/': 'Overview', '/assistant': 'AI Assistant', '/documents': 'My Documents', '/history': 'Chat History', '/profile': 'Profile', '/admin': 'Admin Panel' })[path] || 'Overview'
}

function humanizeProvider(provider) { return provider ? `${provider[0].toUpperCase()}${provider.slice(1)}` : 'AI provider' }
function embeddingSummary(config) {
  return `Embeddings: ${config.embedding_provider || 'unknown'} · ${config.embedding_model || 'model unavailable'} · ${config.embedding_dimensions ?? '—'} dimensions`
}
function humanizeStatus(status) { return status ? status.replaceAll('_', ' ') : 'unknown' }
function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date)
}
function formatDateTime(value) {
  if (!value) return 'date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'date unavailable'
    : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
