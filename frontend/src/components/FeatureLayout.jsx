import { Link, Outlet } from 'react-router-dom'

export default function FeatureLayout({ title }) {
  return (
    <div>
      <nav>
        <Link to="/">Home</Link>
        <span> / {title}</span>
      </nav>
      <Outlet />
    </div>
  )
}
