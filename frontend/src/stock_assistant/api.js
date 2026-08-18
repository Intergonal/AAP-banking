import { api } from '../lib/api.js'

export function sendChat(message, history) {
  return api('/stock-assistant/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })
}

export function runPrediction(ticker) {
  return api('/stock-assistant/predict', {
    method: 'POST',
    body: JSON.stringify({ ticker }),
  })
}

export function getQuote(symbol) {
  return api(`/stock-assistant/quote/${encodeURIComponent(symbol)}`)
}

export function getAccount() {
  return api('/stock-assistant/account')
}

export function placeTrade(payload) {
  return api('/stock-assistant/trade', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function resetAccount() {
  return api('/stock-assistant/account/reset', { method: 'POST' })
}

export function sendTransfer(to_email, amount) {
  return api('/stock-assistant/transfer', {
    method: 'POST',
    body: JSON.stringify({ to_email, amount }),
  })
}

export function getTransfers() {
  return api('/stock-assistant/transfers')
}

export function getRecipient(email) {
  return api(`/stock-assistant/recipient?email=${encodeURIComponent(email)}`)
}

export function getPriceSeries(symbol, period) {
  return api(
    `/stock-assistant/prices/${encodeURIComponent(symbol)}?period=${encodeURIComponent(period)}`
  )
}

export function searchSymbols(query) {
  return api(`/stock-assistant/search?q=${encodeURIComponent(query)}`)
}

export function getKb() {
  return api('/stock-assistant/kb')
}

export function addGlossaryEntry(entry) {
  return api('/stock-assistant/kb/glossary', {
    method: 'POST',
    body: JSON.stringify(entry),
  })
}

export function updateGlossaryEntry(entry) {
  return api('/stock-assistant/kb/glossary', {
    method: 'PUT',
    body: JSON.stringify(entry),
  })
}

export function deleteGlossaryEntry(term) {
  return api(
    `/stock-assistant/kb/glossary?term=${encodeURIComponent(term)}`,
    { method: 'DELETE' }
  )
}

export function addCommentaryEntry(entry) {
  return api('/stock-assistant/kb/commentary', {
    method: 'POST',
    body: JSON.stringify(entry),
  })
}

export function updateCommentaryEntry(entry) {
  return api('/stock-assistant/kb/commentary', {
    method: 'PUT',
    body: JSON.stringify(entry),
  })
}

export function deleteCommentaryEntry(topic) {
  return api(
    `/stock-assistant/kb/commentary?topic=${encodeURIComponent(topic)}`,
    { method: 'DELETE' }
  )
}

export function addMdSection(entry) {
  return api('/stock-assistant/kb/md', {
    method: 'POST',
    body: JSON.stringify(entry),
  })
}

export function updateMdSection(entry) {
  return api('/stock-assistant/kb/md', {
    method: 'PUT',
    body: JSON.stringify(entry),
  })
}

export function deleteMdSection(file, heading) {
  return api(
    `/stock-assistant/kb/md?file=${encodeURIComponent(file)}&heading=${encodeURIComponent(heading)}`,
    { method: 'DELETE' }
  )
}