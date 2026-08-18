import { useEffect, useRef, useState } from 'react'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts'
import { cn } from '@/lib/utils'

const PERIODS = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: '1D' },
]

const INITIAL_CANDLES = 90
const PREPEND_CHUNK = 60

function cssVar(name, fallback) {
  return (
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
  )
}

function oklchToRgba(input) {
  const match = input.match(/oklch\(([^)]+)\)/i)
  if (!match) return null
  const parts = match[1].split(/\s+/).filter(Boolean)
  if (parts.length < 3) return null
  let L = parseFloat(parts[0])
  let C = parseFloat(parts[1])
  const H = parseFloat(parts[2])
  if (parts[0].endsWith('%')) L /= 100
  if (parts[1].endsWith('%')) C /= 100
  let alpha = 1
  const alphaIdx = parts.indexOf('/')
  if (alphaIdx !== -1 && parts[alphaIdx + 1]) {
    alpha = parts[alphaIdx + 1].endsWith('%')
      ? parseFloat(parts[alphaIdx + 1]) / 100
      : parseFloat(parts[alphaIdx + 1])
  }
  const a = C * Math.cos((H * Math.PI) / 180)
  const b = C * Math.sin((H * Math.PI) / 180)
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b
  const s_ = L - 0.0894841775 * a - 1.291485548 * b
  const l = l_ ** 3
  const m = m_ ** 3
  const s = s_ ** 3
  let r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
  let g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
  let bl = -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s
  const clamp = (v) => (v < 0 ? 0 : v > 1 ? 1 : v)
  r = clamp(r)
  g = clamp(g)
  bl = clamp(bl)
  const to8 = (v) =>
    Math.round((v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055) * 255)
  return `rgba(${to8(r)}, ${to8(g)}, ${to8(bl)}, ${alpha})`
}

function chartColor(color, fallback) {
  if (!color) return fallback
  if (/^oklch\(/i.test(color)) {
    const rgba = oklchToRgba(color)
    if (rgba) return rgba
  }
  return color
}

function withAlpha(color, alpha) {
  const m = color.match(/^rgba?\(([^)]+)\)$/)
  if (m) {
    const [r, g, b] = m[1].split(',').map(Number)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }
  return color
}

function toSeconds(datetime) {
  const ms = Date.parse(datetime)
  return Number.isNaN(ms) ? 0 : Math.floor(ms / 1000)
}

function buildPredictedCandle(candles, prediction) {
  if (!candles.length || !prediction) return null
  const last = candles[candles.length - 1]
  const recent = candles.slice(-10)
  const meanMove = recent.reduce((sum, c) => sum + (c.close - c.open), 0) / recent.length
  const avgBody =
    recent.reduce((sum, c) => sum + Math.abs(c.close - c.open), 0) / recent.length
  const delta = Math.max(Math.abs(meanMove), avgBody) * (0.6 + prediction.confidence)

  const up = prediction.direction === 'UP'
  const open = last.close
  const close = up ? open + delta : open - delta
  return {
    time: toSeconds(last.datetime) + 5 * 60,
    open,
    high: Math.max(open, close) + delta * 0.25,
    low: Math.min(open, close) - delta * 0.25,
    close,
    predicted: true,
    direction: prediction.direction,
    confidence: prediction.confidence,
  }
}

function formatLabel(datetime, period) {
  const d = new Date(datetime)
  if (Number.isNaN(d.getTime())) return datetime
  if (period === '1d') {
    return d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
  }
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function PriceChart({
  symbol,
  period,
  points,
  prediction,
  predictionError,
  onPeriodChange,
  loading,
}) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const markersRef = useRef(null)
  const tooltipRef = useRef(null)
  const periodRef = useRef(period)
  const pointsRef = useRef([])
  const visibleCountRef = useRef(INITIAL_CANDLES)
  const initialFitDoneRef = useRef(false)
  const loadMorePendingRef = useRef(false)
  const [themeTick, setThemeTick] = useState(0)
  const [visibleCount, setVisibleCount] = useState(INITIAL_CANDLES)

  useEffect(() => {
    periodRef.current = period
  }, [period])

  useEffect(() => {
    pointsRef.current = points || []
    initialFitDoneRef.current = false
    loadMorePendingRef.current = false
    const total = (points || []).length
    setVisibleCount(Math.min(INITIAL_CANDLES, total))
  }, [points])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const upColor = chartColor(cssVar('--chart-2'), '#22c55e')
    const downColor = chartColor(cssVar('--destructive'), '#ef4444')
    const textColor = chartColor(cssVar('--foreground'), '#09090b')
    const gridColor = chartColor(cssVar('--border'), 'rgba(128, 128, 128, 0.15)')

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor,
      },
      grid: {
        vertLines: { color: 'rgba(128, 128, 128, 0.08)' },
        horzLines: { color: gridColor },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        priceFormatter: (p) => `$${p.toFixed(2)}`,
      },
    })
    chartRef.current = chart

    const series = chart.addSeries(CandlestickSeries, {
      upColor,
      downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor,
    })
    seriesRef.current = series
    markersRef.current = createSeriesMarkers(series, [])

    const tooltip = document.createElement('div')
    tooltip.style.display = 'none'
    tooltip.className =
      'pointer-events-none absolute z-10 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl'
    el.appendChild(tooltip)
    tooltipRef.current = tooltip

    function onCrosshair(param) {
      if (!param.point || param.time === undefined) {
        tooltip.style.display = 'none'
        return
      }
      const d = param.seriesData.get(series)
      if (!d) {
        tooltip.style.display = 'none'
        return
      }
      const up = d.close >= d.open
      const color = up ? 'var(--chart-2)' : 'var(--destructive)'
      const isPred = typeof d.predicted === 'boolean' && d.predicted
      const label = isPred
        ? new Date((d.time + 5 * 60) * 1000)
        : new Date(d.time * 1000)
      const rows = isPred
        ? `
            <div class="grid grid-cols-2 gap-x-4 gap-y-0.5">
              <span class="text-muted-foreground">Predicted (LSTM)</span>
              <span style="color:${color}">${d.direction === 'UP' ? '▲ UP' : '▼ DOWN'}</span>
              <span class="text-muted-foreground">Confidence</span>
              <span>${(d.confidence * 100).toFixed(1)}%</span>
            </div>`
        : `
            <div class="grid grid-cols-2 gap-x-4 gap-y-0.5">
              <span class="text-muted-foreground">Open</span><span>$${d.open.toFixed(2)}</span>
              <span class="text-muted-foreground">High</span><span>$${d.high.toFixed(2)}</span>
              <span class="text-muted-foreground">Low</span><span>$${d.low.toFixed(2)}</span>
              <span class="text-muted-foreground">Close</span><span style="color:${color}">$${d.close.toFixed(2)}</span>
            </div>`
      tooltip.innerHTML = `
        <p class="mb-1 font-medium">${formatLabel(label.toISOString(), periodRef.current)}</p>
        ${rows}`
      const elRect = el.getBoundingClientRect()
      const left = param.point.x + 12
      const top = param.point.y + 12
      tooltip.style.display = 'block'
      tooltip.style.left = `${Math.min(left, elRect.width - 220)}px`
      tooltip.style.top = `${Math.min(top, elRect.height - 90)}px`
    }
    chart.subscribeCrosshairMove(onCrosshair)

    function onVisibleRange(range) {
      if (!range) return
      const total = pointsRef.current.length
      const visible = visibleCountRef.current
      if (range.from <= 1 && visible < total && !loadMorePendingRef.current) {
        loadMorePendingRef.current = true
        const prevRange = { from: range.from, to: range.to }
        setVisibleCount((c) => {
          const next = Math.min(c + PREPEND_CHUNK, total)
          visibleCountRef.current = next
          requestAnimationFrame(() => {
            chart.timeScale().setVisibleLogicalRange({
              from: prevRange.from + (next - c),
              to: prevRange.to + (next - c),
            })
            loadMorePendingRef.current = false
          })
          return next
        })
      }
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRange)

    const observer = new MutationObserver(() => setThemeTick((t) => t + 1))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

    return () => {
      observer.disconnect()
      chart.unsubscribeCrosshairMove(onCrosshair)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRange)
      tooltip.remove()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      markersRef.current = null
      tooltipRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current
    const chart = chartRef.current
    const markers = markersRef.current
    if (!series || !chart || !markers) return

    const upColor = chartColor(cssVar('--chart-2'), '#22c55e')
    const downColor = chartColor(cssVar('--destructive'), '#ef4444')
    series.applyOptions({
      upColor,
      downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor,
    })
    chart.applyOptions({
      layout: {
        textColor: chartColor(cssVar('--foreground'), '#09090b'),
        background: { type: ColorType.Solid, color: 'transparent' },
      },
    })

    const real = pointsRef.current
      .slice(-visibleCount)
      .map((p) => ({
        time: toSeconds(p.datetime),
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      }))
    const predicted = buildPredictedCandle(real, prediction)

    let bars = real
    let marker = null
    if (predicted) {
      const baseColor = predicted.direction === 'UP' ? upColor : downColor
      bars = [
        ...real,
        {
          ...predicted,
          color: withAlpha(baseColor, 0.35),
          borderColor: withAlpha(baseColor, 0.6),
          wickColor: withAlpha(baseColor, 0.5),
        },
      ]
      marker = {
        time: predicted.time,
        position: 'aboveBar',
        color: predicted.direction === 'UP' ? upColor : downColor,
        shape: predicted.direction === 'UP' ? 'arrowUp' : 'arrowDown',
        text: `LSTM ${predicted.direction} ${(predicted.confidence * 100).toFixed(0)}%`,
      }
    }

    series.setData(bars)
    markers.setMarkers(marker ? [marker] : [])
    chart.timeScale().applyOptions({ timeVisible: period !== '1d' })
    if (!initialFitDoneRef.current) {
      chart.timeScale().fitContent()
      initialFitDoneRef.current = true
    }
  }, [points, prediction, period, themeTick, visibleCount])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {symbol} · Candles
          {loading && <span className="ml-2 text-xs text-muted-foreground">loading…</span>}
          {period === '5m' && !loading && (
            <span
              className={cn(
                'ml-2 text-xs',
                prediction
                  ? 'text-muted-foreground'
                  : predictionError
                    ? 'text-destructive/80'
                    : 'text-muted-foreground/60'
              )}
            >
              {prediction
                ? `LSTM predicts ${prediction.direction} (${(prediction.confidence * 100).toFixed(0)}%)`
                : predictionError
                  ? 'LSTM prediction unavailable'
                  : ''}
            </span>
          )}
        </p>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => onPeriodChange(p.value)}
              className={cn(
                'h-7 rounded-md px-2.5 text-xs font-medium transition-colors',
                period === p.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/70'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <div ref={containerRef} className="relative h-80 w-full" />
    </div>
  )
}
