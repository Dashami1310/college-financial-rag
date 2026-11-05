import React, { useEffect, useRef, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader } from '../components/UI'
import { ragApi } from '../api/endpoints'
import { apiErrorMessage } from '../api/client'
import type { ChatMessage } from '../types'

const EXAMPLE_QUESTIONS = [
  'Which department overspent in Q2?',
  'Compare AIML and CSE expenditure.',
  'Show highest expenditure department.',
  'Which quarter had maximum spending?',
  'Summarize the financial report.',
]

export default function RagAssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: 'welcome',
    role: 'assistant',
    content: "Hi, I'm your financial assistant. Ask me anything about the institution's uploaded expenditure data — department comparisons, overspending, quarterly trends, or a general summary.",
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(question: string) {
    if (!question.trim() || loading) return
    setError('')
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: question }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)
    try {
      const res = await ragApi.chat(question)
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(), role: 'assistant',
        content: res.data.answer, sources: res.data.sources,
        generationMode: res.data.generation_mode,
      }
      setMessages((m) => [...m, assistantMsg])
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout title="RAG Financial Assistant">
      <SectionHeader
        eyebrow="Retrieval-Augmented Generation"
        title="Ask the Financial Assistant"
        description="Natural language question-answering over your uploaded expenditure data, powered by FAISS retrieval + Gemini generation."
      />

      <div className="flex h-[calc(100vh-13rem)] flex-col panel">
        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'rounded-br-sm bg-ledger-500 text-ink-950'
                  : 'rounded-bl-sm border border-ink-600 bg-ink-700/50 text-parchment/90'
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.role === 'assistant' && msg.generationMode === 'extractive' && (
                  <p className="mt-2 border-t border-ink-600/60 pt-2 text-[11px] text-parchment/40">
                    Extractive answer — add a valid GOOGLE_API_KEY in backend/.env for AI-generated explanations.
                  </p>
                )}
                {msg.sources && msg.sources.length > 0 && (
                  <details className="mt-2 border-t border-ink-600/60 pt-2">
                    <summary className="cursor-pointer text-xs font-medium text-ledger-300">
                      View {msg.sources.length} retrieved source{msg.sources.length > 1 ? 's' : ''}
                    </summary>
                    <div className="mt-2 space-y-1.5">
                      {msg.sources.map((s, i) => (
                        <p key={i} className="rounded-lg bg-ink-800/60 p-2 text-[11px] text-parchment/50">
                          {s.content}
                        </p>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border border-ink-600 bg-ink-700/50 px-4 py-3">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="h-1.5 w-1.5 animate-pulse rounded-full bg-ledger-400" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Example questions */}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 px-6 pb-3">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="rounded-full border border-ink-600 bg-ink-800/50 px-3 py-1.5 text-xs text-parchment/60 hover:border-ledger-500/50 hover:text-ledger-300 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {error && (
          <div className="mx-6 mb-2 rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-xs text-risk-critical">
            {error}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); sendMessage(input) }}
          className="flex items-center gap-3 border-t border-ink-600/60 p-4"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about departmental spending, anomalies, or trends…"
            className="input-field flex-1"
          />
          <button type="submit" disabled={loading || !input.trim()} className="btn-primary">
            Send
          </button>
        </form>
      </div>
    </AppLayout>
  )
}
