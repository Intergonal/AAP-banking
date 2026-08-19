import { useEffect, useMemo, useRef, useState } from 'react'
import { jsPDF } from 'jspdf'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'

export default function PIIRedaction() {
  const fileInputRef = useRef(null)
  const [text, setText] = useState('')
  const [fileName, setFileName] = useState('')
  const [result, setResult] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [selectedEntry, setSelectedEntry] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const count = useMemo(
    () => (result ? result.match(/\[(?:NAME|EMAIL|PHONE|ID-NUM|URL|USERNAME|ADDRESS|DATE|REDACTED)\]/g)?.length ?? 0 : 0),
    [result],
  )

  async function fetchHistory() {
    try {
      const rows = await api('/pii-redaction/history')
      setHistory(Array.isArray(rows) ? rows : [])
    } catch (err) {
      if (err.message !== 'unauthorized') {
        console.error(err)
      }
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  useEffect(() => {
    const isModalOpen = Boolean(selectedEntry || deleteTarget)
    document.body.style.overflow = isModalOpen ? 'hidden' : ''

    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedEntry, deleteTarget])

  async function handleFileUpload(event) {
    const uploaded = event.target.files?.[0]
    if (!uploaded) return

    const fileText = await uploaded.text().catch(() => '')
    if (!fileText.trim()) {
      setError('That file does not contain readable text. Please upload a text-based file.')
      return
    }

    setText(fileText)
    setFileName(uploaded.name)
    setError('')
    event.target.value = ''
  }

  async function handleRedact() {
    if (!text.trim()) {
      setError('Please enter or upload some text to redact.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const nextFileName = fileName && String(fileName).toLowerCase().startsWith('redaction-')
        ? getNextRedactionDocumentName(fileName)
        : fileName || getNextRedactionDocumentName()

      const data = await api('/pii-redaction/redact', {
        method: 'POST',
        body: JSON.stringify({ text, file_name: nextFileName }),
      })
      const redacted = data.redacted_text || text
      const savedFileName = data.saved_history?.file_name || nextFileName
      setResult(redacted)
      setFileName(savedFileName)
      await fetchHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(entryId) {
    try {
      await api(`/pii-redaction/history/${entryId}`, { method: 'DELETE' })
      await fetchHistory()
    } catch (err) {
      setError(err.message)
    }
  }

  function confirmDelete(entry) {
    setDeleteTarget(entry)
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) return
    await handleDelete(deleteTarget.id)
    setDeleteTarget(null)
  }

  function getPreview(value, maxLength = 180) {
    if (!value) return 'No content available.'
    const cleanValue = String(value).trim()
    return cleanValue.length > maxLength ? `${cleanValue.slice(0, maxLength).trim()}...` : cleanValue
  }

  function renderHighlightedText(value) {
    if (!value) {
      return <span className="text-muted-foreground">No redacted content available.</span>
    }

    const parts = String(value).split(/(\[[A-Z0-9-]+\])/g)

    return (
      <>
        {parts.map((part, index) => {
          if (/^\[[A-Z0-9-]+\]$/.test(part)) {
            return (
              <span
                key={`${part}-${index}`}
                className="rounded border border-destructive/30 bg-destructive/15 px-1 py-0.5 font-medium text-destructive shadow-sm"
              >
                {part}
              </span>
            )
          }

          return <span key={`${part}-${index}`}>{part}</span>
        })}
      </>
    )
  }

  function getNextRedactionDocumentName(currentName = fileName) {
    const candidates = []

    if (currentName) {
      const currentMatch = String(currentName).match(/redaction-(\d+)/i)
      if (currentMatch) {
        candidates.push(Number(currentMatch[1]))
      }
    }

    history.forEach((entry) => {
      const match = String(entry.file_name || '').match(/redaction-(\d+)/i)
      if (match) {
        candidates.push(Number(match[1]))
      }
    })

    const nextNumber = candidates.length > 0 ? Math.max(...candidates) + 1 : 1
    return `redaction-${String(nextNumber).padStart(4, '0')}.txt`
  }

  function handleDownloadPdf() {
    if (!result.trim()) {
      setError('Generate a redacted result before downloading PDF.')
      return
    }

    const doc = new jsPDF({ unit: 'pt', format: 'a4' })
    const lines = doc.splitTextToSize(result, 500)
    doc.setFontSize(11)
    doc.text(lines, 36, 40)
    doc.save(`${(fileName || 'redacted-document').replace(/\.[^/.]+$/, '') || 'redacted-document'}.pdf`)
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight">PII Redaction</h2>
        <p className="text-muted-foreground">
          Prepare customer documents by masking sensitive personal details before internal review or sharing.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Document text</CardTitle>
            <CardDescription>Paste text or upload a text file containing names, IDs, emails, phone numbers, or addresses.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.csv,.json,.log,.rtf"
                className="hidden"
                onChange={handleFileUpload}
              />
              <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                Upload file
              </Button>
              {fileName && <span className="text-sm text-muted-foreground">{fileName}</span>}
            </div>

            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              className="min-h-[260px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none ring-0 placeholder:text-muted-foreground focus-visible:border-ring"
              placeholder="Paste or type the document content here..."
            />

            <div className="flex flex-wrap gap-3">
              <Button onClick={handleRedact} disabled={loading || saving}>
                {loading ? 'Redacting...' : 'Redact text'}
              </Button>
              <Button variant="outline" onClick={() => setText('')}>
                Clear
              </Button>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Redacted output</CardTitle>
            <CardDescription>
              {result ? `${count} sensitive markers applied` : 'The masked version will appear here.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Redactions</p>
              <div className="min-h-[260px] whitespace-pre-wrap break-words text-sm leading-6 text-foreground">
                {renderHighlightedText(result || 'No redacted content yet.')}
              </div>
            </div>
            <Button variant="outline" onClick={handleDownloadPdf} disabled={!result}>
              Save as PDF
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Saved history</CardTitle>
          <CardDescription>Each entry is stored against your account and can be deleted at any time.</CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">No saved redactions yet.</p>
          ) : (
            <div className="space-y-4">
              {history.map((entry) => (
                <div
                  key={entry.id}
                  className="cursor-pointer rounded-lg border bg-muted/20 p-4 transition-colors hover:bg-muted/30"
                  onClick={() => setSelectedEntry(entry)}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{entry.file_name || 'Untitled document'}</p>
                      <p className="text-xs text-muted-foreground">
                        {entry.created_at ? new Date(entry.created_at).toLocaleString() : 'Recently saved'}
                      </p>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      className="border-destructive/40 hover:bg-destructive hover:text-destructive-foreground"
                      onClick={(event) => {
                        event.stopPropagation()
                        confirmDelete(entry)
                      }}
                    >
                      Delete
                    </Button>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-md border bg-background/80 p-3">
                      <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Original</p>
                      <p className="text-sm text-foreground/90">{getPreview(entry.original_text, 140)}</p>
                    </div>
                    <div className="rounded-md border bg-background/80 p-3">
                      <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Redacted</p>
                      <div className="text-sm text-foreground/90">{renderHighlightedText(getPreview(entry.redacted_text, 140))}</div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <span className="text-sm font-medium text-primary hover:underline">View full entry</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {selectedEntry && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm" onClick={() => setSelectedEntry(null)}>
              <div
                className="max-h-[85vh] w-full max-w-4xl overflow-hidden rounded-xl border bg-background shadow-2xl"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="flex items-center justify-between border-b px-4 py-3">
                  <div>
                    <h3 className="text-lg font-semibold">{selectedEntry.file_name || 'Untitled document'}</h3>
                    <p className="text-xs text-muted-foreground">
                      {selectedEntry.created_at ? new Date(selectedEntry.created_at).toLocaleString() : 'Recently saved'}
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setSelectedEntry(null)}>
                    Close
                  </Button>
                </div>

                <div className="grid max-h-[70vh] gap-4 overflow-auto p-4 md:grid-cols-2">
                  <div className="rounded-lg border bg-muted/20 p-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">Original</p>
                    <pre className="whitespace-pre-wrap break-words text-sm leading-6">{selectedEntry.original_text}</pre>
                  </div>
                  <div className="rounded-lg border bg-muted/20 p-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">Redacted</p>
                    <div className="whitespace-pre-wrap break-words text-sm leading-6">{renderHighlightedText(selectedEntry.redacted_text)}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {deleteTarget && (
            <div className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm" onClick={() => setDeleteTarget(null)}>
              <div
                className="w-full max-w-md rounded-xl border bg-card text-card-foreground shadow-2xl"
                onClick={(event) => event.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-history-title"
              >
                <div className="border-b px-5 py-4">
                  <h3 id="delete-history-title" className="text-lg font-semibold">Delete saved entry</h3>
                </div>
                <div className="space-y-2 px-5 py-4">
                  <p className="text-sm text-muted-foreground">
                    Are you sure you want to delete <span className="font-medium text-foreground">{deleteTarget.file_name || 'this redaction'}</span>?
                  </p>
                  <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
                </div>
                <div className="flex justify-end gap-3 border-t px-5 py-4">
                  <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    className="border-destructive/40 hover:bg-destructive hover:text-destructive-foreground"
                    onClick={handleConfirmDelete}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
