import { useEffect, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Button } from '../components/ui/button.jsx'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card.jsx'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog.jsx'
import { Input } from '../components/ui/input.jsx'
import { Label } from '../components/ui/label.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getAccount, getRecipient, getTransfers, sendTransfer } from './api.js'

function fmtMoney(v) {
  if (v === null || v === undefined) return '—'
  return `$${Number(v).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function fmtDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function TransferPage() {
  const { user } = useAuth()
  const [account, setAccount] = useState(null)
  const [accountError, setAccountError] = useState('')
  const [toEmail, setToEmail] = useState('')
  const [amount, setAmount] = useState('')
  const [transfers, setTransfers] = useState([])
  const [sending, setSending] = useState(false)
  const [message, setMessage] = useState(null)
  const [confirming, setConfirming] = useState(null)

  async function loadAll() {
    try {
      setAccount(await getAccount())
      setAccountError('')
    } catch (err) {
      setAccount(null)
      setAccountError(err.message)
    }
    try {
      setTransfers(await getTransfers())
    } catch {
      setTransfers([])
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  function handleSubmit(e) {
    e.preventDefault()
    const value = parseFloat(amount)
    if (!toEmail.trim()) {
      setMessage({ kind: 'error', text: 'Enter the recipient email.' })
      return
    }
    if (!Number.isFinite(value) || value <= 0) {
      setMessage({ kind: 'error', text: 'Enter an amount greater than zero.' })
      return
    }
    setMessage(null)
    getRecipient(toEmail.trim())
      .then((receiver) =>
        setConfirming({
          email: toEmail.trim(),
          value,
          sender: { name: user?.name, email: user?.email },
          receiver,
        })
      )
      .catch((err) => setMessage({ kind: 'error', text: err.message }))
  }

  function confirmTransfer() {
    if (!confirming) return
    setSending(true)
    sendTransfer(confirming.email, confirming.value)
      .then((result) => {
        setAccount(result.account)
        setToEmail('')
        setAmount('')
        setConfirming(null)
        setMessage({
          kind: 'success',
          text: `Sent ${fmtMoney(result.amount)} to ${result.to_name} (${result.to_email}).`,
        })
        return getTransfers().then(setTransfers)
      })
      .catch((err) => {
        setConfirming(null)
        setMessage({ kind: 'error', text: err.message })
      })
      .finally(() => setSending(false))
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent>
          {accountError ? (
            <p className="text-sm text-destructive">{accountError}</p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-3 max-w-sm">
              <p className="text-sm text-muted-foreground">
                Send money to any registered user's account. Paper trading demo — no real money
                is moved.
              </p>
              <p className="text-sm text-muted-foreground">
                Available: <span className="font-medium text-foreground">{fmtMoney(account?.cash)}</span>
              </p>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="transfer-email">Recipient email</Label>
                <Input
                  id="transfer-email"
                  type="email"
                  value={toEmail}
                  onChange={(e) => setToEmail(e.target.value)}
                  placeholder="recipient@example.com"
                  className="h-8"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="transfer-amount">Amount</Label>
                <Input
                  id="transfer-amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="h-8"
                />
              </div>
              {message && (
                <p
                  className={`text-sm ${
                    message.kind === 'error' ? 'text-destructive' : 'text-emerald-600'
                  }`}
                >
                  {message.text}
                </p>
              )}
              <Button type="submit" disabled={sending || !account}>
                {sending ? 'Sending…' : 'Send'}
              </Button>
            </form>
          )}
          <Dialog
            open={confirming !== null}
            onOpenChange={(open) => {
              if (!open && !sending) setConfirming(null)
            }}
          >
            <DialogContent showCloseButton={!sending}>
              <DialogHeader>
                <DialogTitle>Confirm Details</DialogTitle>
              </DialogHeader>
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                <div className="flex flex-col items-center gap-0.5 text-center">
                  <p className="text-sm font-medium">{confirming?.sender?.name}</p>
                  <p className="max-w-full text-xs text-muted-foreground break-all">
                    {confirming?.sender?.email}
                  </p>
                </div>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
                <div className="flex flex-col items-center gap-0.5 text-center">
                  <p className="text-sm font-medium">{confirming?.receiver?.name}</p>
                  <p className="max-w-full text-xs text-muted-foreground break-all">
                    {confirming?.receiver?.email}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between gap-2 rounded-lg border bg-muted/50 px-3 py-2">
                <span className="text-sm text-muted-foreground">Amount</span>
                <span className="text-base font-semibold">{fmtMoney(confirming?.value)}</span>
              </div>
              <DialogFooter>
                <DialogClose render={<Button variant="outline" disabled={sending} />}>
                  Cancel
                </DialogClose>
                <Button onClick={confirmTransfer} disabled={sending}>
                  {sending ? 'Sending…' : 'Confirm'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent transfers</CardTitle>
          <CardDescription>Your last 20 incoming and outgoing transfers.</CardDescription>
        </CardHeader>
        <CardContent>
          {transfers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No transfers yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-1.5 pr-2 font-medium">Direction</th>
                    <th className="py-1.5 pr-2 font-medium">Counterparty</th>
                    <th className="py-1.5 pr-2 font-medium">Amount</th>
                    <th className="py-1.5 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((t) => (
                    <tr key={t.id} className="border-b">
                      <td className="py-1.5 pr-2">
                        {t.direction === 'out' ? (
                          <span className="rounded bg-destructive/10 px-1.5 py-0.5 text-xs font-medium text-destructive">
                            Sent
                          </span>
                        ) : (
                          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-xs font-medium text-emerald-600">
                            Received
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 pr-2">
                        {t.counterparty_name}
                        <span className="ml-1 text-xs text-muted-foreground">
                          {t.counterparty_email}
                        </span>
                      </td>
                      <td
                        className={`py-1.5 pr-2 ${
                          t.direction === 'out' ? 'text-destructive' : 'text-emerald-600'
                        }`}
                      >
                        {t.direction === 'out' ? '-' : '+'}
                        {fmtMoney(t.amount)}
                      </td>
                      <td className="py-1.5 text-muted-foreground">{fmtDate(t.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}