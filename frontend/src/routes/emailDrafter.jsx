import FeatureLayout from '../components/FeatureLayout.jsx'
import EmailDrafter from '../pages/EmailDrafter.jsx'

const emailDrafterRoutes = {
  path: 'email-drafter',
  element: <FeatureLayout title="Email Drafter" />,
  children: [{ index: true, element: <EmailDrafter /> }],
}

export default emailDrafterRoutes
