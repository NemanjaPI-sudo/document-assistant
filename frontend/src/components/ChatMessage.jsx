
import Citation from './Citation'

function ChatMessage({ message }) {
  return (
    <div className={`chat-message ${message.role}`}>
      <div className="message-author">
        {message.role === 'user'
          ? 'You'
          : 'Document Assistant'}
      </div>

      {message.role === 'user' ? (
        <p>{message.text}</p>
      ) : message.status === 'answered' ? (
        <div className="answer-claims">
          {message.claims.map((claim, claimIndex) => (
            <div className="answer-claim" key={claimIndex}>
              <p className="claim-text">
                {claim.text}
              </p>

              {/* Display citations supporting this claim. */}
              <div className="claim-citations">
                {claim.citations.map((citation, citationIndex) => (
                  <Citation
                    key={`${citation.chunk_id}-${citationIndex}`}
                    citation={citation}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className={`message-status ${message.status}`}>
          {message.text}
        </p>
      )}
    </div>
  )
}

export default ChatMessage
