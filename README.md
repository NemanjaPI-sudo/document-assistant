Document Assistant

A web application for uploading PDF and DOCX documents and asking questions about their content. Answers are based on the selected documents and include citations with the document name, page number and original text.

Technologies

- Frontend: React, Vite, JavaScript and CSS
- Backend: Python and FastAPI
- Database: Supabase PostgreSQL with pgvector
- File storage: Supabase Storage
- AI: Google Gemini API for embeddings and answer generation
- Document processing: PyMuPDF and LibreOffice

Requirements

Development environment:

- Python 3.12.10
- Node.js 26.13.1
- npm 12.2.2
- LibreOffice
- Supabase project
- Google Gemini API key

An internet connection is required for Supabase and Gemini cloud services.
Installation

Clone the repository (access to the repository is required):

git clone https://github.com/NemanjaPI-sudo/document-assistant.git

cd document-assistant

Supabase setup

1. Create a new Supabase project.
2. Open the SQL Editor in the Supabase dashboard.
3. Execute supabase/schema.sql to initialize the new database.
4. Copy the project URL and secret API key.

The SQL script creates the database tables, enables pgvector, configures vector search and creates a private storage bucket named documents. The bucket supports PDF and DOCX files up to 20 MB.

If using an already configured project, do not run the initialization script again.
LibreOffice setup
Install LibreOffice for DOCX-to-PDF conversion. Set the executable path in the backend .env file. The example below uses the Windows installation path; adjust it for your operating system and installation directory.
Backend setup
cd backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
The activation command is for Windows Git Bash. On Linux or macOS, use source .venv/bin/activate instead.
Environment configuration
From the backend directory, create a local .env file using the provided template:
cp .env.example .env
Configure the following variables in .env:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-supabase-secret-key
LIBREOFFICE_PATH="C:/Program Files/LibreOffice/program/soffice.com"
GEMINI_API_KEY=your-gemini-api-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_LLM_MODEL=gemini-3.1-flash-lite
Replace the placeholder credentials with your own and adjust the LibreOffice path if necessary. Use a Gemini API key with access to the configured models. Keep the secret keys on the backend and do not commit .env to Git.
Frontend setup
From the backend directory:
cd ../frontend
npm install
Running the application
Open two terminals from the project root.

Backend (Windows Git Bash):
cd backend
source .venv/Scripts/activate
python -m uvicorn main:app --reload
On Linux or macOS, activate the virtual environment using source .venv/bin/activate instead.

Frontend:
cd frontend
npm run dev
Open http://localhost:5173 in your browser. The backend runs at http://localhost:8000 and API documentation is available at http://localhost:8000/docs.

Upload documents, wait until they are ready, select the documents and enter a question.
How it works

1. Uploaded documents are stored in Supabase Storage. DOCX files are converted to PDF using LibreOffice to provide consistent page references within the application.
2. Text is extracted page by page and split into smaller overlapping chunks.
3. Gemini generates embeddings for the chunks, which are stored in PostgreSQL using pgvector.
4. When a user asks a question, the backend generates a query embedding and retrieves up to eight relevant chunks using cosine similarity.
5. Gemini generates a structured answer using the retrieved text. The backend checks each citation against its original chunk and attaches trusted document and page metadata.
6. The validated answer is displayed with links to the cited pages. If there is insufficient information or citation validation fails, the application returns an insufficient-information response.
   The retrieval and citation validation logic is implemented in Python without a managed RAG or file search service.
   Known limitations

- Scanned documents without extractable text are not supported through OCR.
- DOCX page numbers refer to the converted PDF and may differ from Microsoft Word pagination.
- Strict citation validation can reject otherwise correct answers. Exact quote matching does not guarantee factual correctness.
- The application is intended for local, single-user testing and does not include user authentication.
