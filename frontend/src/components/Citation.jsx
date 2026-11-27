
function Citation({ citation }) {
  // Build a link to the original document page.
  const previewUrl =
    `/api/documents/${citation.document_id}/preview` +
    `#page=${citation.page_number}`

  return (
    <div className="citation-card">
      <div className="citation-label">
        Verified citation
      </div>

      {/* Display the original quote returned by the backend. */}
      <blockquote className="citation-quote">
        {citation.quote}
      </blockquote>

      {/* Display trusted document metadata. */}
      <div className="citation-source">
        <a
          className="citation-filename citation-link"
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="Open the original document page"
        >
          {citation.filename} ↗
        </a>

        <span className="citation-page">
          Page {citation.page_number}
        </span>
      </div>
    </div>
  )
}

export default Citation
