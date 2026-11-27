
import { useState } from 'react'

function DocumentPanel({
  documents,
  onLoadDocuments,
  onUploadDocuments,
  uploading,
  selectedDocumentIds,
  onToggleDocument,
  onSelectAll,
  onClearSelection
}) {
  const [selectedFiles, setSelectedFiles] = useState([])

  // Store the files selected by the user.
  function handleFileChange(event) {
    setSelectedFiles(Array.from(event.target.files))
  }

  // Upload the selected files.
  async function handleUpload(event) {
    event.preventDefault()

    if (selectedFiles.length === 0) {
      return
    }

    const form = event.currentTarget

    const success = await onUploadDocuments(selectedFiles)

    if (success) {
      setSelectedFiles([])
      form.reset()
    }
  }

  return (
    <aside className="panel">
      <h2>Documents ({documents.length})</h2>

      <form className="upload-form" onSubmit={handleUpload}>
        <label htmlFor="document-files">
          Select PDF or DOCX files
        </label>

        <input
          id="document-files"
          type="file"
          accept=".pdf,.docx"
          multiple
          onChange={handleFileChange}
          disabled={uploading}
        />

        <p className="upload-hint">
          Maximum 10 files, 20 MB per file.
        </p>

        <button
          className="button full-width"
          type="submit"
          disabled={uploading || selectedFiles.length === 0}
        >
          {uploading
            ? 'Uploading and indexing...'
            : 'Upload documents'}
        </button>
      </form>

      <button
        className="button secondary-button full-width"
        onClick={onLoadDocuments}
        disabled={uploading}
      >
        Refresh documents
      </button>

      {/* Document selection controls. */}
      <div className="document-selection">
        <p>
          Selected documents: {selectedDocumentIds.length}
        </p>

        <div className="selection-actions">
          <button
            className="text-button"
            onClick={onSelectAll}
          >
            Select all
          </button>

          <button
            className="text-button"
            onClick={onClearSelection}
          >
            Clear selection
          </button>
        </div>
      </div>

      {/* Display uploaded documents and their current status. */}
      <div className="document-list">
        {documents.length === 0 && (
          <p className="empty-documents">
            No documents available.
          </p>
        )}

        {documents.map((document) => (
          <div className="document-card" key={document.id}>
            <label className="document-title">
              <input
                type="checkbox"
                checked={selectedDocumentIds.includes(document.id)}
                onChange={() => onToggleDocument(document.id)}
                disabled={document.status !== 'ready'}
              />

              <span>{document.filename}</span>
            </label>

            <p>{document.page_count ?? 'Unknown'} pages</p>

            <span className={`document-status ${document.status}`}>
              {document.status}
            </span>
          </div>
        ))}
      </div>
    </aside>
  )
}

export default DocumentPanel
