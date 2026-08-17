import FeatureLayout from '../components/FeatureLayout.jsx'
import IntentClassifier from '../pages/IntentClassifier.jsx'

const intentClassifierRoutes = {
  path: 'intent-classifier',
  element: <FeatureLayout title="Intent Classifier" />,
  children: [{ index: true, element: <IntentClassifier /> }],
}

export default intentClassifierRoutes
