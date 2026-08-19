const MATH_TOOL_NAMES = new Set([
  'calculate',
  'calculate_returns',
  'moving_average',
  'volatility',
  'correlation',
  'portfolio_stats',
  'time_value',
  'cagr',
  'linear_trend',
])

export default function ToolCallTrace({ toolCalls }) {
  if (!toolCalls?.length) return null
  return (
    <div className="flex max-w-[85%] flex-col gap-1.5">
      {toolCalls.map((tc, i) => {
        const isMath = tc.category === 'math' || MATH_TOOL_NAMES.has(tc.name)
        return (
          <details
            key={i}
            className="rounded-lg border bg-muted/50 px-3 py-1.5 text-xs"
          >
            <summary className="cursor-pointer font-medium">
              {isMath ? (
                <>
                  <span className="mr-1.5 rounded bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-violet-600">
                    Math
                  </span>
                  {mathSummary(tc)}
                </>
              ) : (
                <>
                  {tc.name}({truncate(formatArgs(tc.args), 100)})
                </>
              )}
            </summary>
            {tc.result && (
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-background p-2 text-muted-foreground">
                {tc.result}
              </pre>
            )}
          </details>
        )
      })}
    </div>
  )
}

function mathSummary(tc) {
  const args = tc.args || {}
  if (tc.name === 'calculate') {
    const expr = typeof args.expression === 'string' ? args.expression : ''
    return `calculate: ${truncate(expr, 80)}`
  }
  return `${tc.name}(${truncate(formatArgs(tc.args), 80)})`
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