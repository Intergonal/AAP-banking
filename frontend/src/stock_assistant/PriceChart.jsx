import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const PERIODS = [
  { value: '1d', label: '1D' },
  { value: '5d', label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
]

function formatTick(datetime, period) {
  const d = new Date(datetime)
  if (Number.isNaN(d.getTime())) return ''
  if (period === '1d') {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function formatLabel(datetime, period) {
  const d = new Date(datetime)
  if (Number.isNaN(d.getTime())) return datetime
  if (period === '1d') {
    return d.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  return d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function PriceChart({ symbol, period, points, onPeriodChange, loading }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {symbol} · Closing prices
          {loading && <span className="ml-2 text-xs text-muted-foreground">loading…</span>}
        </p>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => onPeriodChange(p.value)}
              className={`h-7 rounded-md px-2.5 text-xs font-medium transition-colors ${
                period === p.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/70'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
            <XAxis
              dataKey="datetime"
              tickFormatter={(v) => formatTick(v, period)}
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              minTickGap={32}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(v) => `$${v}`}
              width={56}
            />
            <Tooltip
              formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Close']}
              labelFormatter={(v) => formatLabel(v, period)}
              contentStyle={{
                background: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke="hsl(var(--chart-1))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}