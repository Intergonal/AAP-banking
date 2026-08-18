import { useState } from 'react'
import { Button } from '../components/ui/button.jsx'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card.jsx'
import { runPrediction } from './api.js'

const TICKERS = ['AAPL', 'AMZN', 'GOOG', 'MSFT']

export default function PredictionPanel() {
  const [ticker, setTicker] = useState(TICKERS[0])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleRun() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await runPrediction(ticker)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>5-Min Direction Prediction</CardTitle>
        <CardDescription>
          LSTM trained on 2020–2025 5-minute data. Predicts the direction of the
          next bar for AAPL, AMZN, GOOG, MSFT using the last 30 bars.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="h-8 rounded-lg border bg-background px-2.5 text-sm"
          >
            {TICKERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <Button onClick={handleRun} disabled={loading}>
            {loading ? 'Predicting…' : 'Run prediction'}
          </Button>
        </div>

        {error && (
          <p className="text-sm text-destructive">
            {error}
            {error.includes('waking') && (
              <span className="text-muted-foreground">
                {' '}
                (free Spaces hibernate after ~48h idle — retry in a minute)
              </span>
            )}
          </p>
        )}

        {result && (
          <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-muted/40 p-3 text-sm">
            <div>
              <span className="font-medium">{result.ticker}</span>
              <span className="text-muted-foreground"> @ ${result.price}</span>
            </div>
            <div
              className={
                result.direction === 'UP' ? 'text-green-600' : 'text-red-600'
              }
            >
              <span className="font-semibold">
                {result.direction === 'UP' ? '▲ UP' : '▼ DOWN'}
              </span>{' '}
              next bar
            </div>
            <div className="text-muted-foreground">
              confidence {(result.confidence * 100).toFixed(1)}%
            </div>
            <div className="ml-auto text-xs text-muted-foreground">
              as of {new Date(result.datetime).toLocaleString()}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}