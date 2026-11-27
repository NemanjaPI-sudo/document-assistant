
import { useState, useEffect, useRef } from 'react'

import ChatMessage from './ChatMessage'

function ChatPanel({
  messages,
  onAskQuestion,
  asking,
  selectedDocumentCount
}) {
  const [question, setQuestion] = useState('')
  const messagesRef = useRef(null)

  // Scroll to the latest message when the chat changes.
  useEffect(() => {
    const container = messagesRef.current

    if (container) {
      container.scrollTop = container.scrollHeight
    }
  }, [messages, asking])

  // Submit the question to the parent component.
  async function handleSubmit(event) {
    event.preventDefault()

    const text = question.trim()

    if (!text || asking || selectedDocumentCount === 0) {
      return
    }

    setQuestion('')

    await onAskQuestion(text)
  }

  return (
    <section className="panel chat-panel">
      <h2>Chat with your documents</h2>

      <div className="chat-messages" ref={messagesRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            <h3>Ask your first question</h3>

            <p>
              Get answers with verified citations
              from your uploaded documents.
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            message={message}
          />
        ))}

        {asking && (
          <div className="chat-loading" role="status">
            Searching documents and generating an answer...
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <p className="chat-hint">
          {selectedDocumentCount === 0
            ? 'Select at least one document to start.'
            : `Searching ${selectedDocumentCount} selected document(s).`}
        </p>

        <div className="chat-input-row">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question..."
            aria-label="Question"
            maxLength={2000}
            rows={2}
            disabled={asking || selectedDocumentCount === 0}
          />

          <button
            className="button"
            type="submit"
            disabled={
              asking ||
              !question.trim() ||
              selectedDocumentCount === 0
            }
          >
            {asking ? 'Please wait...' : 'Send'}
          </button>
        </div>
      </form>
    </section>
  )
}

export default ChatPanel
