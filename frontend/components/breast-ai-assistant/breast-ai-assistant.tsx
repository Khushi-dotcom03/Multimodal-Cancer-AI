'use client'

import { useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  AlertCircle,
  Bot,
  LoaderCircle,
  MessageCircle,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react'
import { sendBreastAIMessage, type BreastAIMessage } from '@/services/breast-ai-assistant-service'
import { BreastCancerModuleNav } from '@/components/analysis/breast-cancer-module-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader, Panel } from '@/components/common/primitives'

const SUGGESTED_QUESTIONS = [
  'What are the early symptoms of breast cancer?',
  'What are the common risk factors?',
  'What is the difference between a mammogram and an ultrasound?',
  'What are the available treatment approaches?',
]

export function BreastAIAssistant() {
  const [messages, setMessages] = useState<BreastAIMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [disclaimer, setDisclaimer] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const message = input.trim()
    if (!message || loading) return

    const previousMessages = messages
    setMessages((current) => [...current, { role: 'user', content: message }])
    setInput('')
    setError('')
    setLoading(true)

    try {
      const response = await sendBreastAIMessage(message, previousMessages)
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: response.reply },
      ])
      setDisclaimer(response.disclaimer)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  function startNewConversation() {
    if (loading) return
    setMessages([])
    setInput('')
    setError('')
    setDisclaimer('')
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Breast Cancer · AI Assistant"
        title="Breast Cancer AI Assistant"
        description="An AI-powered educational assistant for breast cancer awareness, screening, risk factors, diagnosis processes and treatment information."
      />

      <BreastCancerModuleNav />

      <Panel className="flex min-h-[620px] flex-col overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-border p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-wc-pink/10 text-wc-pink">
              <Bot className="size-6" />
            </div>
            <div>
              <p className="font-semibold">Breast Cancer Assistant</p>
              <p className="text-xs text-muted-foreground">
                Educational support · AI powered
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={startNewConversation}
            disabled={loading || messages.length === 0}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshCw className="size-3.5" />
            New chat
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-5 p-4 sm:p-6">
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center py-8 text-center">
              <div className="mb-4 flex size-16 items-center justify-center rounded-2xl bg-wc-pink/10 text-wc-pink">
                <MessageCircle className="size-8" />
              </div>

              <h2 className="text-xl font-semibold">
                How can I help you today?
              </h2>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                Ask questions about breast cancer awareness, symptoms,
                screening, risk factors and treatment approaches.
              </p>

              <div className="mt-7 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                {SUGGESTED_QUESTIONS.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => setInput(question)}
                    className="rounded-xl border border-border p-3 text-left text-sm transition-colors hover:border-wc-pink/50 hover:bg-muted"
                  >
                    <Sparkles className="mb-2 size-4 text-wc-pink" />
                    {question}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              {messages.map((message, index) => (
                <div
                  key={`${index}-${message.role}`}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'flex-row-reverse' : ''
                  }`}
                >
                  <div
                    className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${
                      message.role === 'assistant'
                        ? 'bg-wc-pink/10 text-wc-pink'
                        : 'bg-muted text-foreground'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <Bot className="size-5" />
                    ) : (
                      <User className="size-5" />
                    )}
                  </div>

                    <div
                    className={`max-w-[85%] min-w-0 rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      message.role === 'assistant'
                        ? 'rounded-tl-sm bg-muted'
                        : 'rounded-tr-sm bg-primary text-primary-foreground'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <div className="assistant-markdown">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({ node, ...props }) => (
                              <div className="assistant-markdown-table">
                                <table {...props} />
                              </div>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <div className="flex size-9 items-center justify-center rounded-xl bg-wc-pink/10 text-wc-pink">
                    <Bot className="size-5" />
                  </div>
                  <span className="inline-flex items-center gap-2">
                    <LoaderCircle className="size-4 animate-spin" />
                    Assistant is thinking...
                  </span>
                </div>
              )}
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {disclaimer && (
            <p className="rounded-lg bg-muted/60 p-3 text-xs leading-relaxed text-muted-foreground">
              {disclaimer}
            </p>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="border-t border-border bg-muted/20 p-4"
        >
          <div className="flex items-end gap-2 rounded-xl border border-border bg-background p-2 focus-within:border-wc-pink/60">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="Ask a breast cancer-related question..."
              rows={2}
              maxLength={4000}
              disabled={loading}
              className="max-h-32 min-h-12 flex-1 resize-y bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
            />

            <button
              type="submit"
              disabled={!input.trim() || loading}
              aria-label="Send message"
              className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? (
                <LoaderCircle className="size-5 animate-spin" />
              ) : (
                <Send className="size-5" />
              )}
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Educational information only · Not a substitute for professional medical advice
          </p>
        </form>
      </Panel>

      <ResearchDisclaimer />
    </div>
  )
}
