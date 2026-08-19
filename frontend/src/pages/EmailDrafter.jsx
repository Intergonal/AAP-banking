import { useState } from 'react'
import { api } from '../lib/api.js'
import { marked } from 'marked' 

export default function EmailDrafter() {
  const [customerEmail, setCustomerEmail] = useState('alex.student@example.com')
  const [query, setQuery] = useState('')
  
  // State for the pipeline
  const [analysis, setAnalysis] = useState(null)
  const [draft, setDraft] = useState('')
  
  // Loading states to show exactly what the AI is doing
  const [loadingStep, setLoadingStep] = useState(null) // 'analyzing', 'drafting', 'iterating', 'sending', or null
  const [sendSuccess, setSendSuccess] = useState(false)

  // To track if the user has entered editing mode for the email draft
  const [isEditing, setIsEditing] = useState(false)

  const processTicket = async () => {
    if (!query.trim()) return;
    setAnalysis(null);
    setDraft('');
    setSendSuccess(false);
    setIsEditing(false);
    
    try {
      // Run the Classification
      setLoadingStep('analyzing');
      const classData = await api('/intent-classifier/classify', {
        method: 'POST',
        body: JSON.stringify({ text: query })
      });
      setAnalysis(classData);

      // Generate the Draft using the classification results
      setLoadingStep('drafting');
      const draftData = await api('/email-drafter/draft', {
        method: 'POST',
        body: JSON.stringify({ 
            email: customerEmail, 
            query: query,
            intent: classData.intent,
            sentiment: classData.sentiment 
        })
      });
      setDraft(draftData.draft);
      
    } catch (error) {
      console.error("Pipeline failed:", error);
      alert("An error occurred during processing. Check console.");
    } finally {
      setLoadingStep(null);
    }
  };

  // Draft iteration via Gemini 3.5 Flash
  const iterateDraft = async (actionType) => {
    if (!draft) return;
    setLoadingStep('iterating');
    setIsEditing(false);
    try {
      const data = await api('/email-drafter/iterate', {
        method: 'POST',
        body: JSON.stringify({ current_draft: draft, action: actionType })
      });
      setDraft(data.new_draft);
    } catch (error) {
      console.error("Iteration failed:", error);
    } finally {
      setLoadingStep(null);
    }
  };

  // Sending the Email
  const sendEmail = async () => {
    if (!draft || !customerEmail) return;
    setLoadingStep('sending');
    try {
      await api('/email-drafter/send', {
        method: 'POST',
        body: JSON.stringify({
          to: customerEmail,
          subject: "Update from Bankly Customer Support",
          body: draft
        })
      });
      setSendSuccess(true);
    } catch (error) {
      console.error("Sending failed:", error);
      alert("Failed to send email. Did you configure the .env correctly?");
    } finally {
      setLoadingStep(null);
    }
  };

  return (
    <section className="p-6 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-6">Ticket Resolution</h2>
      
      {/* Input Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-400 mb-1">Customer Email</label>
          <input 
            type="email"
            className="w-full p-2 border border-gray-700 rounded bg-gray-800 text-white"
            value={customerEmail}
            onChange={(e) => setCustomerEmail(e.target.value)}
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-400 mb-1">Customer Query</label>
          <textarea 
            className="w-full p-3 border border-gray-700 rounded bg-gray-800 text-white"
            rows="3"
            placeholder="e.g., The ATM swallowed my card!"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        
        <button 
          onClick={processTicket}
          disabled={loadingStep !== null}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded disabled:opacity-50 transition-colors"
        >
          {loadingStep === 'analyzing' ? '🧠 Classifying Intent...' : 
           loadingStep === 'drafting' ? '✍️ Generating Draft...' : 
           '🚀 Process Ticket'}
        </button>
      </div>

      {/* Results Section */}
      {(analysis || draft) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Left Column: Context Metadata */}
          <div className="col-span-1 bg-gray-900 border border-gray-800 rounded-lg p-5 h-fit">
            <h3 className="font-bold text-lg mb-4 text-gray-300">Ticket Context</h3>
            {analysis ? (
              <div className="space-y-3 text-sm">
                <p><strong>Intent:</strong> <br/><span className="text-blue-400 bg-blue-900/30 px-2 py-1 rounded inline-block mt-1">{analysis.intent}</span></p>
                <p><strong>Sentiment:</strong> <br/><span className={`px-2 py-1 rounded inline-block mt-1 ${analysis.sentiment === 'NEGATIVE' ? 'text-red-400 bg-red-900/30' : 'text-green-400 bg-green-900/30'}`}>{analysis.sentiment}</span></p>
                <p><strong>Confidence:</strong> <br/><span className="text-gray-400">{(analysis.confidence * 100).toFixed(1)}%</span></p>
              </div>
            ) : (
              <p className="text-gray-500 italic">Waiting for analysis...</p>
            )}
          </div>

          {/* Right Column: The Draft Editor */}
          <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg text-gray-300">Generated Email</h3>
              
              {/* The Edit Toggle Button */}
              {draft && loadingStep !== 'iterating' && (
                <button 
                  onClick={() => setIsEditing(!isEditing)}
                  className="text-sm px-3 py-1 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
                >
                  {isEditing ? '👀 Preview HTML' : '✏️ Edit Manually'}
                </button>
              )}
            </div>
            
            {loadingStep === 'iterating' ? (
              <div className="py-10 text-center text-gray-400 animate-pulse">Iterating draft...</div>
            ) : isEditing ? (
              /* Edit Mode: A textarea bound directly to the draft state */
              <textarea
                className="w-full p-4 bg-gray-950 rounded border border-gray-700 text-gray-300 min-h-[200px] font-mono text-sm mb-6 outline-none focus:border-blue-500"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
              />
            ) : (
              /* Preview Mode: The read-only parsed markdown */
              <div 
                className="prose prose-invert max-w-none mb-6 p-4 bg-gray-800 rounded border border-gray-700 min-h-[200px]"
                dangerouslySetInnerHTML={{ __html: marked.parse(draft || '') }} 
              />
            )}
            
            {/* Iteration Controls (Hidden while editing to avoid confusion) */}
            {!isEditing && (
              <div className="flex flex-wrap gap-3 pb-4 mb-4 border-b border-gray-700">
                 <button onClick={() => iterateDraft('shorter')} disabled={loadingStep !== null} className="px-3 py-1.5 text-sm bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50">
                    📏 Shorter
                 </button>
                 <button onClick={() => iterateDraft('empathetic')} disabled={loadingStep !== null} className="px-3 py-1.5 text-sm bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50">
                    🤝 Empathetic
                 </button>
                 <button onClick={() => iterateDraft('regenerate')} disabled={loadingStep !== null} className="px-3 py-1.5 text-sm bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50">
                    🔄 Regenerate
                 </button>
              </div>
            )}

            {/* Send Control */}
            <div className="flex items-center justify-between mt-4">
                {sendSuccess ? (
                    <span className="text-green-500 font-bold">✅ Email Sent Successfully!</span>
                ) : (
                    <span className="text-gray-500 text-sm">Review draft before sending</span>
                )}
                <button 
                  onClick={sendEmail}
                  disabled={loadingStep !== null || sendSuccess || isEditing}
                  title={isEditing ? "Preview draft before sending" : ""}
                  className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded disabled:opacity-50 transition-colors"
                >
                  {loadingStep === 'sending' ? 'Sending...' : '✉️ Send Email'}
                </button>
            </div>
          </div>
          
        </div>
      )}
    </section>
  )
}