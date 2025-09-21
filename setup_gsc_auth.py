#!/usr/bin/env python3
"""
Google Search Console Authentication Setup Script
This script helps you authenticate with Google Search Console API
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# The scopes required for Search Console API
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def setup_gsc_authentication():
    """Run the OAuth flow to get credentials"""
    
    # Your OAuth credentials from the .env file
    client_id = "223019563074-cdr1us0i30jc4hhldtplarabgbt7kv5.apps.googleusercontent.com"
    client_secret = "GOCSPX-3FHF-imOidWtmbxGs3sdWdAyZt"
    project_id = "500377612"
    
    print("Setting up Google Search Console authentication...")
    print("=" * 50)
    
    # Create credentials configuration
    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    # Save credentials to a file
    with open('credentials.json', 'w') as f:
        json.dump(client_config, f, indent=2)
    print("✓ Created credentials.json file")
    
    creds = None
    # Check if we already have a token
    if os.path.exists('token.json'):
        print("Found existing token.json, loading credentials...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("\nStarting OAuth flow...")
            print("A browser window will open for Google authentication.")
            print("If the browser doesn't open automatically, please visit the URL shown below.")
            print("-" * 50)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Try port 8080 first (matching the redirect URI)
            try:
                creds = flow.run_local_server(port=8080, open_browser=True)
            except:
                # If port 8080 is busy, use port 0 (any available port)
                print("\nPort 8080 is busy, trying with a random port...")
                creds = flow.run_local_server(port=0, open_browser=True)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("\n✓ Authentication successful! Credentials saved to token.json")
    
    # Test the credentials by listing verified sites
    try:
        print("\nTesting connection to Google Search Console...")
        service = build('searchconsole', 'v1', credentials=creds)
        sites_list = service.sites().list().execute()
        
        sites = sites_list.get('sitesData', [])
        if sites:
            print(f"\n✓ Success! Found {len(sites)} verified site(s):")
            for site in sites:
                print(f"  - {site['siteUrl']}")
        else:
            print("\n⚠ No verified sites found. Please verify your sites in Google Search Console.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error testing connection: {str(e)}")
        return False

def main():
    """Main function"""
    print("Google Search Console OAuth Setup")
    print("This script will help you authenticate with Google Search Console\n")
    
    success = setup_gsc_authentication()
    
    if success:
        print("\n" + "="*50)
        print("Setup completed successfully!")
        print("\nYou can now:")
        print("1. Restart your FastAPI server")
        print("2. Use the 'Connect GSC' button in the web interface")
        print("3. Or directly use the GSC analysis features")
        print("\nYour authentication tokens are saved in 'token.json'")
        print("Keep this file secure and don't share it!")
    else:
        print("\nSetup failed. Please check the error messages above.")
        print("\nTroubleshooting tips:")
        print("1. Make sure you have the Search Console API enabled in Google Cloud Console")
        print("2. Verify that the OAuth client ID and secret are correct")
        print("3. Add http://localhost:8080 to your authorized redirect URIs in Google Cloud Console")

if __name__ == "__main__":
    main()
