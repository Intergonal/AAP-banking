import FeatureLayout from '../components/FeatureLayout.jsx'
import TicketDashboard from '../pages/TicketDashboard.jsx'

const ticketDashboardRoutes = {
  path: 'ticket-dashboard',
  element: <FeatureLayout title="Customer Tickets" />,
  children: [{ index: true, element: <TicketDashboard /> }],
}

export default ticketDashboardRoutes