import { Link, useLocation } from 'react-router-dom'
import {
  ArrowLeftRight,
  Database,
  Landmark,
  LogOut,
  Mail,
  MessageSquare,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'

const FEATURE_ITEMS = [
  { to: '/', label: 'Home', icon: Landmark, end: true },
  { to: '/stock-assistant', label: 'Stock Assistant', icon: MessageSquare },
  { to: '/stock-assistant/trading', label: 'Trading', icon: TrendingUp },
  { to: '/stock-assistant/transfer', label: 'Transfer', icon: ArrowLeftRight },
  { to: '/intent-classifier', label: 'Intent Classifier', icon: Sparkles },
  { to: '/email-drafter', label: 'Email Drafter', icon: Mail },
]

const ADMIN_ITEMS = [
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/rag', label: 'RAG Management', icon: Database },
]

function NavItem({ to, label, icon: Icon, end }) {
  const { pathname } = useLocation()
  const isActive = end ? pathname === to : pathname.startsWith(to)
  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        render={<Link to={to} />}
        isActive={isActive}
        tooltip={label}
      >
        <Icon />
        <span className="group-data-[collapsible=icon]:hidden">{label}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

export default function AppSidebar() {
  const { user, logout } = useAuth()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link to="/" />}>
              <div className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Landmark className="size-4" />
              </div>
              <span className="group-data-[collapsible=icon]:hidden font-semibold">Bankly</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Features</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {FEATURE_ITEMS.map((item) => (
                <NavItem key={item.to} {...item} />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {user?.is_admin && (
          <SidebarGroup>
            <SidebarGroupLabel>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {ADMIN_ITEMS.map((item) => (
                  <NavItem key={item.to} {...item} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip={user?.name}>
              <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                {(user?.name || '?').charAt(0).toUpperCase()}
              </span>
              <span className="group-data-[collapsible=icon]:hidden truncate">{user?.name}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={logout} tooltip="Log out">
              <LogOut />
              <span className="group-data-[collapsible=icon]:hidden">Log out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
