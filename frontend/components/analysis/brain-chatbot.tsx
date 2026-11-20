'use client'

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { AlertCircle, Brain, Check, Loader2, MessageCircle, Plus, Send, Trash2 } from 'lucide-react'
import { Panel } from '@/components/common/primitives'
import { brainContextLabels, clearBrainChatContext, getBrainChatContext, type BrainAnalysisContext } from '@/lib/brain-chat-context'
import { getBrainChatStatus, sendBrainChat, type BrainChatMessage, type BrainChatStatus } from '@/services/brain-chatbot-service'
import { BrainChatMarkdown } from './brain-chat-markdown'

interface DisplayMessage extends BrainChatMessage { id: string }

const STARTERS = [
  'Explain glioblastoma in simple terms.',
  'What is the difference between glioma and glioblastoma?',
  'What does IDH mutation mean?',
  'Explain MGMT methylation.',
  'What does my MRI analysis result mean?',
  'What is the difference between T1CE and FLAIR MRI?',
  'What questions could I ask my neuro-oncologist?',
]

export function BrainChatbot() {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [draft, setDraft] = useState('')
  const [context, setContext] = useState<BrainAnalysisContext | null>(null)
  const [status, setStatus] = useState<BrainChatStatus | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryText, setRetryText] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setContext(getBrainChatContext())
    getBrainChatStatus().then(setStatus).catch((cause) => setStatusError(cause instanceof Error ? cause.message : 'Chat backend is unavailable.'))
  }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])

  const submit = async (question: string, addUserMessage = true) => {
    const text = question.trim()
    if (!text || busy) return
    const next = addUserMessage ? [...messages, { id: crypto.randomUUID(), role: 'user' as const, content: text }] : messages
    if (addUserMessage) setMessages(next)
    setBusy(true); setError(null); setRetryText(null)
    try {
      const response = await sendBrainChat(next.map(({ role, content }) => ({ role, content })), context)
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'assistant', content: response.answer }])
      setDraft('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The assistant could not respond. Please retry.')
      setRetryText(text)
    } finally { setBusy(false); inputRef.current?.focus() }
  }

  const send = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void submit(draft) }
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit(draft) }
  }
  const resetChat = () => { setMessages([]); setDraft(''); setError(null); setRetryText(null); inputRef.current?.focus() }
  const removeContext = () => { clearBrainChatContext(); setContext(null) }
  const configured = status?.configured === true
  const contextLabels = brainContextLabels(context)

  return <div className="grid min-h-[calc(100dvh-13rem)] gap-5 xl:grid-cols-[minmax(0,1fr)_18rem]">
    <Panel className="flex min-h-[70vh] flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-xl bg-wc-violet/10 text-wc-violet"><Brain className="size-5" /></span><div><h2 className="text-sm font-semibold">Brain AI Assistant</h2><p className="text-xs text-muted-foreground">Brain tumors · MRI · biomarkers</p></div></div>
        <button type="button" onClick={resetChat} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-xs font-medium hover:bg-muted" title="Start a new conversation"><Plus className="size-4" /> New chat</button>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite" aria-label="Conversation">
        {messages.length === 0 ? <div className="mx-auto flex max-w-2xl flex-col items-center py-8 text-center sm:py-12">
          <span className="flex size-14 items-center justify-center rounded-2xl bg-wc-violet/10 text-wc-violet"><MessageCircle className="size-7" /></span>
          <h3 className="mt-4 text-xl font-bold">How can I help with brain cancer information?</h3>
          <p className="mt-2 max-w-lg text-sm leading-6 text-muted-foreground">Ask about brain tumor terminology, MRI sequences, biomarkers, pathology language, or the research results produced by this Brain module.</p>
          <div className="mt-6 grid w-full gap-2 text-left sm:grid-cols-2">{STARTERS.map((prompt) => <button key={prompt} type="button" onClick={() => void submit(prompt)} disabled={busy} className="rounded-xl border border-border bg-card p-3 text-sm transition-colors hover:border-wc-violet/40 hover:bg-muted/60 disabled:cursor-not-allowed disabled:opacity-50">{prompt}</button>)}</div>
        </div> : messages.map((message) => <article key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          {message.role === 'assistant' && <span className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-lg bg-wc-violet/10 text-wc-violet"><Brain className="size-4" /></span>}
          <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm sm:max-w-[80%] ${message.role === 'user' ? 'rounded-br-md bg-primary text-primary-foreground' : 'rounded-bl-md bg-muted/70 text-foreground'}`}>
            {message.role === 'assistant' ? <BrainChatMarkdown content={message.content} /> : <p className="whitespace-pre-wrap leading-6">{message.content}</p>}
          </div>
        </article>)}
        {busy && <div className="flex items-center gap-3"><span className="flex size-8 items-center justify-center rounded-lg bg-wc-violet/10 text-wc-violet"><Brain className="size-4" /></span><div className="flex items-center gap-2 rounded-2xl bg-muted/70 px-4 py-3 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Thinking…</div></div>}
        {error && <div role="alert" className="ml-11 rounded-xl border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700 dark:text-red-300"><div className="flex items-start gap-2"><AlertCircle className="mt-0.5 size-4 shrink-0" /><p>{error}</p></div>{retryText && <button type="button" onClick={() => void submit(retryText, false)} disabled={busy} className="mt-2 text-xs font-semibold underline underline-offset-2 disabled:opacity-50">Retry</button>}</div>}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="border-t border-border p-3 sm:p-4">
        <div className="flex items-end gap-2 rounded-2xl border border-input bg-background p-2 focus-within:ring-3 focus-within:ring-ring/20">
          <textarea ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={keyDown} disabled={busy} rows={1} maxLength={5000} placeholder="Ask a brain tumor or MRI question…" className="max-h-36 min-h-10 flex-1 resize-y bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed" aria-label="Message the Brain AI assistant" />
          <button type="submit" disabled={busy || !draft.trim()} className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground disabled:cursor-not-allowed disabled:opacity-40" aria-label="Send message"><Send className="size-4" /></button>
        </div>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">Educational information only · not a diagnosis or treatment plan</p>
      </form>
    </Panel>

    <aside className="flex flex-col gap-4">
      {!configured && <div role="status" className="rounded-2xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6"><p className="font-semibold">AI provider setup required</p><p className="mt-1 text-muted-foreground">{statusError ?? (status ? 'The backend has no AI key configured. Add OPENAI_API_KEY to the backend environment, then restart the API.' : 'Checking backend provider…')}</p><p className="mt-2 text-xs text-muted-foreground">Keys stay on the server and are never sent to the browser.</p></div>}
      {configured && <div className="rounded-2xl border border-wc-turquoise/30 bg-wc-turquoise/8 p-4 text-sm"><p className="flex items-center gap-2 font-semibold"><Check className="size-4 text-wc-teal" /> AI provider configured</p><p className="mt-1 text-xs text-muted-foreground">{status?.provider} · {status?.model}</p></div>}
      <div className="rounded-2xl border border-border bg-card p-4"><h3 className="text-sm font-semibold">Brain analysis context</h3>{contextLabels.length ? <><p className="mt-1 text-xs leading-5 text-muted-foreground">Actual results saved in this browser session will be sent with questions.</p><ul className="mt-3 space-y-2">{contextLabels.map((label) => <li key={label} className="flex items-center gap-2 text-xs"><Check className="size-3.5 text-wc-teal" />{label}</li>)}</ul><button type="button" onClick={removeContext} className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"><Trash2 className="size-3.5" /> Clear analysis context</button></> : <p className="mt-1 text-xs leading-5 text-muted-foreground">No Brain results attached. Run image, clinical, or multimodal analysis in this tab to let the assistant explain its actual output.</p>}<div className="mt-3 flex flex-wrap gap-2"><Link className="text-xs font-medium text-wc-violet hover:underline" href="/brain-image">MRI analysis</Link><span className="text-muted-foreground">·</span><Link className="text-xs font-medium text-wc-violet hover:underline" href="/brain-clinical">Clinical report</Link><span className="text-muted-foreground">·</span><Link className="text-xs font-medium text-wc-violet hover:underline" href="/brain-multimodal">MRI + clinical</Link></div></div>
      <div className="rounded-2xl border border-border bg-card p-4"><h3 className="text-sm font-semibold">About this assistant</h3><p className="mt-2 text-xs leading-5 text-muted-foreground">Brain-focused educational support for MRI concepts, glioma terminology, IDH, MGMT, 1p/19q, and questions to discuss with a neuro-oncology team.</p><p className="mt-3 text-xs leading-5 text-muted-foreground">For new severe neurological symptoms such as a seizure or sudden weakness, seek emergency medical care.</p></div>
    </aside>
  </div>
}
