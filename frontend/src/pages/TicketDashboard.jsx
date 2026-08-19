import { useState, useEffect } from 'react'
import { api } from '../lib/api.js'
import { marked } from 'marked'
import {
  RefreshCcw,
  ChevronDown,
  Sparkles,
  Brain,
  PenTool,
  Ruler,
  HeartHandshake,
  Mail,
  Eye,
  Pencil,
  MailCheck,
  Check
} from 'lucide-react'

export default function TicketDashboard() {
  // Queue State
  const [tickets, setTickets] = useState([])
  const [activeTicket, setActiveTicket] = useState(null)
  const [loadingTickets, setLoadingTickets] = useState(true)
  const [sortOrder, setSortOrder] = useState('oldest')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  // Workspace State
  const [analysis, setAnalysis] = useState(null)
  const [draft, setDraft] = useState('')
  const [loadingStep, setLoadingStep] = useState(null)
  const [sendSuccess, setSendSuccess] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // Fetch tickets on load
  const fetchTickets = async () => {
    try {
      const data = await api('/tickets/open');
      setTickets(data.tickets || []);
    } catch (error) {
      console.error("Failed to fetch tickets:", error);
    } finally {
      setLoadingTickets(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  // Sort tickets dynamically
  const sortedTickets = [...tickets].sort((a, b) => {
    if (sortOrder === 'oldest') return new Date(a.created_at) - new Date(b.created_at);
    return new Date(b.created_at) - new Date(a.created_at);
  });

  // Handle selecting a ticket from the queue
  const handleSelectTicket = async (ticket) => {
    // Clear out the previous ticket first
    setActiveTicket(ticket);
    setAnalysis(null);
    setDraft('');
    setIsEditing(false);
    setSendSuccess(false);

    try {
      setLoadingStep('loading'); 
      
      const data = await api(`/tickets/${ticket.ticket_id}/workspace`);
      
      // If the backend found existing data, populate the workspace
      if (data.analysis) setAnalysis(data.analysis);
      if (data.latest_draft) setDraft(data.latest_draft);
      
    } catch (error) {
      console.error("Failed to load workspace data", error);
    } finally {
      setLoadingStep(null);
    }
  };

  // Handle saving a generated draft to the database
  const saveDraftToDB = async (ticketId, text, currentAnalysis) => {
    try {
      await api('/tickets/save-draft', {
        method: 'POST',
        body: JSON.stringify({ 
          ticket_id: ticketId, 
          draft_text: text,
          intent: currentAnalysis?.intent,
          sentiment: currentAnalysis?.sentiment,
          confidence: currentAnalysis?.confidence
        })
      });
    } catch (error) {
      console.error("Failed to save draft to history:", error);
    }
  };

  // Process Ticket button
  const processTicket = async () => {
    if (!activeTicket) return;
    setAnalysis(null);
    setDraft('');
    setSendSuccess(false);
    setIsEditing(false);
    
    try {
      setLoadingStep('analyzing');
      const classData = await api('/intent-classifier/classify', {
        method: 'POST',
        body: JSON.stringify({ text: activeTicket.customer_query })
      });
      setAnalysis(classData);

      setLoadingStep('drafting');
      const draftData = await api('/email-drafter/draft', {
        method: 'POST',
        body: JSON.stringify({ 
            email: activeTicket.customer_email, 
            query: activeTicket.customer_query,
            intent: classData.intent,
            sentiment: classData.sentiment 
        })
      });

      setDraft(draftData.draft);
      await saveDraftToDB(activeTicket.ticket_id, draftData.draft, classData);

    } catch (error) {
      console.error("Pipeline failed:", error);
    } finally {
      setLoadingStep(null);
    }
  };

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
      await saveDraftToDB(activeTicket.ticket_id, data.new_draft, analysis);

    } catch (error) {
      console.error("Iteration failed:", error);
    } finally {
      setLoadingStep(null);
    }
  };

  const sendEmail = async () => {
    if (!draft || !activeTicket) return;
    setLoadingStep('sending');
    try {
      await api('/email-drafter/send', {
        method: 'POST',
        body: JSON.stringify({
          to: activeTicket.customer_email,
          subject: "Update from Bankly Customer Support",
          body: draft
        })
      });
      
      await api('/tickets/close', {
        method: 'POST',
        body: JSON.stringify({ ticket_id: activeTicket.ticket_id })
      });
      
      setSendSuccess(true);
      fetchTickets(); // Refresh the queue on the left
      
      // Setting a timeout so that the status messages can be seen
      setTimeout(() => {
        setActiveTicket(null);
        setAnalysis(null);
        setDraft('');
        setIsEditing(false);
      }, 2000);

    } catch (error) {
      console.error("Sending failed:", error);
    } finally {
      setLoadingStep(null);
    }
  };

  return (
    <section className="flex h-[calc(100vh-4rem)] max-w-7xl mx-auto">
      
      {/* Left Column: Ticket Queue */}
      <div className="w-96 border-r border-gray-800 p-4 overflow-y-auto flex flex-col">
        <div className="flex justify-between items-center mb-6 relative">
          <h2 className="text-xl font-bold">Open Tickets</h2>
          
          {/* Controls Group */}
          <div className="flex gap-2">
            {/* Refresh Button */}
            <button 
              onClick={fetchTickets}
              disabled={loadingTickets}
              title="Refresh Queue"
              className="px-3 py-1 text-sm bg-gray-800 border border-gray-700 rounded text-gray-300 hover:text-white hover:bg-gray-700 disabled:opacity-50"
            >
              <RefreshCcw size={20} strokeWidth={2}/>
            </button>

            {/* Sort Dropdown */}
            <div className="relative">
              <button 
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="inline-flex items-center justify-center gap-1 py-1 px-2 text-sm bg-gray-800 border border-gray-700 rounded text-gray-300 hover:text-white"
              >
                Sort <ChevronDown size={15} strokeWidth={2}/>
              </button>
              {isDropdownOpen && (
                <div className="absolute right-0 mt-1 w-32 bg-gray-800 border border-gray-700 rounded shadow-lg z-10">
                  <button 
                    onClick={() => { setSortOrder('oldest'); setIsDropdownOpen(false); }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-gray-700 text-gray-200"
                  >Oldest First</button>
                  <button 
                    onClick={() => { setSortOrder('newest'); setIsDropdownOpen(false); }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-gray-700 text-gray-200"
                  >Newest First</button>
                </div>
              )}
            </div>
          </div>
        </div>

        {loadingTickets ? (
          <p className="text-gray-500">Loading queue...</p>
        ) : sortedTickets.length === 0 ? (
          <p className="text-gray-500">No open tickets. Great job!</p>
        ) : (
          <div className="space-y-3 flex-1">
            {sortedTickets.map(ticket => (
              <div 
                key={ticket.ticket_id}
                onClick={() => handleSelectTicket(ticket)}
                className={`p-4 rounded-lg cursor-pointer border transition-colors ${activeTicket?.ticket_id === ticket.ticket_id ? 'bg-blue-900/20 border-blue-500' : 'bg-gray-900 border-gray-800 hover:border-gray-600'}`}
              >
                <div className="text-sm font-bold text-gray-300 mb-1">{ticket.customer_email}</div>
                <div className="text-sm text-gray-400 line-clamp-2">{ticket.customer_query}</div>
                <div className="text-xs text-gray-500 mt-2">
                  {new Date(ticket.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Column: Copilot Workspace */}
      <div className="flex-1 p-6 overflow-y-auto">
        {!activeTicket ? (
          <div className="flex h-full items-center justify-center text-gray-500">
            Select a ticket from the queue to open the workspace.
          </div>
        ) : (
          <div className="animate-in fade-in duration-300">
            <h2 className="text-2xl font-bold mb-6">Ticket Workspace</h2>
            
            {/* Active Ticket Context */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
               <h3 className="text-sm font-medium text-gray-400 mb-2">Customer Query</h3>
               <p className="text-lg text-gray-200 mb-4 bg-gray-950 p-4 rounded border border-gray-800">"{activeTicket.customer_query}"</p>
               
               {/* Only show the button if no data exists yet */}
               {!(analysis || draft) && (
                 <button 
                  onClick={processTicket}
                  disabled={loadingStep !== null}
                  className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded disabled:opacity-50 transition-colors"
                 >
                  {loadingStep === 'analyzing' ? (
                        <><Brain size={18} /> Classifying...</>
                    ) : loadingStep === 'drafting' ? (
                        <><PenTool size={18} /> Drafting...</>
                    ) : (
                        <><Sparkles size={18} /> Process Ticket</>
                    )}
                 </button>
               )}
            </div>

            {/* Results Grid */}
            {(analysis || draft) && (
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                
                {/* Metadata Column */}
                <div className="xl:col-span-1 bg-gray-900 border border-gray-800 rounded-lg p-5 h-fit">
                  <h3 className="font-bold mb-4 text-gray-300">AI Analysis</h3>
                  {analysis ? (
                    <div className="space-y-4 text-sm">
                      <div>
                         <span className="block text-gray-500 mb-1">Detected Intent</span>
                         <span className="text-blue-400 bg-blue-900/30 px-2 py-1 rounded inline-block">{analysis.intent}</span>
                      </div>
                      <div>
                         <span className="block text-gray-500 mb-1">Customer Sentiment</span>
                         <span className={`px-2 py-1 rounded inline-block ${analysis.sentiment === 'NEGATIVE' ? 'text-red-400 bg-red-900/30' : 'text-green-400 bg-green-900/30'}`}>{analysis.sentiment}</span>
                      </div>
                      <div>
                         <span className="block text-gray-500 mb-1">Model Confidence</span>
                         <span className="text-gray-300">{(analysis.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">Waiting for analysis...</p>
                  )}
                </div>

                {/* Editor Column */}
                <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-lg p-5 flex flex-col">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-bold text-gray-300">Email Draft</h3>
                    {draft && loadingStep !== 'iterating' && (
                      <button onClick={() => setIsEditing(!isEditing)} className="inline-flex items-center justify-center gap-2 text-sm px-3 py-1 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:text-white">
                        {isEditing ? (
                            <><Eye size={15} /> Preview</>
                            ) : (
                            <><Pencil size={15} /> Edit</>
                            )}
                      </button>
                    )}
                  </div>
                  
                  {loadingStep === 'iterating' ? (
                    <div className="flex-1 py-10 text-center text-gray-400 animate-pulse">Iterating draft...</div>
                  ) : isEditing ? (
                    <textarea
                      className="flex-1 w-full p-4 bg-gray-950 rounded border border-gray-700 text-gray-300 min-h-[250px] font-mono text-sm mb-4 outline-none"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                    />
                  ) : (
                    <div 
                      className="flex-1 prose prose-invert max-w-none mb-4 p-4 bg-gray-800 rounded border border-gray-700 overflow-y-auto"
                      dangerouslySetInnerHTML={{ __html: marked.parse(draft || '') }} 
                    />
                  )}
                  
                  {/* Iteration Controls */}
                  {!isEditing && draft && (
                    <div className="flex gap-2 pb-4 mb-4 border-b border-gray-700">
                       <button onClick={() => iterateDraft('shorter')} disabled={loadingStep !== null} className="px-3 py-1.5 text-xs bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50 inline-flex items-center justify-center gap-2 "><Ruler size={18}/> Shorter</button>
                       <button onClick={() => iterateDraft('empathetic')} disabled={loadingStep !== null} className="px-3 py-1.5 text-xs bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"><HeartHandshake size={18}/> Empathetic</button>
                       <button onClick={() => iterateDraft('regenerate')} disabled={loadingStep !== null} className="px-3 py-1.5 text-xs bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"><RefreshCcw size={18}/> Regenerate</button>
                    </div>
                  )}

                  {/* Send Action */}
                  <div className="flex items-center justify-between mt-auto pt-2">
                      {sendSuccess ? (
                          <span className="inline-flex items-center justify-center gap-2 text-green-500 font-bold"><Check size={15}/> Closed & Sent!</span>
                      ) : (
                          <span className="inline-flex items-center justify-center gap-2 text-gray-500 text-xs"> <MailCheck size={15}/>Ready to deliver</span>
                      )}
                      <button 
                        onClick={sendEmail}
                        disabled={loadingStep !== null || sendSuccess || isEditing}
                        className="inline-flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded disabled:opacity-50 transition-colors"
                      >
                        {loadingStep === 'sending' ? 'Sending...' : <><Mail size={18}/>Send Email & Close Ticket</>}
                      </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}