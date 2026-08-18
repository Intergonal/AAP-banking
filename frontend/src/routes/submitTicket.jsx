import FeatureLayout from '../components/FeatureLayout.jsx'
import SubmitTicket from '../pages/SubmitTicket.jsx'

const submitTicketRoutes = {
  path: 'submit-ticket',
  element: <FeatureLayout title="Contact Support" />,
  children: [{ index: true, element: <SubmitTicket /> }],
}

export default submitTicketRoutes