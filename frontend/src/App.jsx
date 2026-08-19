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
import piiRedactionRoutes from './routes/piiRedaction.jsx'
import shareholderAssistantRoutes from './routes/shareholderAssistant.jsx'
import adminRoutes from './routes/admin.jsx'
import ticketDashboardRoutes from './routes/TicketDashboard.jsx'
import submitTicketRoutes from './routes/submitTicket.jsx'

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
      piiRedactionRoutes,
      shareholderAssistantRoutes,
      adminRoutes,
      ticketDashboardRoutes,
      submitTicketRoutes
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