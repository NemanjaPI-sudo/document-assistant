
import { useState } from 'react'

function App() {
  // Store the current backend connection status.
  const [status, setStatus] = useState('Not checked')

  // Check if the backend server is available.
  async function checkBackend() {
    try {
      // Send a request to the backend health endpoint.
      const response = await fetch('/api/health')

      // Handle unsuccessful HTTP responses.
      if (!response.ok) {
        throw new Error('Request failed')
      }

      // Update the state with the status returned by the backend.
      const data = await response.json()
      setStatus(data.status)
    } catch {
      // Display an error if the request or connection fails.
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
