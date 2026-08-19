import { Outlet } from 'react-router-dom'

export default function FeatureLayout(props) {
  const { children } = props
  return <div className="flex flex-col gap-4">{children ?? <Outlet />}</div>
}