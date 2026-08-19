import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export default function RequireAdmin({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (!user.is_admin) return <Navigate to="/" replace />
  return children
}