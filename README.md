# Prometrix SEO Agents API

A comprehensive backlink management and off-page SEO automation platform built with FastAPI and modern web technologies.

## 🚀 Features

### Core Functionality
- **Backlink Management**: Import, analyze, and manage backlinks from various SEO tools
- **Risk Assessment**: AI-powered risk scoring for backlinks (low/medium/high)
- **Competitor Analysis**: Identify link opportunities by analyzing competitor backlink profiles
- **Outreach Campaigns**: Create and manage automated email outreach campaigns
- **Data Export**: Export backlink data in multiple formats (CSV, disavow files)

### Technical Features
- **Modern API**: FastAPI with automatic OpenAPI documentation
- **Database**: SQLite with SQLModel ORM for easy data management
- **Frontend**: Responsive web interface with Tailwind CSS and Chart.js
- **CORS Support**: Cross-origin requests enabled for local development
- **Health Monitoring**: Built-in health check endpoints

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup
1. Clone or download the project
2. **Create environment configuration:**
   ```bash
   # Copy the example environment file
   cp env.example .env
   # Then edit .env with your actual API keys
   ```
3. **Configure your API keys in the `.env` file** (see Configuration section below)
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the application:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Open your browser and navigate to `http://localhost:8000`

## 📊 API Endpoints

### Core Endpoints
- `GET /` - Main application interface
- `GET /health` - Health check endpoint
- `GET /api` - API information and available endpoints

### Backlink Management
- `GET /api/backlinks` - Get backlinks with filtering options
- `GET /api/backlinks/{id}` - Get specific backlink details
- `GET /api/backlinks/summary` - Get backlink analytics summary
- `POST /api/backlinks/import` - Import backlinks from CSV
- `GET /api/export/backlinks.csv` - Export backlinks to CSV

### Analysis & Intelligence
- `POST /api/analyze` - Analyze domain backlink profile
- `POST /api/competitors/analyze` - Analyze competitor backlink gaps

### Campaign Management
- `POST /api/campaigns` - Create new outreach campaigns
- `GET /api/campaigns/metrics` - Get campaign performance metrics
- `POST /api/emails/generate` - Generate AI-powered email content

### Utilities
- `POST /api/disavow/generate` - Generate Google-compliant disavow files

## 🔧 Configuration

### Environment Variables Setup

The application requires several API keys and configuration settings. Create a `.env` file in the project root directory to store your sensitive information securely.

#### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# OpenAI API Configuration (for AI email generation)
OPENAI_API_KEY=your_openai_api_key_here

# Google Search Console API Configuration
GSC_CLIENT_ID=your_google_client_id_here
GSC_CLIENT_SECRET=your_google_client_secret_here
GSC_PROJECT_ID=your_google_project_id_here
GSC_REDIRECT_URI=http://localhost:8080
GSC_DEFAULT_PROPERTY=https://yourdomain.com/

# Optional: Existing OAuth tokens (if you have them)
GSC_ACCESS_TOKEN=your_access_token_here
GSC_REFRESH_TOKEN=your_refresh_token_here

# Database Configuration (optional - defaults to SQLite)
DATABASE_URL=sqlite:///./prometrix.db

# CORS Configuration (optional)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

#### How to Get API Keys

**OpenAI API Key:**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and add it to your `.env` file

**Google Search Console API Credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Search Console API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Desktop application" as the application type
6. Download the credentials JSON file
7. Extract the `client_id`, `client_secret`, and `project_id` from the JSON file
8. Add these values to your `.env` file

#### Security Notes

- **Never commit your `.env` file to version control**
- The `.env` file is already included in `.gitignore` to prevent accidental commits
- Keep your API keys secure and rotate them regularly
- Use different keys for development and production environments
- Consider using environment-specific `.env` files (`.env.development`, `.env.production`)

#### Example .env File Structure

```bash
# Copy this template and fill in your actual values
OPENAI_API_KEY=sk-1234567890abcdef...
GSC_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GSC_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
GSC_PROJECT_ID=123456789
GSC_REDIRECT_URI=http://localhost:8080
GSC_DEFAULT_PROPERTY=https://example.com/
```

### Database Configuration
- Default: SQLite database (`prometrix.db`)
- Automatically created on first run
- Includes sample data for demonstration
- For production, consider PostgreSQL or MySQL

## 📁 Project Structure

```
Backlink-Off-Page/
├── main.py                 # Main FastAPI application
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from env.example)
├── env.example             # Example environment configuration
├── .gitignore              # Git ignore file
├── prometrix.db           # SQLite database (created automatically)
├── static/                # Static files
│   └── backlink_seo_agents.html  # Frontend interface
├── test_api.py            # API testing script
├── setup_gsc_auth.py      # GSC authentication setup script
└── README.md              # This file
```

## 🧪 Testing

Run the test script to verify API functionality:

```bash
python test_api.py
```

This will test all major endpoints and provide feedback on their status.

## 🚀 Usage Examples

### Import Backlinks
1. Prepare a CSV file with columns like:
   - `backlink_source` (required)
   - `anchor_text`
   - `target_url`
   - `domain_authority`
   - `nofollow`
   - `date_found`
   - `link_type`
   - `source_domain`

2. Use the web interface or API to upload the file

### Analyze Competitors
1. Navigate to the Competitor Analysis section
2. Enter your domain and competitor domains
3. Set minimum Domain Authority requirements
4. Click "Analyze Gaps" to find opportunities

### Create Outreach Campaigns
1. Go to the Campaigns section
2. Fill in campaign details (name, target URL, keywords)
3. Customize email templates for each follow-up step
4. Launch the campaign to start outreach

## 🔒 Security Features

- Input validation for all endpoints
- File type validation for uploads
- Error handling with appropriate HTTP status codes
- CORS configuration for development

## 🚧 Known Limitations

- Currently uses SQLite (not suitable for high-volume production)
- AI email generation is stubbed (ready for OpenAI/Claude integration)
- External API integrations are simulated
- No user authentication system

## 🛣️ Roadmap

- [ ] User authentication and multi-tenant support
- [ ] PostgreSQL/MySQL database support
- [ ] Real-time notifications
- [ ] Advanced analytics and reporting
- [ ] Integration with major SEO tools (Ahrefs, SEMrush, Moz)
- [ ] Email automation and tracking
- [ ] Mobile application

## 🆘 Support

For issues and questions:
1. Check the existing documentation
2. Review the API endpoints at `/api`
3. Test with the provided test script
4. Check server logs for error details

## 🔄 Recent Updates

- Fixed deprecated `datetime.utcnow()` usage
- Added automatic risk level calculation for imported backlinks
- Improved error handling and validation
- Added health check and API info endpoints
- Enhanced CSV import with better column mapping
- Added comprehensive testing script
