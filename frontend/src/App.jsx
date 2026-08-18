import { useRoutes } from 'react-router-dom'
import AppLayout from './components/AppLayout.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import Home from './pages/Home.jsx'
import NotFound from './pages/NotFound.jsx'
import authRoutes from './routes/auth.jsx'
import stockAssistantRoutes from './routes/stockAssistant.jsx'
import intentClassifierRoutes from './routes/intentClassifier.jsx'
import emailDrafterRoutes from './routes/emailDrafter.jsx'
import adminRoutes from './routes/admin.jsx'

const routes = [
  ...authRoutes,
  { path: '*', element: <NotFound /> },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Home /> },
      stockAssistantRoutes,
      intentClassifierRoutes,
      emailDrafterRoutes,
      adminRoutes,
    ],
  },
]

export default function App() {
  return (
    <ErrorBoundary>
      <RouteTree />
    </ErrorBoundary>
  )
}

function RouteTree() {
  return useRoutes(routes)
}