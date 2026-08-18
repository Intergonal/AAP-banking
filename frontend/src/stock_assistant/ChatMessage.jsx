import ToolCallTrace from './ToolCallTrace.jsx'

export default function ChatMessage({ message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {message.toolCalls?.length > 0 && <ToolCallTrace toolCalls={message.toolCalls} />}
      <div className="max-w-[85%] rounded-lg border bg-card px-3 py-2 text-sm">
        <span className="whitespace-pre-wrap">{message.content || '…'}</span>
      </div>
    </div>
  )
}