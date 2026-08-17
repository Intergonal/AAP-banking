import FeatureLayout from '../components/FeatureLayout.jsx'
import StockAssistant from '../pages/StockAssistant.jsx'

const stockAssistantRoutes = {
  path: 'stock-assistant',
  element: <FeatureLayout title="Stock Assistant" />,
  children: [{ index: true, element: <StockAssistant /> }],
}

export default stockAssistantRoutes
