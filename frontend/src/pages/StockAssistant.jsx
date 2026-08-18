import { useState } from 'react'
import { Button } from '../components/ui/button.jsx'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card.jsx'
import ChatMessage from '../stock_assistant/ChatMessage.jsx'
import PredictionPanel from '../stock_assistant/PredictionPanel.jsx'
import { sendChat } from '../stock_assistant/api.js'

export default function StockAssistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const history = messages
    .filter((m) => m.content)
    .map((m) => ({ role: m.role, text: m.content }))

  async function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const data = await sendChat(text, history)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          toolCalls: data.tool_calls || [],
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, toolCalls: [] },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PredictionPanel />

      <Card>
        <CardHeader>
          <CardTitle>Investment Assistant</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex max-h-96 min-h-48 flex-col gap-3 overflow-y-auto p-1">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Ask about your portfolio, stock prices, news, analyst ratings,
                market indices, or investment concepts (e.g. “Analyze my
                portfolio”, “What is the latest news on AAPL?”, “Explain
                dollar-cost averaging”).
              </p>
            )}
            {messages.map((m, i) => (
              <ChatMessage key={i} message={m} />
            ))}
            {loading && (
              <p className="text-sm text-muted-foreground">Assistant is thinking…</p>
            )}
          </div>

          <form onSubmit={handleSend} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about stocks, portfolio, or investments..."
              className="h-8 flex-1 rounded-lg border bg-background px-2.5 text-sm"
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              Send
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}