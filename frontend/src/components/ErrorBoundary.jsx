import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="m-8 rounded-lg border border-red-600/40 bg-red-600/5 p-4">
          <h1 className="font-semibold text-red-600">Something went wrong</h1>
          <p className="mt-1 font-mono text-xs text-red-700">
            {String(this.state.error?.message || this.state.error)}
          </p>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap font-mono text-xs text-red-800">
            {this.state.error?.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 cursor-pointer rounded-md border border-border bg-background px-2.5 py-1 text-sm"
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
