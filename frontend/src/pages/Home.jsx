import { Link } from 'react-router-dom'
import { Button, buttonVariants } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'

export default function Home() {
  const { user, logout } = useAuth()

  return (
    <div className="mx-auto max-w-2xl p-8 text-center">
      <h1 className="text-3xl font-semibold">AAP Banking</h1>
      <p className="mt-2 text-muted-foreground">Pick a feature to get started.</p>

      {user ? (
        <div className="mt-6 flex items-center justify-center gap-4">
          <p>
            Logged in as <span className="font-medium">{user.name}</span> (
            {user.email})
          </p>
          <Button variant="outline" onClick={logout}>
            Log out
          </Button>
        </div>
      ) : (
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/login" className={buttonVariants()}>
            Log in
          </Link>
          <Link to="/register" className={buttonVariants({ variant: 'outline' })}>
            Register
          </Link>
        </div>
      )}

      <ul className="mt-10 space-y-2">
        <li>
          <Link to="/stock-assistant" className="underline underline-offset-4">
            Stock Assistant
          </Link>
        </li>
        <li>
          <Link to="/intent-classifier" className="underline underline-offset-4">
            Intent Classifier
          </Link>
        </li>
        <li>
          <Link to="/email-drafter" className="underline underline-offset-4">
            Email Drafter
          </Link>
        </li>
      </ul>
    </div>
  )
}