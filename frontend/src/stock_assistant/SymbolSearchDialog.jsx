import { useEffect, useRef, useState } from 'react'
import { SearchIcon } from 'lucide-react'
import { Input } from '../components/ui/input.jsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog.jsx'
import { searchSymbols } from './api.js'

export default function SymbolSearchDialog({ open, onOpenChange, onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const requestRef = useRef(0)

  useEffect(() => {
    if (!open) return
    setQuery('')
    setResults(null)
    setError('')
  }, [open])

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      setResults(null)
      setError('')
      return
    }
    const id = ++requestRef.current
    setLoading(true)
    setError('')
    const timer = setTimeout(async () => {
      try {
        const data = await searchSymbols(q)
        if (requestRef.current !== id) return
        setResults(data.results)
      } catch (e) {
        if (requestRef.current !== id) return
        setError(e.message)
        setResults(null)
      } finally {
        if (requestRef.current === id) setLoading(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  function pick(sym) {
    onSelect(sym)
    onOpenChange(false)
  }

  const q = query.trim().toUpperCase()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Search symbols</DialogTitle>
          <DialogDescription>
            Type a company name or ticker to load its chart.
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Apple or AAPL"
            className="h-9 pl-8"
            onKeyDown={(e) => {
              if (e.key !== 'Enter') return
              e.preventDefault()
              if (results?.length) pick(results[0].symbol)
              else if (q.length >= 2) pick(q)
            }}
          />
        </div>

        <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
          {loading && (
            <p className="px-1 py-2 text-xs text-muted-foreground">Searching…</p>
          )}
          {!loading && error && (
            <p className="px-1 py-2 text-xs text-destructive">
              {error} — press Enter to load the exact ticker anyway.
            </p>
          )}
          {!loading && !error && results?.length === 0 && q.length >= 2 && (
            <p className="px-1 py-2 text-xs text-muted-foreground">
              No results for {q}. Press Enter to load it anyway.
            </p>
          )}
          {!loading && !error &&
            (results?.length ?? 0) > 0 &&
            results.map((r) => (
              <button
                key={r.symbol}
                type="button"
                onClick={() => pick(r.symbol)}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted"
              >
                <span className="font-medium">{r.symbol}</span>
                <span className="truncate text-xs text-muted-foreground">{r.name}</span>
                {r.exchange && (
                  <span className="ml-auto text-xs text-muted-foreground/70">
                    {r.exchange}
                  </span>
                )}
              </button>
            ))}
          {!loading && !error && results === null && (
            <p className="px-1 py-2 text-xs text-muted-foreground">
              Type at least 2 characters.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}