import { Navigate } from 'react-router-dom'
import RagManager from '../stock_assistant/RagManager.jsx'

const adminRoutes = {
  path: 'admin',
  children: [
    { index: true, element: <Navigate to="/admin/rag" replace /> },
    { path: 'rag', element: <RagManager /> },
  ],
}

export default adminRoutes