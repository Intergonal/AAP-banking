import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/context/AuthContext'
import { deleteUser, getUsers, setUserDisabled } from './api.js'

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function UsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [dialog, setDialog] = useState(null)
  const [password, setPassword] = useState('')
  const [dialogError, setDialogError] = useState(null)
  const [dialogBusy, setDialogBusy] = useState(false)

  async function load() {
    try {
      setUsers(await getUsers())
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function openDialog(u, action) {
    setDialog({ user: u, action })
    setPassword('')
    setDialogError(null)
  }

  async function handleConfirm(e) {
    e.preventDefault()
    if (!dialog) return
    setDialogBusy(true)
    setDialogError(null)
    try {
      if (dialog.action === 'delete') {
        await deleteUser(dialog.user.id, password)
      } else {
        await setUserDisabled(dialog.user.id, true, password)
      }
      setDialog(null)
      await load()
    } catch (err) {
      setDialogError(err.message)
    } finally {
      setDialogBusy(false)
    }
  }

  async function enableUser(u) {
    setBusyId(u.id)
    try {
      await setUserDisabled(u.id, false)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Card>
      <CardContent>
        {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
        {!users ? (
          <p className="text-sm text-muted-foreground">Loading users…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => {
                const isSelf = u.id === user?.id
                const busy = busyId === u.id
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">
                      {u.name}
                      {isSelf && (
                        <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={u.is_admin ? 'secondary' : 'outline'}>
                        {u.is_admin ? 'Admin' : 'User'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.disabled ? 'destructive' : 'default'}>
                        {u.disabled ? 'Disabled' : 'Active'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(u.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {u.disabled ? (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busy}
                            onClick={() => enableUser(u)}
                          >
                            Enable
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={isSelf || busy}
                            onClick={() => openDialog(u, 'disable')}
                          >
                            Disable
                          </Button>
                        )}
                        {!isSelf && !u.is_admin && (
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={busy}
                            onClick={() => openDialog(u, 'delete')}
                          >
                            <Trash2 data-icon="inline-start" />
                            Delete
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog
        open={!!dialog}
        onOpenChange={(open) => {
          if (!open && !dialogBusy) setDialog(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialog?.action === 'delete' ? 'Delete account' : 'Disable account'}
            </DialogTitle>
            <DialogDescription>
              {dialog?.action === 'delete'
                ? `Permanently delete the account for ${dialog?.user?.name} (${dialog?.user?.email})? This cannot be undone.`
                : `Disable the account for ${dialog?.user?.name} (${dialog?.user?.email})? They will not be able to log in until re-enabled.`}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleConfirm} className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="admin-password">Your password</Label>
              <Input
                id="admin-password"
                type="password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Confirm your password"
                className="h-8"
              />
            </div>
            {dialogError && <p className="text-sm text-destructive">{dialogError}</p>}
            <DialogFooter>
              <DialogClose render={<Button variant="outline" type="button" />}>
                Cancel
              </DialogClose>
              <Button
                type="submit"
                variant={dialog?.action === 'delete' ? 'destructive' : 'default'}
                disabled={dialogBusy || !password}
              >
                {dialogBusy
                  ? '…'
                  : dialog?.action === 'delete'
                    ? 'Delete account'
                    : 'Disable account'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
