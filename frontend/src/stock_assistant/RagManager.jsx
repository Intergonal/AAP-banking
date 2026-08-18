import { useEffect, useState } from 'react'
import { Button } from '../components/ui/button.jsx'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card.jsx'
import {
  addCommentaryEntry,
  addGlossaryEntry,
  addMdSection,
  deleteCommentaryEntry,
  deleteGlossaryEntry,
  deleteMdSection,
  getKb,
  updateCommentaryEntry,
  updateGlossaryEntry,
  updateMdSection,
} from './api.js'

const TABS = [
  { id: 'glossary', label: 'Glossary' },
  { id: 'commentary', label: 'Commentary' },
  { id: 'markdown', label: 'Markdown Notes' },
]

export default function RagManager() {
  const [tab, setTab] = useState('glossary')
  const [kb, setKb] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getKb()
      .then((data) => {
        setKb(data)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [])

  async function mutate(fn, payload) {
    setBusy(true)
    setError(null)
    try {
      const updated = await fn(payload)
      setKb(updated)
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>RAG Knowledge Base</CardTitle>
          <CardDescription>
            Content the agent retrieves via search_knowledge_base. Changes are
            re-embedded immediately and visible to the agent. Writes require login.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={
                  tab === t.id
                    ? 'h-8 rounded-lg bg-primary px-2.5 text-sm text-primary-foreground'
                    : 'h-8 rounded-lg border bg-background px-2.5 text-sm hover:bg-muted'
                }
              >
                {t.label}
              </button>
            ))}
            <span className="ml-auto text-xs text-muted-foreground">
              {kb ? `${kb.chunks} chunks · ${kb.embedded ? 'embedded' : 'not embedded'}` : ''}
            </span>
          </div>

          {error && (
            <p className="mb-3 text-sm text-destructive">
              {error}
              {error.includes('unauthorized') && (
                <span className="text-muted-foreground">
                  {' '}
                  — log in to modify the knowledge base.
                </span>
              )}
            </p>
          )}

          {!kb && !error && (
            <p className="text-sm text-muted-foreground">Loading knowledge base…</p>
          )}

          {kb && tab === 'glossary' && (
            <EntrySection
              entries={kb.glossary}
              keyLabel="Term"
              valueLabel="Definition"
              keyOf={(e) => e.term}
              valueOf={(e) => e.definition}
              onAdd={(k, v) => mutate(addGlossaryEntry, { term: k, definition: v })}
              onUpdate={(k, v) => mutate(updateGlossaryEntry, { term: k, definition: v })}
              onDelete={(k) => mutate(deleteGlossaryEntry, k)}
              busy={busy}
            />
          )}

          {kb && tab === 'commentary' && (
            <EntrySection
              entries={kb.commentary}
              keyLabel="Topic"
              valueLabel="Content"
              keyOf={(e) => e.topic}
              valueOf={(e) => e.content}
              onAdd={(k, v) => mutate(addCommentaryEntry, { topic: k, content: v })}
              onUpdate={(k, v) => mutate(updateCommentaryEntry, { topic: k, content: v })}
              onDelete={(k) => mutate(deleteCommentaryEntry, k)}
              busy={busy}
            />
          )}

          {kb && tab === 'markdown' && (
            <MarkdownSection files={kb.markdown} mutate={mutate} busy={busy} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function EntrySection({
  entries,
  keyLabel,
  valueLabel,
  keyOf,
  valueOf,
  onAdd,
  onUpdate,
  onDelete,
  busy,
}) {
  const [adding, setAdding] = useState(false)

  return (
    <div className="flex flex-col gap-2">
      {!adding && (
        <div>
          <Button size="sm" variant="outline" onClick={() => setAdding(true)} disabled={busy}>
            Add {keyLabel.toLowerCase()}
          </Button>
        </div>
      )}
      {adding && (
        <FieldForm
          keyLabel={keyLabel}
          valueLabel={valueLabel}
          submitLabel="Add"
          onSubmit={async (k, v) => {
            const ok = await onAdd(k, v)
            if (ok) setAdding(false)
            return ok
          }}
          onCancel={() => setAdding(false)}
          busy={busy}
        />
      )}
      {entries.length === 0 && !adding && (
        <p className="text-sm text-muted-foreground">No entries yet.</p>
      )}
      {entries.map((e, i) => (
        <EntryRow
          key={i}
          entry={e}
          keyLabel={keyLabel}
          valueLabel={valueLabel}
          keyOf={keyOf}
          valueOf={valueOf}
          onUpdate={onUpdate}
          onDelete={onDelete}
          busy={busy}
        />
      ))}
    </div>
  )
}

function MarkdownSection({ files, mutate, busy }) {
  const [file, setFile] = useState(files[0]?.file ?? null)
  const current = files.find((f) => f.file === file) ?? files[0]

  if (!current) {
    return <p className="text-sm text-muted-foreground">No markdown files found.</p>
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground">File</label>
        <select
          value={current.file}
          onChange={(e) => setFile(e.target.value)}
          className="h-8 rounded-lg border bg-background px-2.5 text-sm"
        >
          {files.map((f) => (
            <option key={f.file} value={f.file}>
              {f.file}
            </option>
          ))}
        </select>
      </div>
      <EntrySection
        entries={current.sections}
        keyLabel="Heading"
        valueLabel="Content"
        keyOf={(s) => s.heading}
        valueOf={(s) => s.content}
        onAdd={(k, v) => mutate(addMdSection, { file: current.file, heading: k, content: v })}
        onUpdate={(k, v) =>
          mutate(updateMdSection, { file: current.file, heading: k, content: v })
        }
        onDelete={(k) => mutate(deleteMdSection, current.file, k)}
        busy={busy}
      />
    </div>
  )
}

function EntryRow({
  entry,
  keyLabel,
  valueLabel,
  keyOf,
  valueOf,
  onUpdate,
  onDelete,
  busy,
}) {
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const key = keyOf(entry)
  const value = valueOf(entry)

  if (editing) {
    return (
      <div className="rounded-lg border bg-background p-3">
        <FieldForm
          keyLabel={keyLabel}
          valueLabel={valueLabel}
          initialKey={key}
          initialValue={value}
          submitLabel="Save"
          readonlyKey
          onSubmit={async (k, v) => {
            const ok = await onUpdate(k, v)
            if (ok) setEditing(false)
            return ok
          }}
          onCancel={() => setEditing(false)}
          busy={busy}
        />
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-medium">{key}</div>
          <p className="mt-0.5 line-clamp-4 text-xs whitespace-pre-wrap text-muted-foreground">
            {value}
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Button size="sm" variant="outline" onClick={() => setEditing(true)} disabled={busy}>
            Edit
          </Button>
          {confirming ? (
            <>
              <Button
                size="sm"
                variant="destructive"
                onClick={async () => {
                  const ok = await onDelete(key)
                  if (ok) setConfirming(false)
                }}
                disabled={busy}
              >
                Confirm
              </Button>
              <Button size="sm" variant="outline" onClick={() => setConfirming(false)} disabled={busy}>
                Cancel
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setConfirming(true)}
              disabled={busy}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function FieldForm({
  keyLabel,
  valueLabel,
  initialKey = '',
  initialValue = '',
  submitLabel,
  onSubmit,
  onCancel,
  busy,
  readonlyKey = false,
}) {
  const [key, setKey] = useState(initialKey)
  const [value, setValue] = useState(initialValue)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!key.trim() || !value.trim()) return
    await onSubmit(key.trim(), value.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 rounded-lg border bg-muted/40 p-3">
      <input
        value={key}
        onChange={(e) => setKey(e.target.value)}
        placeholder={`${keyLabel}...`}
        disabled={busy || readonlyKey}
        className="h-8 rounded-lg border bg-background px-2.5 text-sm disabled:opacity-60"
      />
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={`${valueLabel}...`}
        rows={3}
        disabled={busy}
        className="rounded-lg border bg-background px-2.5 py-1.5 text-sm"
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={busy || !key.trim() || !value.trim()}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" size="sm" variant="outline" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}