'use client'

import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, MessageCircle, ShieldAlert } from 'lucide-react'
import { Badge, EmptyState, inputClass, Panel, PanelHeader } from '@/components/common/primitives'
import { isApiConfigured } from '@/lib/api-client'
import { assistantService, type AssistantStatus } from '@/services/assistant-service'

type ChatLine = { role: 'user' | 'assistant'; text: string; sources?: { title: string; organization: string; topic: string; url: string }[]; datasetMetadata?: { name: string; task: string; manifest: string; status: string; accessUrl?: string }[] }

export function AssistantWorkspace() {
  const cancerType = 'skin' as const
  const [status, setStatus] = useState<AssistantStatus | null>(null)
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [conversationId, setConversationId] = useState<string>()
  const [messages, setMessages] = useState<ChatLine[]>([])

  useEffect(() => {
    if (isApiConfigured) assistantService.status().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : 'Assistant status unavailable.'))
  }, [])

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submitted = question.trim()
    if (!submitted || busy) return
    const history = messages.map((item) => ({ role: item.role, content: item.text })).slice(-8)
    setMessages((current) => [...current, { role: 'user', text: submitted }])
    setQuestion('')
    setBusy(true)
    setError(null)
    try {
      const response = await assistantService.ask({ message: submitted, cancerType, history, conversationId })
      setConversationId(response.conversationId)
      setMessages((current) => [...current, { role: 'assistant', text: response.answer, sources: response.sources, datasetMetadata: response.datasetMetadata }])
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Assistant is not available.'
      setError(message)
      setQuestion(submitted)
      setMessages((current) => [...current, { role: 'assistant', text: `No generated answer was returned. ${message}` }])
    } finally {
      setBusy(false)
    }
  }

  return <Panel>
    <PanelHeader title="Skin Cancer AI Assistant" description="Educational information from the configured Groq API." icon={MessageCircle} action={<Badge tone={status?.providerConfigured ? 'emerald' : status ? 'amber' : 'amber'}>{status?.providerConfigured ? 'Groq connected' : status ? 'Configuration required' : 'Checking setup'}</Badge>} />
    <div className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex items-start gap-3 rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4"><ShieldAlert className="mt-0.5 size-5 shrink-0 text-wc-amber" /><div><p className="text-sm font-semibold">Educational information only</p><p className="mt-1 text-sm text-muted-foreground">Responses are generated directly by the configured Groq API. They do not diagnose, prescribe, or replace assessment by a qualified healthcare professional. {status?.message ?? 'Check backend configuration.'}</p></div></div>
      {messages.length > 0 && <ol aria-label="Conversation history" className="flex max-h-96 flex-col gap-3 overflow-y-auto rounded-xl border border-border bg-elevated p-4">{messages.map((message, index) => <li key={`${message.role}-${index}`} className={`max-w-[92%] rounded-xl px-4 py-3 text-sm ${message.role === 'user' ? 'self-end bg-primary text-primary-foreground' : 'self-start border border-border bg-card'}`}><p className="mb-1 text-[11px] font-semibold uppercase opacity-70">{message.role === 'user' ? 'You' : 'Assistant'}</p>{message.role === 'assistant' ? (
  <div className="max-w-none break-words [&_h1]:mb-2 [&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-bold [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:mb-2 [&_h3]:mt-3 [&_h3]:text-sm [&_h3]:font-semibold [&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-1 [&_a]:underline [&_a]:underline-offset-2 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_pre]:overflow-x-auto">
    <ReactMarkdown>
      {message.text.replace(/\\([#*_>])/g, '$1')}
    </ReactMarkdown>
  </div>
) : (
  <p className="whitespace-pre-wrap">{message.text}</p>
)}{message.sources && message.sources.length > 0 && <div className="mt-3 border-t border-border pt-2"><p className="mb-1 text-xs font-semibold">Educational sources</p><ul className="list-inside list-disc">{message.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{source.title}</a> <span className="text-muted-foreground">— {source.organization} · {source.topic}</span></li>)}</ul></div>}{message.datasetMetadata && message.datasetMetadata.length > 0 && <div className="mt-3 border-t border-border pt-2"><p className="mb-1 text-xs font-semibold">Dataset and data access metadata</p><ul className="list-inside list-disc">{message.datasetMetadata.map((item) => <li key={item.name}>{item.name}: {item.task}; {item.status} ({item.manifest.startsWith('https://') ? <a className="underline" href={item.manifest} target="_blank" rel="noreferrer">documentation</a> : <>manifest: <code>{item.manifest}</code></>}){item.accessUrl && <> · <a className="underline" href={item.accessUrl} target="_blank" rel="noreferrer">access details</a></>}</li>)}</ul></div>}</li>)}</ol>}
      <form onSubmit={submit} className="flex flex-col gap-3"><label htmlFor="assistant-question" className="text-sm font-medium">Your question</label><textarea id="assistant-question" value={question} onChange={(e) => setQuestion(e.target.value)} className={`${inputClass} min-h-28 resize-y py-3`} placeholder="Ask an educational question about skin cancer…" maxLength={2000} /><button disabled={!isApiConfigured || busy || !question.trim()} className="inline-flex h-10 items-center justify-center gap-2 self-start rounded-xl brand-gradient px-4 text-sm font-semibold text-white disabled:opacity-50">{busy && <Loader2 className="size-4 animate-spin" />}{busy ? 'Sending to Groq…' : 'Ask the assistant'}</button></form>
      {error && <EmptyState icon={MessageCircle} title="Assistant unavailable" description={error} className="border-amber-500/30 bg-amber-500/5" />}
      <p className="text-xs leading-relaxed text-muted-foreground">A qualified healthcare professional should assess personal symptoms or test results. WeCure does not diagnose, prescribe medication or treatment, or promise cures.</p>
    </div>
  </Panel>
}
