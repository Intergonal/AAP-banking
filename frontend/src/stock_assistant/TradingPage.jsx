import { useEffect, useState } from 'react'
import { SearchIcon } from 'lucide-react'
import { Button } from '../components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card.jsx'
import { Input } from '../components/ui/input.jsx'
import { Label } from '../components/ui/label.jsx'
import { getAccount, getPriceSeries, getQuote, placeTrade, resetAccount, runPrediction } from './api.js'
import PriceChart from './PriceChart.jsx'
import SymbolSearchDialog from './SymbolSearchDialog.jsx'

const MODEL_TICKERS = ['AAPL', 'AMZN', 'GOOG', 'MSFT']

function fmtMoney(v) {
  if (v === null || v === undefined) return '—'
  return `$${Number(v).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function fmtSigned(v) {
  if (v === null || v === undefined) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${fmtMoney(v)}`
}

export default function TradingPage() {
  const [symbol, setSymbol] = useState('AAPL')
  const [searchOpen, setSearchOpen] = useState(false)
  const [period, setPeriod] = useState('30m')
  const [points, setPoints] = useState([])
  const [chartLoading, setChartLoading] = useState(false)
  const [chartError, setChartError] = useState('')
  const [prediction, setPrediction] = useState(null)
  const [predictionError, setPredictionError] = useState('')

  const [quote, setQuote] = useState(null)
  const [account, setAccount] = useState(null)
  const [accountError, setAccountError] = useState('')
  const [message, setMessage] = useState(null)

  const [side, setSide] = useState('buy')
  const [quantity, setQuantity] = useState('')
  const [trading, setTrading] = useState(false)

  async function loadAccount() {
    try {
      setAccount(await getAccount())
      setAccountError('')
    } catch (err) {
      setAccount(null)
      setAccountError(err.message)
    }
  }

  async function loadPrediction(sym, per) {
    setPrediction(null)
    setPredictionError('')
    if (per !== '5m' || !MODEL_TICKERS.includes(sym)) return
    try {
      setPrediction(await runPrediction(sym))
    } catch (err) {
      setPredictionError(err.message)
    }
  }

  async function loadChart(sym, per) {
    setChartLoading(true)
    setChartError('')
    try {
      const data = await getPriceSeries(sym, per)
      setPoints(data.points)
      setSymbol(sym)
    } catch (err) {
      setPoints([])
      setChartError(err.message)
    } finally {
      setChartLoading(false)
    }
    loadPrediction(sym, per)
  }

  async function loadQuote(sym) {
    try {
      setQuote(await getQuote(sym))
    } catch {
      setQuote(null)
    }
  }

  useEffect(() => {
    loadAccount()
  }, [])

  useEffect(() => {
    loadChart(symbol, period)
    loadQuote(symbol)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSelectSymbol(sym) {
    setSearchOpen(false)
    if (sym === symbol) return
    loadChart(sym, period)
    loadQuote(sym)
  }

  function handlePeriodChange(p) {
    setPeriod(p)
    loadChart(symbol, p)
  }

  function handleTrade(e) {
    e.preventDefault()
    const qty = parseInt(quantity, 10)
    if (!qty || qty <= 0) {
      setMessage({ kind: 'error', text: 'Enter a positive whole number of shares.' })
      return
    }
    setTrading(true)
    setMessage(null)
    placeTrade({ symbol, side, quantity: qty })
      .then((acc) => {
        setAccount(acc)
        setQuantity('')
        setMessage({
          kind: 'success',
          text: `${side === 'buy' ? 'Bought' : 'Sold'} ${qty} × ${symbol} at ${fmtMoney(
            quote?.price
          )}.`,
        })
      })
      .catch((err) => setMessage({ kind: 'error', text: err.message }))
      .finally(() => setTrading(false))
  }

  async function handleReset() {
    if (!window.confirm('Reset your trading account to $100,000 cash with no positions?')) return
    try {
      setAccount(await resetAccount())
      setMessage({ kind: 'success', text: 'Account reset to $100,000.' })
    } catch (err) {
      setMessage({ kind: 'error', text: err.message })
    }
  }

  const positions = account?.positions || []
  const estimated = quote?.price && parseInt(quantity, 10) > 0
    ? Number(quote.price) * parseInt(quantity, 10)
    : null

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4">
          <p className="text-xs text-muted-foreground">
            Paper trading demo — prices are live from Yahoo Finance, no real
            money is moved.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex h-8 w-44 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-xs outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring"
            >
              <SearchIcon className="size-3.5 text-muted-foreground" data-icon="inline-start" />
              <span className="truncate font-medium">{symbol}</span>
            </button>
            {quote && (
              <span className="text-sm text-muted-foreground">
                {quote.symbol}: {fmtMoney(quote.price)}{' '}
                {quote.change_pct !== null && quote.change_pct !== undefined && (
                  <span
                    className={
                      quote.change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'
                    }
                  >
                    ({quote.change_pct >= 0 ? '+' : ''}
                    {quote.change_pct}%)
                  </span>
                )}
              </span>
            )}
          </div>
          <SymbolSearchDialog
            open={searchOpen}
            onOpenChange={setSearchOpen}
            onSelect={handleSelectSymbol}
          />

          {chartError ? (
            <p className="text-sm text-red-600">{chartError}</p>
          ) : (
            <PriceChart
              symbol={symbol}
              period={period}
              points={points}
              prediction={prediction}
              predictionError={predictionError}
              onPeriodChange={handlePeriodChange}
              loading={chartLoading}
            />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {accountError ? (
              <p className="text-sm text-red-600">
                {accountError} — log in to access your account.
              </p>
            ) : !account ? (
              <p className="text-sm text-muted-foreground">Loading account…</p>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="rounded-lg border p-2">
                    <p className="text-xs text-muted-foreground">Cash</p>
                    <p className="font-medium">{fmtMoney(account.cash)}</p>
                  </div>
                  <div className="rounded-lg border p-2">
                    <p className="text-xs text-muted-foreground">Total value</p>
                    <p className="font-medium">{fmtMoney(account.total_value)}</p>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th className="py-1.5 pr-2 font-medium">Ticker</th>
                        <th className="py-1.5 pr-2 font-medium">Shares</th>
                        <th className="py-1.5 pr-2 font-medium">Avg</th>
                        <th className="py-1.5 pr-2 font-medium">Price</th>
                        <th className="py-1.5 pr-2 font-medium">Value</th>
                        <th className="py-1.5 font-medium">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.length === 0 && (
                        <tr>
                          <td colSpan={6} className="py-3 text-muted-foreground">
                            No positions yet — place your first trade.
                          </td>
                        </tr>
                      )}
                      {positions.map((p) => (
                        <tr key={p.ticker} className="border-b">
                          <td className="py-1.5 pr-2 font-medium">{p.ticker}</td>
                          <td className="py-1.5 pr-2">{p.quantity}</td>
                          <td className="py-1.5 pr-2">{fmtMoney(p.avg_price)}</td>
                          <td className="py-1.5 pr-2">{fmtMoney(p.current_price)}</td>
                          <td className="py-1.5 pr-2">{fmtMoney(p.market_value)}</td>
                          <td
                            className={`py-1.5 ${
                              p.unrealized_pl >= 0 ? 'text-emerald-600' : 'text-red-600'
                            }`}
                          >
                            {fmtSigned(p.unrealized_pl)} (
                            {p.unrealized_pl_pct >= 0 ? '+' : ''}
                            {p.unrealized_pl_pct}%)
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <Button variant="outline" className="w-fit" onClick={handleReset}>
                  Reset account
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Place a trade</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <form onSubmit={handleTrade} className="flex flex-col gap-3">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={side === 'buy' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setSide('buy')}
                >
                  Buy
                </Button>
                <Button
                  type="button"
                  variant={side === 'sell' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setSide('sell')}
                >
                  Sell
                </Button>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="trade-quantity">Shares of {symbol}</Label>
                <Input
                  id="trade-quantity"
                  type="number"
                  min="1"
                  step="1"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="e.g. 5"
                  className="h-8"
                />
              </div>

              {estimated !== null && (
                <p className="text-xs text-muted-foreground">
                  Estimated {side === 'buy' ? 'cost' : 'proceeds'}:{' '}
                  {fmtMoney(estimated)} @ {fmtMoney(quote?.price)}
                </p>
              )}

              {message && (
                <p
                  className={`text-sm ${
                    message.kind === 'error' ? 'text-red-600' : 'text-emerald-600'
                  }`}
                >
                  {message.text}
                </p>
              )}

              <Button
                type="submit"
                disabled={trading || !account || !quantity || !quote}
              >
                {trading ? 'Executing…' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}