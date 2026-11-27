import { useState } from 'react'

function App() {
  const [status, setStatus] = useState('Not checked')

  async function checkBackend() {
    try {
      const response = await fetch('/api/health')

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const data = await response.json()
      setStatus(data.status)
    } catch {
      setStatus('Connection failed')
    }
  }

  return (
    <div>
      <h1>Document Assistant</h1>

      <p>Backend status: {status}</p>

      <button onClick={checkBackend}>
        Check backend
      </button>
    </div>
  )
}

export default App