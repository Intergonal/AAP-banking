import { Outlet, useLocation } from 'react-router-dom'
import { Separator } from '@/components/ui/separator'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import AppSidebar from './app-sidebar.jsx'
import ThemeToggle from './ThemeToggle.jsx'

const PAGE_TITLES = {
  '/': 'Home',
  '/stock-assistant': 'Stock Assistant',
  '/stock-assistant/trading': 'Trading',
  '/stock-assistant/transfer': 'Transfer',
  '/intent-classifier': 'Intent Classifier',
  '/email-drafter': 'Email Drafter',
  '/admin/rag': 'RAG Management',
  '/admin/users': 'Users',
}

export default function AppLayout() {
  const { pathname } = useLocation()
  const title =
    PAGE_TITLES[pathname] ??
    pathname
      .split('/')
      .filter(Boolean)
      .at(-1)
      ?.replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase()) ??
    'Home'

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-12 shrink-0 items-center gap-2 border-b bg-card px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <span className="text-sm font-medium">{title}</span>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <div className="flex flex-1 flex-col p-4">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
