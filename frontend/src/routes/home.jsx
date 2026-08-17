import Home from '../pages/Home.jsx'
import NotFound from '../pages/NotFound.jsx'

const homeRoutes = [
  { path: '/', element: <Home /> },
  { path: '*', element: <NotFound /> },
]

export default homeRoutes
