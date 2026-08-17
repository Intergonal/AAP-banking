import { useEffect, useState } from 'react'

export default function IntentClassifier() {
  const [health, setHealth] = useState('checking...')

  useEffect(() => {
    fetch('/api/intent-classifier/health')
      .then((res) => res.json())
      .then((data) => setHealth(JSON.stringify(data)))
      .catch(() => setHealth('backend unreachable'))
  }, [])

  return (
    <section>
      <h2>Intent Classifier</h2>
      <p>Placeholder page for the intent classifier feature.</p>
      <p>Backend health: {health}</p>
    </section>
  )
}
