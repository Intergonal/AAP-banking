export default function ToolCallTrace({ toolCalls }) {
  if (!toolCalls?.length) return null
  return (
    <div className="flex max-w-[85%] flex-col gap-1.5">
      {toolCalls.map((tc, i) => (
        <details
          key={i}
          className="rounded-lg border bg-muted/50 px-3 py-1.5 text-xs"
        >
          <summary className="cursor-pointer font-medium">
            {tc.name}({truncate(formatArgs(tc.args), 100)})
          </summary>
          {tc.result && (
            <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-background p-2 text-muted-foreground">
              {tc.result}
            </pre>
          )}
        </details>
      ))}
    </div>
  )
}

function truncate(text, max) {
  if (text.length <= max) return text
  return text.slice(0, max) + '…'
}

function formatArgs(args) {
  if (!args || Object.keys(args).length === 0) return ''
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === 'string' ? `"${v}"` : v}`)
    .join(', ')
}