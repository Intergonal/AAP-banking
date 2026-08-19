import FeatureLayout from '../components/FeatureLayout.jsx'
import ShareholderAssistant from '../pages/ShareholderAssistant.jsx'

const shareholderAssistantRoutes = {
  path: 'shareholder-assistant',
  element: <FeatureLayout title="Shareholder Assistant" />,
  children: [{ index: true, element: <ShareholderAssistant /> }],
}

export default shareholderAssistantRoutes
