import FeatureLayout from '../components/FeatureLayout.jsx'
import StockAssistant from '../pages/StockAssistant.jsx'
import TradingPage from '../stock_assistant/TradingPage.jsx'

const stockAssistantRoutes = {
  path: 'stock-assistant',
  element: <FeatureLayout title="Stock Assistant" />,
  children: [
    { index: true, element: <StockAssistant /> },
    { path: 'trading', element: <TradingPage /> },
  ],
}

export default stockAssistantRoutes