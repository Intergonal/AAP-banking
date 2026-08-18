import { useState } from 'react'
import { api } from '../lib/api.js'

export default function IntentClassifier() {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleClassify = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const data = await api('/intent-classifier/classify', {
        method: 'POST',
        body: JSON.stringify({ text })
      });
      setResult(data);
    } catch (error) {
      console.error("Classification failed:", error);
      setResult({ error: "Failed to reach the classification server." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">Intent Classifier</h2>
      <p className="mb-4 text-gray-400">Test the ModernBERT classification and sentiment models.</p>
      
      <div className="flex flex-col gap-4">
        <textarea 
          className="w-full p-3 border rounded bg-transparent text-white"
          rows="4"
          placeholder="Enter a customer message here (e.g., 'My card was swallowed by the machine.')"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        
        <button 
          onClick={handleClassify}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Classify Intent'}
        </button>

        {result && !result.error && (
          <div className="mt-6 p-4 border rounded bg-gray-900">
            <h3 className="font-bold text-lg mb-2">Analysis Results:</h3>
            <p><strong>Intent:</strong> <span className="text-blue-400">{result.intent}</span></p>
            <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
            <p><strong>Sentiment:</strong> <span className={result.sentiment === 'NEGATIVE' ? 'text-red-400' : 'text-green-400'}>{result.sentiment}</span></p>
          </div>
        )}
        
        {result?.error && (
          <div className="mt-4 p-4 border border-red-500 text-red-500 rounded">
            {result.error}
          </div>
        )}
      </div>
    </section>
  )
}