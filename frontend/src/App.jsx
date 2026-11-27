
import { useState, useEffect } from 'react'

import {
  checkHealth,
  getDocuments,
  uploadDocuments,
  askQuestion
} from './api'

import DocumentPanel from './components/DocumentPanel'
import ChatPanel from './components/ChatPanel'

import './App.css'

function App() {
  const [status, setStatus] = useState('Connecting...')
  const [documents, setDocuments] = useState([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState([])
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([])
  const [messages, setMessages] = useState([])
  const [asking, setAsking] = useState(false)

  // Load backend status and documents when the application starts.
  useEffect(() => {
    let cancelled = false

    async function initializeApp() {
      try {
        const health = await checkHealth()

        if (!cancelled) {
          setStatus(health.status)
        }
      } catch {
        if (!cancelled) {
          setStatus('Connection failed')
        }
      }

      try {
        const data = await getDocuments()

        if (!cancelled) {
          setDocuments(data.documents)
        }
      } catch (error) {
        if (!cancelled) {
          setError(error.message)
        }
      }
    }

    initializeApp()

    return () => {
      cancelled = true
    }
  }, [])

  // Retrieve documents from the backend.
  async function loadDocuments() {
    try {
      setError('')

      const data = await getDocuments()
      setDocuments(data.documents)
      setStatus('ok')

      // Remove selections that are no longer available.
      const readyIds = data.documents
        .filter((document) => document.status === 'ready')
        .map((document) => document.id)

      setSelectedDocumentIds((previousIds) =>
        previousIds.filter((id) => readyIds.includes(id))
      )
    } catch (error) {
      setError(error.message)

      // Check whether the backend is still available.
      try {
        const health = await checkHealth()
        setStatus(health.status)
      } catch {
        setStatus('Connection failed')
      }
    }
  }

  // Toggle the selection of an individual document.
  function toggleDocument(documentId) {
    setSelectedDocumentIds((previousIds) => {
      if (previousIds.includes(documentId)) {
        return previousIds.filter((id) => id !== documentId)
      }

      return [...previousIds, documentId]
    })
  }

  // Select all documents that are ready for searching.
  function selectAllDocuments() {
    const readyIds = documents
      .filter((document) => document.status === 'ready')
      .map((document) => document.id)

    setSelectedDocumentIds(readyIds)
  }

  // Clear the current document selection.
  function clearDocumentSelection() {
    setSelectedDocumentIds([])
  }

  // Validate and upload the selected documents.
  async function handleUploadDocuments(files) {
    setError('')
    setUploadResults([])

    if (files.length === 0) {
      setError('Select at least one file.')
      return false
    }

    if (files.length > 10) {
      setError('Maximum 10 files per upload.')
      return false
    }

    for (const file of files) {
      const filename = file.name.toLowerCase()

      if (
        !filename.endsWith('.pdf') &&
        !filename.endsWith('.docx')
      ) {
        setError(`Unsupported file type: ${file.name}`)
        return false
      }

      if (file.size === 0) {
        setError(`Empty file: ${file.name}`)
        return false
      }

      if (file.size > 20 * 1024 * 1024) {
        setError(`File exceeds 20 MB: ${file.name}`)
        return false
      }
    }

    setUploading(true)

    try {
      // Upload and index documents through the backend.
      const data = await uploadDocuments(files)

      setUploadResults(data.documents)

      // Refresh the document list after processing.
      await loadDocuments()

      return true
    } catch (error) {
      setError(error.message)
      return false
    } finally {
      setUploading(false)
    }
  }

  // Send a question to the backend and store the response.
  async function handleAskQuestion(question) {
    if (!question.trim() || asking) {
      return
    }

    if (selectedDocumentIds.length === 0) {
      setError('Select at least one document.')
      return
    }

    setError('')
    setAsking(true)

    // Add the user question to the chat history.
    setMessages((previousMessages) => [
      ...previousMessages,
      {
        role: 'user',
        text: question
      }
    ])

    try {
      const result = await askQuestion(
        question,
        selectedDocumentIds
      )

      setStatus('ok')

      if (result.status === 'answered') {
        // Preserve claims and citations returned by the backend.
        setMessages((previousMessages) => [
          ...previousMessages,
          {
            role: 'assistant',
            status: 'answered',
            claims: result.claims
          }
        ])
      } else {
        setMessages((previousMessages) => [
          ...previousMessages,
          {
            role: 'assistant',
            status: 'insufficient_information',
            text: 'There is not enough information in the selected documents to answer this question.'
          }
        ])
      }
    } catch (error) {
      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: 'assistant',
          status: 'error',
          text: error.message
        }
      ])
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="app">

      {/* Application header and connection status. */}
      <header className="app-header">
        <h1>Document Assistant</h1>

        <div className="connection-status" role="status">
          <span
            className={`status-dot ${
              status === 'ok' ? 'connected' : 'disconnected'
            }`}
            aria-hidden="true"
          />

          <span>
            {status === 'ok' ? 'Connected' : status}
          </span>
        </div>
      </header>

      {/* Display application errors. */}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* Display document upload results. */}
      {uploadResults.length > 0 && (
        <div className="upload-results" aria-live="polite">
          <h3>Upload results</h3>

          {uploadResults.map((result, index) => (
            <div
              className={`upload-result ${result.status}`}
              key={`${result.filename}-${index}`}
            >
              <strong>{result.filename}</strong>

              <span>{result.status}</span>

              {result.error && (
                <p>{result.error}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Main application layout. */}
      <main className="app-layout">
        <DocumentPanel
          documents={documents}
          onLoadDocuments={loadDocuments}
          onUploadDocuments={handleUploadDocuments}
          uploading={uploading}
          selectedDocumentIds={selectedDocumentIds}
          onToggleDocument={toggleDocument}
          onSelectAll={selectAllDocuments}
          onClearSelection={clearDocumentSelection}
        />

        <ChatPanel
          messages={messages}
          onAskQuestion={handleAskQuestion}
          asking={asking}
          selectedDocumentCount={selectedDocumentIds.length}
        />
      </main>
    </div>
  )
}

export default App
