import { NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'

export default function FeatureLayout({ title, nav }) {
  return (
    <div className="flex flex-col gap-4">
      {title && <h1 className="text-lg font-semibold">{title}</h1>}
      {nav && (
        <div className="inline-flex w-fit gap-1 rounded-lg border bg-card p-1">
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      )}
      <Outlet />
    </div>
  )
}