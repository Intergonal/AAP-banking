import StockAssistant from '../pages/StockAssistant.jsx'
import TradingPage from '../stock_assistant/TradingPage.jsx'
import TransferPage from '../stock_assistant/TransferPage.jsx'

const stockAssistantRoutes = {
  path: 'stock-assistant',
  children: [
    { index: true, element: <StockAssistant /> },
    { path: 'trading', element: <TradingPage /> },
    { path: 'transfer', element: <TransferPage /> },
  ],
}

export default stockAssistantRoutes