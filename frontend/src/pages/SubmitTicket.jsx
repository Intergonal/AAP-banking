import { useState } from 'react'
import { api } from '../lib/api.js'
import {
    Mail,
    CircleCheckBig,
    CircleX
} from 'lucide-react'

export default function SubmitTicket() {
  const [email, setEmail] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState({ loading: false, success: false, error: null })

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !query.trim()) return;

    setStatus({ loading: true, success: false, error: null });

    try {
      await api('/tickets/submit', {
        method: 'POST',
        body: JSON.stringify({ email, query })
      });
      setStatus({ loading: false, success: true, error: null });
      setQuery(''); // Clear the form on success
    } catch (error) {
      console.error("Submission failed:", error);
      setStatus({ loading: false, success: false, error: "Failed to submit ticket. Ensure your email is registered." });
    }
  };

  return (
    <section className="p-6 max-w-xl mx-auto mt-10">
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
        <h2 className="text-2xl font-bold mb-2">Contact Support</h2>
        <p className="text-gray-400 mb-6">Describe your issue below and our team will get back to you.</p>

        {status.success && (
          <div className="inline-flex items-center justify-center gap-2 mb-6 p-4 bg-green-900/50 border border-green-500 text-green-400 rounded">
            <CircleCheckBig/>Ticket submitted successfully! We will email you soon.
          </div>
        )}

        {status.error && (
          <div className="inline-flex items-center justify-center gap-2 mb-6 p-4 bg-red-900/50 border border-red-500 text-red-400 rounded">
            <CircleX/>{status.error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Account Email</label>
            <input 
              type="email"
              required
              className="w-full p-3 border border-gray-700 rounded bg-gray-800 text-white focus:border-blue-500 outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">How can we help?</label>
            <textarea 
              required
              className="w-full p-3 border border-gray-700 rounded bg-gray-800 text-white focus:border-blue-500 outline-none"
              rows="5"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Please provide details about your issue..."
            />
          </div>
          <button 
            type="submit"
            disabled={status.loading}
            className="inline-flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded disabled:opacity-50 transition-colors"
          >
            {status.loading ? 'Submitting...' : <><Mail/> Send Ticket</>}
          </button>
        </form>
      </div>
    </section>
  )
}