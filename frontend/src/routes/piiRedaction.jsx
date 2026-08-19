import FeatureLayout from '../components/FeatureLayout.jsx'
import PIIRedaction from '../pages/PIIRedaction.jsx'

const piiRedactionRoutes = {
  path: 'pii-redaction',
  element: <FeatureLayout title="PII Redaction" />,
  children: [{ index: true, element: <PIIRedaction /> }],
}

export default piiRedactionRoutes
