
// Send a request to the backend and parse the JSON response.
async function request(url, options = {}) {
  let response

  // Handle network and connection errors.
  try {
    response = await fetch(url, options)
  } catch {
    throw new Error('Unable to connect to the backend.')
  }

  let data

  // Handle responses that do not contain valid JSON.
  try {
    data = await response.json()
  } catch {
    throw new Error(
      `Invalid backend response (${response.status}).`
    )
  }

  // Handle unsuccessful HTTP responses.
  if (!response.ok) {
    let message = `Request failed (${response.status})`

    if (typeof data.detail === 'string') {
      message = data.detail
    } else if (Array.isArray(data.detail)) {
      message = data.detail
        .map((item) => item.msg)
        .join(', ')
    }

    throw new Error(message)
  }

  return data
}


// Check if the backend server is available.
export async function checkHealth() {
  return request('/api/health')
}


// Retrieve all uploaded documents.
export async function getDocuments() {
  return request('/api/documents')
}


// Upload one or more PDF or DOCX files.
export async function uploadDocuments(files) {
  const formData = new FormData()

  for (const file of files) {
    formData.append('files', file)
  }

  return request('/api/documents', {
    method: 'POST',
    body: formData
  })
}


// Ask a question using the selected documents.
export async function askQuestion(question, documentIds = null) {
  return request('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      question: question,
      document_ids: documentIds
    })
  })
}
