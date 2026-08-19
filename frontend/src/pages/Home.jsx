import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Database,
  Mail,
  MessageSquare,
  Shield,
  Sparkles,
  TrendingUp,
  MessageCircleQuestionMark,
  LayoutDashboard,
  UsersRound,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useAuth } from '@/context/AuthContext'

const FEATURES = [
  {
    to: '/stock-assistant',
    icon: MessageSquare,
    title: 'Stock Assistant',
    description:
      'Ask about stocks, markets, and investment concepts with live data and analysis.',
  },
  {
    to: '/stock-assistant/trading',
    icon: TrendingUp,
    title: 'Trading',
    description:
      'Trade with live prices, charts, and P&L tracking.',
  },
  {
    to: '/admin/rag',
    icon: Database,
    title: 'RAG Management',
    description:
      'Manage the knowledge base that powers the assistant — glossary, commentary, and docs.',
  },
  {
    to: '/intent-classifier',
    icon: Sparkles,
    title: 'Intent Classifier',
    description: 'Classify user messages into banking intents with the ML classifier.',
  },
  {
    to: '/email-drafter',
    icon: Mail,
    title: 'Email Drafter',
    description: 'Draft banking and support emails from a short prompt.',
  },
  {
    to: '/submit-ticket',
    icon: MessageCircleQuestionMark,
    title: 'Help',
    description: 'Send a ticket to our customer support team.',
  },
  {
    to: '/ticket-dashboard',
    icon: LayoutDashboard,
    title: 'Ticket Dashboard',
    description: 'View customer tickets.',
  },
  {
    to: '/pii-redaction',
    icon: Shield,
    title: 'PII Redaction',
    description: 'Mask sensitive personal information before safe analysis or sharing.',
  },
  {
    to: '/shareholder-assistant',
    icon: UsersRound,
    title: 'Shareholder Assistant',
    description: 'Support investor research, shareholder updates, and portfolio communications.',
  },
]

export default function Home() {
  const { user } = useAuth()

  return (
    <div className="mx-auto max-w-4xl">
      <section className="mt-6 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">
          Welcome back{user?.name ? `, ${user.name}` : ''}
        </h2>
        <p className="mt-2 text-muted-foreground">Pick a feature to get started.</p>
      </section>

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        {FEATURES.map(({ to, icon: Icon, title, description }) => (
          <Link key={to} to={to} className="group">
            <Card className="h-full transition-colors group-hover:border-ring">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <span className="rounded-lg border bg-muted p-2">
                  <Icon className="size-5" />
                </span>
                <CardTitle className="text-base">{title}</CardTitle>
              </CardHeader>
              <CardContent className="flex items-start justify-between gap-3">
                <CardDescription>{description}</CardDescription>
                <ArrowRight className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </section>
    </div>
  )
}