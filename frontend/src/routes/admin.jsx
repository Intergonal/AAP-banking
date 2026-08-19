import { Navigate, Outlet } from 'react-router-dom'
import RequireAdmin from '../components/RequireAdmin.jsx'
import RagManager from '../stock_assistant/RagManager.jsx'
import UsersPage from '../admin/UsersPage.jsx'

const adminRoutes = {
  path: 'admin',
  element: (
    <RequireAdmin>
      <Outlet />
    </RequireAdmin>
  ),
  children: [
    { index: true, element: <Navigate to="/admin/rag" replace /> },
    { path: 'rag', element: <RagManager /> },
    { path: 'users', element: <UsersPage /> },
  ],
}

export default adminRoutes