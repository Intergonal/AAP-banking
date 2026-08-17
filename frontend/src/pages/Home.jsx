import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div>
      <h1>AAP Banking</h1>
      <p>Pick a feature to get started.</p>
      <ul>
        <li>
          <Link to="/stock-assistant">Stock Assistant</Link>
        </li>
        <li>
          <Link to="/intent-classifier">Intent Classifier</Link>
        </li>
        <li>
          <Link to="/email-drafter">Email Drafter</Link>
        </li>
      </ul>
    </div>
  )
}
