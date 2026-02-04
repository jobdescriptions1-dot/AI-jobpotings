# Government Procurement Automation System

A unified automation system for monitoring and processing government procurement job postings from multiple portals (HHSC, VMS, Odoo) with integrated RAG-powered chatbot capabilities.

## 🚀 Features

### Core Automation
- **Multi-Portal Monitoring**: Automated monitoring of HHSC and VMS portals for new job postings
- **Email Processing**: Automatic Gmail integration for processing job-related emails
- **Dual Table Processing**: Advanced job tracking using Excel-based dual table system
- **Continuous Monitoring**: Background monitoring with 15-second intervals for new emails
- **Daily Email Reports**: Automated daily email reports to configured recipients

### RAG Chatbot System
- **Intelligent Q&A**: Ask natural language questions about job postings
- **Vector Search**: ChromaDB-powered semantic search across job documents
- **LLM Integration**: Groq/Llama-3 powered responses with rich formatting
- **Auto-Ingestion**: Automatic processing of new documents into the knowledge base
- **Odoo Integration**: Direct integration with Odoo job posting data

### Frontend Dashboard
- **React-based UI**: Modern Vite + React frontend
- **Real-time Statistics**: Live processing statistics and system status
- **Job Management**: Browse, filter, and manage job postings
- **Chatbot Interface**: Interactive chatbot for querying job information

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- Google Gmail API credentials
- ChromeDriver (for web scraping)
- Odoo API access (optional)

## 🔧 Installation

### Backend Setup

1. **Clone the repository**
   ```bash
   cd backend3
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Add your environment variables here
   GROQ_API_KEY=your_groq_api_key
   ODOO_URL=your_odoo_url
   ODOO_DB=your_odoo_database
   ODOO_USERNAME=your_username
   ODOO_PASSWORD=your_password
   ```

4. **Set up Gmail API credentials**
   - Place `credentials1.json` and `client.json` in the root directory
   - Run the application once to generate `token.json` and `token1.json`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## 🚀 Running the Application

### Start Backend Server

```bash
python app.py
```

The backend server will start on `http://localhost:5000` and automatically:
- Initialize the RAG chatbot system
- Start continuous monitoring after 5 seconds
- Begin processing emails from configured portals

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173` (default Vite port)

## 📡 API Endpoints

### System Endpoints
- `GET /` - System information and available endpoints
- `GET /api/status` - Get system status
- `POST /api/start` - Run all portals once
- `POST /api/monitor/start` - Start continuous monitoring
- `POST /api/monitor/stop` - Stop monitoring
- `POST /api/email/send` - Send due list email
- `GET /api/stats` - Get processing statistics
- `POST /api/run/portal/<name>` - Run specific portal

### RAG Chatbot Endpoints
- `GET /rag/stats` - RAG system statistics
- `POST /rag/query` - Ask questions about jobs
- `GET /rag/sample-queries` - Example questions
- `GET /rag/odoo-postings` - Odoo posting statistics

## 🏗️ Project Structure

```
backend3/
├── api/                          # API route blueprints
│   ├── unified_routes.py         # Main unified API routes
│   ├── odoo_routes.py           # Odoo-specific routes
│   └── ...
├── services/                     # Core business logic
│   ├── unified/                 # Unified monitoring services
│   ├── dir/                     # HHSC portal services
│   ├── vms/                     # VMS portal services
│   ├── odoo/                    # Odoo integration services
│   ├── dual_table/              # Dual table processing
│   └── email/                   # Email services
├── rag/                         # RAG chatbot system
│   ├── chatbot_api.py          # Chatbot API endpoints
│   ├── chroma_manager.py       # ChromaDB vector store
│   ├── llm_generator.py        # LLM response generation
│   ├── query_engine.py         # Query processing
│   └── ingestion_service.py    # Document ingestion
├── utils/                       # Utility modules
│   ├── config.py               # Configuration management
│   ├── logger.py               # Logging utilities
│   └── ...
├── frontend/                    # React frontend
│   ├── src/                    # Source files
│   ├── public/                 # Static assets
│   └── package.json            # Frontend dependencies
├── entry_points/               # Entry point scripts
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔐 Security Notes

The following files contain sensitive information and are gitignored:
- `.env` - Environment variables
- `credentials*.json` - Google API credentials
- `client.json` - OAuth client configuration
- `token*.json` - OAuth tokens
- `sqlite_db/` - Database files
- `*_documents/` - Downloaded documents
- `chromadb_data/` - Vector database

**Never commit these files to version control!**

## 📊 Data Storage

- **SQLite Database**: Job tracking and metadata (`sqlite_db/`)
- **ChromaDB**: Vector embeddings for RAG system (`chromadb_data/`)
- **Excel Files**: Dual table job tracking (`job_tracker_report.xlsx`)
- **JSON Files**: Email and file processing tracking

## 🤖 RAG System

The RAG (Retrieval-Augmented Generation) system provides intelligent question-answering capabilities:

1. **Document Ingestion**: Automatically processes PDFs, DOCX, and TXT files
2. **Vector Storage**: Uses ChromaDB with sentence-transformers for embeddings
3. **Semantic Search**: Finds relevant job information based on natural language queries
4. **LLM Generation**: Generates formatted responses using Groq/Llama-3

### Example Queries
- "What jobs are available in Austin?"
- "Show me all software developer positions"
- "What are the requirements for job ID 12345?"

## 🛠️ Development

### Running Tests
```bash
python test_chatbot.py
python test_rag_filters.py
```

### Building Frontend for Production
```bash
cd frontend
npm run build
```

## 📝 Monitoring Configuration

The system monitors:
- **HHSC Portal**: Every 15 seconds for new emails
- **VMS Portal**: Every 15 seconds for new emails
- **Daily Email**: Sent to `jobdescriptions1@gmail.com`
- **Processing**: Dual table system using Excel tracking

## 🔄 Automation Flow

1. System starts and initializes RAG chatbot
2. After 5 seconds, continuous monitoring begins
3. Every 15 seconds, checks for new emails in both portals
4. Processes new emails and extracts job information
5. Updates dual table tracking system
6. Ingests documents into RAG system
7. Sends daily email reports

## 📞 Support

For issues or questions, check the logs in the console output. The system provides detailed logging for all operations.

## 📄 License

[Add your license information here]

## 👥 Contributors

[Add contributor information here]
