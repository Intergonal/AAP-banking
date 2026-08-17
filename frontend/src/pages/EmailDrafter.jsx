import { useEffect, useState } from 'react'

export default function EmailDrafter() {
  const [health, setHealth] = useState('checking...')

  useEffect(() => {
    fetch('/api/email-drafter/health')
      .then((res) => res.json())
      .then((data) => setHealth(JSON.stringify(data)))
      .catch(() => setHealth('backend unreachable'))
  }, [])

  return (
    <section>
      <h2>Email Drafter</h2>
      <p>Placeholder page for the email drafter feature.</p>
      <p>Backend health: {health}</p>
    </section>
  )
}
