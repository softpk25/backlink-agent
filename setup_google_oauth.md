# Setting Up Google OAuth for Search Console Integration

## The Problem
You're getting a redirect URI mismatch error because the redirect URI in your Google Cloud Console doesn't match what the application is using.

## Solution Steps

### 1. Update Google Cloud Console Settings

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (Project ID: 500377612)
3. Navigate to **APIs & Services** > **Credentials**
4. Find your OAuth 2.0 Client ID: `223019563074-cdr1us0i30jc4hhldtplarabgbt7kv5.apps.googleusercontent.com`
5. Click on it to edit
6. In the **Authorized redirect URIs** section, add these URIs:
   - `http://localhost:8080`
   - `http://localhost:8882/backlinkapi/gsc/oauth/callback`
   - `http://localhost:8080/`
   - `http://localhost:0`
7. Click **Save**

### 2. Alternative: Use the Simplified GSC Setup

The application has a simpler GSC setup endpoint that handles OAuth differently. After restarting the server, try:

1. Click the "Connect GSC" button in the UI
2. If it still fails, navigate directly to: `http://localhost:8882/backlinkapi/gsc/setup`
3. This will use the installed app flow which is more flexible with redirect URIs

### 3. Manual Token Generation (If OAuth Still Fails)

If OAuth continues to fail, you can generate tokens manually:

1. Use Google's OAuth 2.0 Playground: https://developers.google.com/oauthplayground/
2. Select the Search Console API v3 scope: `https://www.googleapis.com/auth/webmasters.readonly`
3. Authorize and get the access token and refresh token
4. Update your .env file with:
   ```
   GSC_ACCESS_TOKEN=your-access-token
   GSC_REFRESH_TOKEN=your-refresh-token
   ```

## Current Configuration

Your current .env file has:
- Client ID: `223019563074-cdr1us0i30jc4hhldtplarabgbt7kv5.apps.googleusercontent.com`
- Redirect URI: `http://localhost:8080`

## Testing the Connection

After fixing the redirect URI:

1. Restart the server
2. Open `http://localhost:8882`
3. Click "Connect GSC" button
4. Complete the Google authentication
5. Once connected, enter your domain in the analysis field
6. Click "Analyze" to get GSC data

## Saving Analysis Results

The application will automatically save analysis results as JSON in the database. To export:

1. After analysis completes, use the export endpoint: 
   `http://localhost:8882/backlinkapi/export/gsc-analysis/{analysis_id}.csv`

2. Or access the raw JSON data via API:
   `http://localhost:8882/backlinkapi/gsc/analysis/{analysis_id}`
