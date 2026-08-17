import { useRoutes } from 'react-router-dom'
import homeRoutes from './routes/home.jsx'
import authRoutes from './routes/auth.jsx'
import stockAssistantRoutes from './routes/stockAssistant.jsx'
import intentClassifierRoutes from './routes/intentClassifier.jsx'
import emailDrafterRoutes from './routes/emailDrafter.jsx'

const routes = [
  homeRoutes,
  authRoutes,
  stockAssistantRoutes,
  intentClassifierRoutes,
  emailDrafterRoutes,
]

export default function App() {
  return useRoutes(routes)
}