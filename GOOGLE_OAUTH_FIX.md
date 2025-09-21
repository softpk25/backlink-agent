# Fix Google OAuth Redirect URI Error

## Quick Fix Instructions

### The Error
You're getting: `Error 400: redirect_uri_mismatch`

This happens because Google expects the exact redirect URI that's registered in your Google Cloud Console.

### Solution - Add Redirect URI to Google Cloud Console

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com/
   - Make sure you're in the correct project (Project ID: 500377612)

2. **Navigate to OAuth Credentials**
   - Click on the hamburger menu (☰)
   - Go to **APIs & Services** → **Credentials**

3. **Edit Your OAuth 2.0 Client**
   - Find your OAuth client: `223019563074-cdr1us0i30jc4hhldtplarabgbt7kv5.apps.googleusercontent.com`
   - Click on it to open the edit page

4. **Add Authorized Redirect URIs**
   - Scroll down to **Authorized redirect URIs**
   - Click **ADD URI**
   - Add these URIs exactly as shown:
     ```
     http://localhost:8080
     http://localhost:8080/
     ```
   - Click **SAVE** at the bottom

### After Fixing the Redirect URI

1. **Run the Authentication Setup**
   ```bash
   cd ..\prometrix\Backlink-Off-Page
   python setup_gsc_auth.py
   ```

2. **Complete Google Login**
   - A browser will open
   - Log in with your Google account
   - Grant permissions for Search Console access
   - You'll see "The authentication flow has completed" message

3. **Use GSC in Your Application**
   - Open http://localhost:8882 in your browser
   - In the Backlink Intelligence section:
     - Enter your domain (e.g., jyotiradityasingh.vercel.app)
     - Select "Google Search Console" as Data Source
     - Click "Analyze"

### The Analysis Will Include
- Total clicks and impressions
- Top performing queries
- Top performing pages
- Click-through rates
- Average positions
- Device and country breakdowns

### Export Analysis Results
After analysis, you can:
1. View results in the UI
2. Export as CSV: The UI will show export options
3. Access via API: `GET /backlinkapi/gsc/analysis/{analysis_id}`

### Important Notes
- The authentication token is saved in `token.json`
- Keep this file secure - it contains your access credentials
- The token will auto-refresh when needed
- You only need to do this OAuth setup once

### If You Still Get Errors
1. Make sure you saved the changes in Google Cloud Console
2. Wait 1-2 minutes for changes to propagate
3. Clear your browser cache
4. Try using an incognito/private browser window
