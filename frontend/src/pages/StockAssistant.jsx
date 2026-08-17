import { useEffect, useState } from 'react'

export default function StockAssistant() {
  const [health, setHealth] = useState('checking...')

  useEffect(() => {
    fetch('/api/stock-assistant/health')
      .then((res) => res.json())
      .then((data) => setHealth(JSON.stringify(data)))
      .catch(() => setHealth('backend unreachable'))
  }, [])

  return (
    <section>
      <h2>Stock Assistant</h2>
      <p>Placeholder page for the stock assistant feature.</p>
      <p>Backend health: {health}</p>
    </section>
  )
}
