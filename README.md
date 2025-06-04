# George AI Hotel Receptionist 🏨

An intelligent AI-powered hotel booking and customer service system built in Python with Streamlit and LangChain.

**📚 Academic Project:** This system was developed as the final project for an AI course, serving as a comprehensive study case for building conversational AI applications in the hospitality industry.

George is an AI hotel receptionist chatbot that handles guest inquiries, room bookings, and provides personalized recommendations. The system features an **intelligent AI router** that analyzes user queries and directs them to specialized tools for optimal responses.

### AI Router System
The core feature is a **LLM-powered router** that classifies user intent and routes queries to the most appropriate tool:

- **🔍 Vector Tool** - Semantic search through hotel knowledge base for amenities, policies, and services
- **🗄️ SQL Tool** - Natural language to SQL conversion for room availability, pricing, and booking data
- **📅 Booking Tool** - Interactive form activation for room reservations
- **💬 Chat Tool** - General conversation handler for greetings and non-hotel topics
- **🎯 Follow-up Tool** - Post-booking engagement with activity recommendations

## Features

- **🧠 Intelligent Query Routing** - AI-powered system routes questions to appropriate tools
- **📅 Real-time Booking System** - Complete room booking with availability checking
- **🔍 Smart Information Retrieval** - Vector search (Pinecone) and SQL queries (Railway) for hotel information
- **📧 Email Confirmations** - Automated booking confirmations with professional templates
- **💬 Contextual Conversations** - Memory-enabled chat for personalized interactions
- **🎯 Post-booking Follow-up** - Automatic activity recommendations after booking
- **🛠️ Developer Tools** - Built-in SQL panel and logging for debugging, LangSmith tracing

## Architecture

```
User Query → AI Router (LLM) → Tool Selection → Specialized Processing → Response
                   ↓
     [vector_tool, sql_tool, booking_tool, chat_tool, followup_tool]
```

**System Components:**
- **Router Intelligence:** GPT-3.5-turbo for intent classification with conversation memory
- **Vector Storage:** Hotel knowledge base stored in Pinecone for semantic search
- **Database:** Railway-hosted MySQL for dynamic booking data storage and retrieval
- **Monitoring:** LangSmith tracing for all LLM calls and system performance

**📊 Full Architecture Diagram:** [View Interactive Diagram](https://bejewelled-nougat-9ce61a.netlify.app)

### Core Components

- **`main.py`** - Application entry point and query routing
- **`tools/`** - Specialized AI tools for different functions
- **`booking/`** - Booking form and email confirmation system
- **`utils/config.py`** - Configuration management and LLM setup
- **`chat_ui.py`** - User interface components
- **`logger.py`** - Centralized logging system

## Project Structure

```
George/
├── 📁 .devcontainer/         # Development container configuration
├── 📁 .venv/                 # Virtual environment
├── 📁 assets/                # Static assets (images, etc.)
├── 📁 booking/               # Booking system
│   ├── __init__.py
│   ├── calendar.py           # Booking form interface
│   └── email.py              # Email confirmation system
├── 📁 Debuggers/             # Debugging utilities
├── 📁 docs/                  # Documentation
│   └── index.html
├── 📁 Ingestion/             # Data ingestion scripts
│   ├── ingestion.py          # Main ingestion logic
│   ├── ingestion_firecrawl.py # Web scraping with Firecrawl
│   └── reset_firecrawl_ingestion.py
├── 📁 static/                # Static content
│   └── hotel_facts.txt       # Hotel information database
├── 📁 tools/                 # AI tool modules
│   ├── __init__.py
│   ├── booking_tool.py       # Booking form activation
│   ├── chat_tool.py          # General conversation handler
│   ├── followup_tool.py      # Post-booking engagement
│   ├── sql_tool.py           # Database query processor
│   └── vector_tool.py        # Semantic search engine
├── 📁 utils/                 # Utility modules
│   ├── __init__.py
│   └── config.py             # Configuration management
├── 📄 .env                   # Environment variables
├── 📄 .gitattributes         # Git configuration
├── 📄 .gitignore             # Git ignore rules
├── 📄 chat_ui.py             # Chat interface components
├── 📄 hotel_descriptions.txt # Additional hotel content
├── 📄 logger.py              # Logging system
├── 📄 main.py                # Main application entry point
├── 📄 Pipfile                # Pipenv configuration
├── 📄 Pipfile.lock           # Pipenv lock file
├── 📄 requirements.txt       # Python dependencies
├── 📄 timestamping_files.py  # File management utility
└── 📄 updates                # Update notes
```

## Quick Start

**Zero-setup deployment - just connect and configure:**

1. **Fork/Clone Repository**
   ```bash
   git clone <repository-url>
   ```

2. **Deploy to Streamlit Cloud**
   - Sign up at [Streamlit.io](https://streamlit.io) and connect your GitHub account
   - Connect your repository to Streamlit Cloud
   - Configure secrets in Streamlit Cloud dashboard (see template below)
   - Deploy - dependencies auto-install from `requirements.txt`

3. **Configure Secrets**
   Add these in Streamlit Cloud's secrets management:
   ```toml
   # SQL DATABASE - INSERT ONLY (FOR BOOKING FORM)
   DB_HOST_FORM = "your_db_host"
   DB_PORT_FORM = "your_db_port"
   DB_USERNAME_FORM = "your_form_user"
   DB_PASSWORD_FORM = "your_form_password"
   DB_DATABASE_FORM = "your_database"
   
   # SQL DATABASE - READ ONLY (FOR QUERIES)
   DB_HOST_READ_ONLY = "your_db_host"
   DB_PORT_READ_ONLY = "your_db_port"
   DB_USERNAME_READ_ONLY = "your_readonly_user"
   DB_PASSWORD_READ_ONLY = "your_readonly_password"
   DB_DATABASE_READ_ONLY = "your_database"
   
   # SQL DATABASE - FULL ACCESS (FOR DEVELOPMENT)
   DB_HOST = "your_db_host"
   DB_PORT = "your_db_port"
   DB_USERNAME = "your_admin_user"
   DB_PASSWORD = "your_admin_password"
   DB_DATABASE = "your_database"
   
   # LLM API KEYS
   DEEPSEEK_API_KEY = "your_deepseek_key"
   OPENAI_API_KEY = "your_openai_key"
   
   # WEB SCRAPING
   FIRECRAWL_API_KEY = "your_firecrawl_key"
   
   # MONITORING & TRACING
   LANGSMITH_TRACING = "true"
   LANGSMITH_PROJECT = "George"
   LANGSMITH_API_KEY = "your_langsmith_key"
   
   # VECTOR DATABASE (PINECONE)
   PINECONE_INDEX_NAME = "george"
   PINECONE_API_KEY = "your_pinecone_key"
   PINECONE_ENVIRONMENT = "us-east1-aws"
   
   # EMAIL SMTP CONFIGURATION
   smtp_host = "your_smtp_host"
   smtp_port = 587
   smtp_user = "your_email@domain.com"
   smtp_password = "your_app_password"
   ```

That's it! Your George AI system will be live and ready to use.

## Tool System

| Tool | Example Queries |
|------|----------------|
| **vector_tool** | "When is check-in and check-out?", "What types of rooms do you have?" |
| **sql_tool** | "Are there rooms available this weekend?", "What's my booking status?", "Show me my reservation details" |
| **booking_tool** | "I want to book a room", "Help me make a reservation" |
| **chat_tool** | "Hello, how are you?", "What are the things to do in the area?" |
| **followup_tool** | Automatic post-booking activity recommendations |

## Key Features

### Intelligent Booking Flow
- Room availability checking with conflict detection
- Dynamic pricing calculation
- Unique booking number generation (`BKG-YYYYMMDD-XXXX`)
- Professional email confirmations

### Smart Query Processing
- LLM-powered intent classification
- Context-aware responses using conversation memory
- Seamless tool switching based on user needs

### Production Features
- Multi-tier database security with Railway hosting
- Real-time SQL query panel for development
- Comprehensive logging and LangSmith monitoring
- Pinecone vector storage for semantic search
- Streamlit Cloud deployment ready

## Configuration

The system supports multiple database connections for different environments and uses role-based access control for security.

## Dependencies

**Core Framework:**
- **Streamlit** (1.44.1) - Web application framework
- **LangChain** (0.0.353) - LLM orchestration and memory
- **LangGraph** (0.3.31) - Advanced workflow management
- **OpenAI** (1.75.0) - Language model provider

**Database & Storage:**
- **MySQL Connector** (9.3.0) - Database connectivity
- **FAISS** (1.10.0) - Vector similarity search
- **Pinecone** (6.0.2) - Vector database (optional)
- **SQLAlchemy** (2.0.40) - Database ORM

**Data Processing:**
- **Pandas** (2.2.3) - Data manipulation
- **NumPy** (2.2.5) - Numerical computing
- **Pydantic** (2.11.3) - Data validation

**Utilities:**
- **python-dotenv** (1.1.0) - Environment management
- **tiktoken** (0.9.0) - Token counting
- **tenacity** (9.1.2) - Retry logic
- **requests** (2.32.3) - HTTP client

See `requirements.txt` for complete dependency list.

## Security

- Environment-based secret management
- SQL injection protection with parameterized queries
- TLS-encrypted email delivery
- Secure database connection handling

## Development

Enable developer tools in the sidebar for SQL queries, real-time logging, and system architecture visualization.

## License

This project is designed for hotel booking and customer service applications.

---

**📚 Built as a final project for an AI course - A comprehensive study case demonstrating real-world conversational AI implementation for the hospitality industry.**

**🏨 Designed for Chez Govinda Hotel**