import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'

const defaultPrompt = 'Summarise the key shareholder themes from the annual reports.'

export default function ShareholderAssistant() {
  const [documents, setDocuments] = useState([])
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Ask about dividends, earnings, strategy, operational performance, or investor highlights across the documents in the project folder.',
    },
  ])
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const [status, setStatus] = useState({ document_count: 0, chunk_count: 0, ready: false })

  async function refreshDocuments() {
    try {
      const data = await api('/shareholder-assistant/documents')
      setDocuments(data.documents || [])
      setStatus({
        document_count: data.document_count || 0,
        chunk_count: data.chunk_count || 0,
        ready: Boolean(data.ready),
      })
      setReady(Boolean(data.ready))
    } catch (error) {
      console.error(error)
    }
  }

  useEffect(() => {
    refreshDocuments()
  }, [])

  async function handleReindex() {
    try {
      const data = await api('/shareholder-assistant/reindex', { method: 'POST' })
      setStatus({
        document_count: data.document_count || 0,
        chunk_count: data.chunk_count || 0,
        ready: Boolean(data.ready),
      })
      setReady(Boolean(data.ready))
      await refreshDocuments()
    } catch (error) {
      console.error(error)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextMessage = message.trim()
    if (!nextMessage || loading || !ready) return

    const userMessage = { role: 'user', content: nextMessage }
    setMessages((current) => [...current, userMessage])
    setMessage('')
    setLoading(true)

    try {
      const data = await api('/shareholder-assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ message: nextMessage }),
      })

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: data.answer || 'I could not find a relevant answer in the uploaded annual reports.',
          sources: data.sources || [],
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: `I hit a problem: ${error.message}`,
          sources: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight">Shareholder Assistant</h2>
        <p className="text-muted-foreground">
          Ask questions about annual reports, operational performance, dividends, strategy, and investor updates using the Annual report database.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-1">
        <Card className="min-h-[620px]">
          <CardHeader>
            <CardTitle>Chat</CardTitle>
            <CardDescription>Use the annual reports as source material for your questions.</CardDescription>
          </CardHeader>
          <CardContent className="flex h-[520px] flex-col gap-4">
            <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border bg-muted/20 p-3">
              {messages.map((entry, index) => (
                <div
                  key={`${entry.role}-${index}`}
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-6 ${
                    entry.role === 'user'
                      ? 'ml-auto bg-primary text-primary-foreground'
                      : 'bg-background text-foreground'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{entry.content}</div>
                  {entry.sources && entry.sources.length > 0 && (
                    <div className="mt-2 border-t border-current/15 pt-2 text-xs opacity-80">
                      Sources: {entry.sources.join(', ')}
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="max-w-[85%] rounded-xl bg-background px-3 py-2 text-sm text-muted-foreground">
                  Searching the annual reports...
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={4}
                disabled={!ready}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={ready ? 'Ask about shareholder returns, revenue, debt, guidance, acquisitions, or strategic priorities...' : 'Waiting for documents to finish indexing...'}
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Button type="button" variant="ghost" onClick={() => setMessage(defaultPrompt)} disabled={!ready}>
                  Use sample prompt
                </Button>
                <Button type="submit" disabled={loading || !ready || !message.trim()}>
                  {loading ? 'Searching...' : 'Ask assistant'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
