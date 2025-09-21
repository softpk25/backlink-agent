# How to Run the Prometrix SEO Agents Application

## ✅ The application is now running successfully!

### Access the Application

1. **Web Interface**: Open your web browser and go to:
   - http://localhost:8882
   - This will show the SEO Backlink Management interface

2. **API Documentation**: View the interactive API docs at:
   - http://localhost:8882/docs (Swagger UI)
   - http://localhost:8882/redoc (ReDoc)

### Running the Application

To start the server, open a terminal in the project directory and run:

```bash
cd C:\Users\jyoti\Desktop\prometrix\Backlink-Off-Page
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8882 --reload
```

### Features Available

1. **Backlink Intelligence**: Monitor and analyze your backlink profile
2. **Competitor Backlink Spy**: Discover link opportunities from competitors
3. **Link Building Campaigns**: Create and manage outreach campaigns

### Testing the API

You can test the API using the provided test scripts:

```bash
# Test basic connection
python test_connection.py

# Test API endpoints
python test_api_simple.py

# Full API test
python test_api.py
```

### Troubleshooting

If you encounter any issues:

1. Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Check that port 8882 is not in use by another application

3. The SQLite database (prometrix.db) will be created automatically on first run

### API Endpoints

The main API endpoints are available under `/backlinkapi/`:
- `/backlinkapi/backlinks` - Manage backlinks
- `/backlinkapi/competitors/analyze` - Analyze competitor backlinks
- `/backlinkapi/campaigns` - Manage outreach campaigns
- `/backlinkapi/emails/generate` - Generate AI-powered emails

Enjoy using Prometrix SEO Agents! 🚀
