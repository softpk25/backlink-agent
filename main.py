import os
import io
import csv
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Google APIs
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build as gbuild

# =========================
# Database Models (TRS-aligned)
# =========================

class Backlink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    backlink_source: str
    anchor_text: Optional[str] = None
    target_url: Optional[str] = None
    domain_authority: Optional[int] = None
    nofollow: Optional[bool] = None
    date_found: Optional[datetime] = None
    link_type: Optional[str] = None
    source_domain: Optional[str] = None
    risk_level: Optional[str] = None  # "low","medium","high"

class LinkRiskScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    backlink_id: int
    risk_score: float
    reason: Optional[str] = None

class CompetitorGapLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    linking_domain: str
    da: Optional[int] = None
    your_site: bool = False
    competitor_a: bool = False
    competitor_b: bool = False
    effort_level: str = "Medium"  # Easy/Medium/Hard
    potential_value: int = 50     # for plotting

class OutreachCampaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url_to_promote: Optional[str] = None
    target_keywords: Optional[str] = None
    prospect_type: Optional[str] = None
    email_tone: Optional[str] = None
    status: str = "Active"

class AIEmailOutput(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: Optional[int] = None
    step: int
    subject: str
    body: str

# New model to store GSC analysis results
class GSCAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    site_url: str
    analysis_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_clicks: Optional[int] = None
    total_impressions: Optional[int] = None
    avg_ctr: Optional[float] = None
    avg_position: Optional[float] = None
    total_queries: Optional[int] = None
    data_json: Optional[str] = None  # Store raw analysis data as JSON

# =========================
# GSC Domain Analysis Class
# =========================

class GoogleSearchConsoleAnalyzer:
    def __init__(self, client_id: str, client_secret: str, project_id: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id or "500377612"  # Default from your credentials
        self.scopes = ['https://www.googleapis.com/auth/webmasters.readonly']
        self.service = None
        self.credentials = None
        
    def create_credentials_file(self):
        """Create credentials.json file from provided details"""
        credentials_data = {
            "installed": {
                "client_id": self.client_id,
                "project_id": self.project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": self.client_secret,
                "redirect_uris": ["http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"]
            }
        }
        
        with open('credentials.json', 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        return 'credentials.json'
    
    def authenticate(self):
        """Authenticate with Google Search Console API"""
        creds = None
        
        # Check if token.json exists (saved credentials)
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.scopes)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Create credentials file
                credentials_file = self.create_credentials_file()
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, self.scopes)
                # Use port 8080 to match the redirect URI in Google Cloud Console
                creds = flow.run_local_server(port=8080, open_browser=True)
            
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        self.service = gbuild('searchconsole', 'v1', credentials=creds)
        return True
    
    def get_verified_sites(self):
        """Get all verified sites for the authenticated user"""
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            sites = self.service.sites().list().execute()
            return [site['siteUrl'] for site in sites.get('sitesData', [])]
        except Exception as e:
            print(f"Error getting verified sites: {e}")
            return []
    
    def get_search_analytics(self, site_url: str, start_date: str, end_date: str, 
                           dimensions: List[str] = None, limit: int = 1000,
                           filters: Dict = None):
        """Get search analytics data"""
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'rowLimit': limit
        }
        
        if dimensions:
            request_body['dimensions'] = dimensions
            
        if filters:
            request_body['dimensionFilterGroups'] = filters
        
        try:
            response = self.service.searchanalytics().query(
                siteUrl=site_url, body=request_body).execute()
            return response
        except Exception as e:
            print(f"Error getting search analytics: {e}")
            return {}
    
    def analyze_domain_comprehensive(self, site_url: str, days_back: int = 30):
        """Perform comprehensive domain analysis"""
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        # Calculate date range
        end_date = datetime.now() - timedelta(days=3)  # GSC data is 2-3 days behind
        start_date = end_date - timedelta(days=days_back)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        print(f"Analyzing {site_url} from {start_date_str} to {end_date_str}")
        
        analysis_results = {
            'site_url': site_url,
            'period': {'start': start_date_str, 'end': end_date_str},
            'analysis_date': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # 1. Overall Performance Summary
            overview = self.get_search_analytics(site_url, start_date_str, end_date_str, dimensions=[])
            if overview and 'rows' in overview and overview['rows']:
                row = overview['rows'][0]
                analysis_results['overview'] = {
                    'total_clicks': row.get('clicks', 0),
                    'total_impressions': row.get('impressions', 0),
                    'avg_ctr': round(row.get('ctr', 0) * 100, 2),
                    'avg_position': round(row.get('position', 0), 1)
                }
            else:
                analysis_results['overview'] = {
                    'total_clicks': 0,
                    'total_impressions': 0,
                    'avg_ctr': 0,
                    'avg_position': 0
                }
            
            # 2. Performance by Date
            by_date = self.get_search_analytics(site_url, start_date_str, end_date_str, 
                                              dimensions=['date'], limit=100)
            analysis_results['performance_by_date'] = by_date.get('rows', [])
            
            # 3. Top Performing Queries
            top_queries = self.get_search_analytics(site_url, start_date_str, end_date_str,
                                                  dimensions=['query'], limit=50)
            analysis_results['top_queries'] = top_queries.get('rows', [])
            
            # 4. Top Performing Pages
            top_pages = self.get_search_analytics(site_url, start_date_str, end_date_str,
                                                dimensions=['page'], limit=50)
            analysis_results['top_pages'] = top_pages.get('rows', [])
            
            # 5. Performance by Country
            by_country = self.get_search_analytics(site_url, start_date_str, end_date_str,
                                                 dimensions=['country'], limit=25)
            analysis_results['performance_by_country'] = by_country.get('rows', [])
            
            # 6. Performance by Device
            by_device = self.get_search_analytics(site_url, start_date_str, end_date_str,
                                                dimensions=['device'])
            analysis_results['performance_by_device'] = by_device.get('rows', [])
            
            # 7. Query Performance Analysis
            query_page = self.get_search_analytics(site_url, start_date_str, end_date_str,
                                                 dimensions=['query', 'page'], limit=100)
            analysis_results['query_page_performance'] = query_page.get('rows', [])
            
            return analysis_results
            
        except Exception as e:
            analysis_results['error'] = str(e)
            return analysis_results

# =========================
# App & DB bootstrap
# =========================
DB_URL = "sqlite:///./prometrix.db"
engine = create_engine(DB_URL, echo=False)
load_dotenv()

def init_db():
    SQLModel.metadata.create_all(engine)

def seed_demo_data():
    """Seed demo data for initial setup"""
    with Session(engine) as s:
        if not s.exec(select(Backlink)).first():
            demo_rows = [
                Backlink(backlink_source="https://spammysite.com/bad", source_domain="spammysite.com",
                         anchor_text="cheap loans", domain_authority=8, nofollow=True,
                         date_found=datetime.now(timezone.utc), link_type="footer", risk_level="high"),
                Backlink(backlink_source="https://qualityblog.com/good", source_domain="qualityblog.com",
                         anchor_text="financial planning", domain_authority=67, nofollow=False,
                         date_found=datetime.now(timezone.utc), link_type="editorial", risk_level="low"),
                Backlink(backlink_source="https://mediumblog.net/ok", source_domain="mediumblog.net",
                         anchor_text="click here", domain_authority=34, nofollow=False,
                         date_found=datetime.now(timezone.utc), link_type="contextual", risk_level="medium")
            ]
            for r in demo_rows:
                s.add(r)
            s.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    seed_demo_data()
    yield
    # Shutdown (if needed)

app = FastAPI(title="Prometrix SEO Agents API", version="1.0", lifespan=lifespan)

# CORS: allow local file and localhost usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: serve your HTML from ./static
STATIC_DIR = "./static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Global GSC analyzer instance
gsc_analyzer = None

# =============== Helper Functions ===============
def risk_bucket(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"

def calculate_risk_level(domain_authority: Optional[int], nofollow: Optional[bool], link_type: Optional[str]) -> str:
    """Calculate risk level based on backlink characteristics"""
    if domain_authority is None:
        domain_authority = 0
    
    # High risk factors
    if domain_authority < 10:
        return "high"
    if nofollow and domain_authority < 20:
        return "high"
    if link_type in ["footer", "sidebar"] and domain_authority < 30:
        return "high"
    
    # Medium risk factors
    if domain_authority < 30:
        return "medium"
    if link_type in ["footer", "sidebar"]:
        return "medium"
    
    # Low risk
    return "low"

def parse_bool(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in {"1","true","yes","y"}

def get_gsc_analyzer():
    """Get or create GSC analyzer instance"""
    global gsc_analyzer
    
    if gsc_analyzer is None:
        client_id = os.getenv("GSC_CLIENT_ID", "223019563074-cdr1us0i30jc4hhldtplarabgbt7kv5.apps.googleusercontent.com")
        client_secret = os.getenv("GSC_CLIENT_SECRET", "GOCSPX-3FHF-imOidWtmbxGs3sdWdAyZt")
        project_id = os.getenv("GSC_PROJECT_ID", "500377612")
        
        gsc_analyzer = GoogleSearchConsoleAnalyzer(
            client_id=client_id,
            client_secret=client_secret,
            project_id=project_id
        )
    
    return gsc_analyzer

# =============== Routes ===============

@app.get("/", response_class=HTMLResponse)
def root():
    # Serve the UI if you've copied it to static/
    index_path = os.path.join(STATIC_DIR, "backlink_seo_agents.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h2>Prometrix SEO Agents API is running.</h2>")

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    try:
        with Session(engine) as s:
            # Test database connection
            s.exec(select(Backlink).limit(1)).first()
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(500, f"Health check failed: {str(e)}")

@app.get("/backlinkapi")
def api_info():
    """API information and available endpoints"""
    return {
        "name": "Prometrix SEO Agents API",
        "version": "1.0",
        "description": "Backlink management and off-page SEO automation platform with GSC integration",
        "endpoints": {
            "backlinks": "/backlinkapi/backlinks",
            "import": "/backlinkapi/backlinks/import",
            "summary": "/backlinkapi/backlinks/summary",
            "export": "/backlinkapi/export/backlinks.csv",
            "campaigns": "/backlinkapi/campaigns",
            "competitors": "/backlinkapi/competitors/analyze",
            "disavow": "/backlinkapi/disavow/generate",
            "emails": "/backlinkapi/emails/generate",
            "gsc_setup": "/backlinkapi/gsc/setup",
            "gsc_analyze": "/backlinkapi/gsc/analyze",
            "gsc_sites": "/backlinkapi/gsc/sites"
        }
    }

# =========================
# New GSC Integration Routes
# =========================

@app.post("/backlinkapi/gsc/setup")
def setup_gsc():
    """Setup GSC authentication"""
    try:
        analyzer = get_gsc_analyzer()
        success = analyzer.authenticate()
        
        if success:
            # Get available sites
            sites = analyzer.get_verified_sites()
            return {
                "status": "success",
                "message": "GSC authentication successful",
                "verified_sites": sites
            }
        else:
            raise HTTPException(500, "Authentication failed")
            
    except Exception as e:
        raise HTTPException(500, f"GSC setup failed: {str(e)}")

@app.get("/backlinkapi/gsc/sites")
def get_gsc_sites():
    """Get all verified sites from GSC"""
    try:
        analyzer = get_gsc_analyzer()
        
        if not analyzer.service:
            raise HTTPException(401, "GSC not authenticated. Please setup authentication first using /backlinkapi/gsc/setup")
        
        sites = analyzer.get_verified_sites()
        return {"verified_sites": sites}
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get GSC sites: {str(e)}")

@app.post("/backlinkapi/gsc/analyze")
def analyze_gsc_domain(payload: Dict[str, Any]):
    """Comprehensive GSC domain analysis"""
    try:
        site_url = payload.get("site_url")
        days_back = payload.get("days_back", 30)
        
        if not site_url:
            raise HTTPException(400, "site_url is required")
        
        analyzer = get_gsc_analyzer()
        
        if not analyzer.service:
            raise HTTPException(401, "GSC not authenticated. Please setup authentication first using /backlinkapi/gsc/setup")
        
        # Perform comprehensive analysis
        analysis_results = analyzer.analyze_domain_comprehensive(site_url, days_back)
        
        # Store results in database
        with Session(engine) as s:
            gsc_analysis = GSCAnalysis(
                site_url=site_url,
                analysis_date=datetime.now(timezone.utc),
                total_clicks=analysis_results.get('overview', {}).get('total_clicks'),
                total_impressions=analysis_results.get('overview', {}).get('total_impressions'),
                avg_ctr=analysis_results.get('overview', {}).get('avg_ctr'),
                avg_position=analysis_results.get('overview', {}).get('avg_position'),
                total_queries=len(analysis_results.get('top_queries', [])),
                data_json=json.dumps(analysis_results)
            )
            s.add(gsc_analysis)
            s.commit()
            s.refresh(gsc_analysis)
        
        return {
            "status": "success",
            "analysis_id": gsc_analysis.id,
            "results": analysis_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@app.get("/backlinkapi/gsc/analysis/{analysis_id}")
def get_gsc_analysis(analysis_id: int):
    """Get stored GSC analysis by ID"""
    with Session(engine) as s:
        analysis = s.exec(select(GSCAnalysis).where(GSCAnalysis.id == analysis_id)).first()
        if not analysis:
            raise HTTPException(404, "Analysis not found")
        
        # Parse the stored JSON data
        try:
            data = json.loads(analysis.data_json) if analysis.data_json else {}
        except:
            data = {}
        
        return {
            "id": analysis.id,
            "site_url": analysis.site_url,
            "analysis_date": analysis.analysis_date,
            "summary": {
                "total_clicks": analysis.total_clicks,
                "total_impressions": analysis.total_impressions,
                "avg_ctr": analysis.avg_ctr,
                "avg_position": analysis.avg_position,
                "total_queries": analysis.total_queries
            },
            "full_data": data
        }

@app.get("/backlinkapi/gsc/analysis/history/{site_url}")
def get_gsc_analysis_history(site_url: str):
    """Get analysis history for a specific site"""
    with Session(engine) as s:
        analyses = s.exec(
            select(GSCAnalysis)
            .where(GSCAnalysis.site_url == site_url)
            .order_by(GSCAnalysis.analysis_date.desc())
        ).all()
        
        return [
            {
                "id": analysis.id,
                "analysis_date": analysis.analysis_date,
                "total_clicks": analysis.total_clicks,
                "total_impressions": analysis.total_impressions,
                "avg_ctr": analysis.avg_ctr,
                "avg_position": analysis.avg_position,
                "total_queries": analysis.total_queries
            }
            for analysis in analyses
        ]

# ---- Demo data endpoint ----
@app.get("/backlinkapi/demo")
def get_demo_data():
    """Serve static demo dataset for UI."""
    demo_path = os.path.join(STATIC_DIR, "demo_data.json")
    if not os.path.exists(demo_path):
        raise HTTPException(404, "Demo data not found")
    try:
        with open(demo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Failed to read demo data: {e}")

# Updated analyze_domain endpoint with GSC integration
@app.post("/backlinkapi/analyze")
def analyze_domain(payload: Dict[str, Any]):
    """Enhanced domain analysis with GSC integration"""
    domain = payload.get("domain")
    period = payload.get("period", "30d")
    source = payload.get("source", "GSC")
    
    # Parse period
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(str(period).lower(), 30)
    
    # Get existing backlink summary
    summary = backlinks_summary()
    
    # Initialize GSC data structure
    gsc_data = {"enabled": False, "error": None}
    
    if source == "GSC" and domain:
        try:
            analyzer = get_gsc_analyzer()
            
            if analyzer.service:
                # Perform GSC analysis
                analysis_results = analyzer.analyze_domain_comprehensive(domain, days)
                
                if 'error' not in analysis_results:
                    gsc_data = {
                        "enabled": True,
                        "site_url": domain,
                        "period": analysis_results.get("period"),
                        "overview": analysis_results.get("overview"),
                        "top_queries": analysis_results.get("top_queries", [])[:10],
                        "top_pages": analysis_results.get("top_pages", [])[:10],
                        "performance_by_device": analysis_results.get("performance_by_device", []),
                        "performance_by_country": analysis_results.get("performance_by_country", [])[:5]
                    }
                else:
                    gsc_data["error"] = analysis_results.get("error")
            else:
                gsc_data["error"] = "GSC not authenticated"
                
        except Exception as e:
            gsc_data["error"] = str(e)
    
    return {
        "message": f"Analysis for {domain} via {source} ({period}) complete.",
        "domain": domain,
        "period": period,
        "source": source,
        "summary": summary,
        "gsc": gsc_data
    }

# Keep all existing routes below...
# [All your existing routes remain the same from here...]

# ---- Backlink Import (CSV / Ahrefs/SEMrush/Moz export formats) ----
@app.post("/backlinkapi/backlinks/import")
async def import_backlinks(
    source: str = Form("csv"),
    file: UploadFile = File(...)
):
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "Only CSV files are supported")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        # Validate that we have at least some data
        if df.empty:
            raise HTTPException(400, "CSV file is empty")
            
    except Exception as e:
        raise HTTPException(400, f"Failed to parse CSV: {e}")

    # Try to map common column names coming from different tools
    colmap_candidates = {
        "backlink_source": ["backlink_source", "url_from", "source_url", "referring_page", "Backlink"],
        "anchor_text": ["anchor_text", "anchor", "text"],
        "target_url": ["target_url", "url_to", "target", "Destination URL"],
        "domain_authority": ["domain_authority", "da", "Domain Authority", "Authority Score", "Domain Rating"],
        "nofollow": ["nofollow", "is_nofollow", "nofollow?"],
        "date_found": ["date_found", "first_seen", "Found On", "First seen"],
        "link_type": ["link_type", "type", "Link Type"],
        "source_domain": ["source_domain", "domain_from", "Referring Domain", "root_domain"]
    }

    def pick(series: pd.Series, keys: List[str]) -> Optional[str]:
        """Pick the first available column name from the candidates"""
        for k in keys:
            if k in series:
                return k
        return None

    inserted = 0
    errors = 0
    with Session(engine) as s:
        for idx, row in df.iterrows():
            try:
                # Extract values
                da = int(row[pick(df.columns, colmap_candidates["domain_authority"])]) if pick(df.columns, colmap_candidates["domain_authority"]) else None
                nofollow_val = parse_bool(row[pick(df.columns, colmap_candidates["nofollow"])]) if pick(df.columns, colmap_candidates["nofollow"]) else None
                link_type_val = (pick(df.columns, colmap_candidates["link_type"]) and row[pick(df.columns, colmap_candidates["link_type"])])
                
                bk = Backlink(
                    backlink_source = (pick(df.columns, colmap_candidates["backlink_source"]) and row[pick(df.columns, colmap_candidates["backlink_source"])]) or str(row.get("url","")),
                    anchor_text = (pick(df.columns, colmap_candidates["anchor_text"]) and row[pick(df.columns, colmap_candidates["anchor_text"])]),
                    target_url = (pick(df.columns, colmap_candidates["target_url"]) and row[pick(df.columns, colmap_candidates["target_url"])]),
                    domain_authority = da,
                    nofollow = nofollow_val,
                    date_found = pd.to_datetime(row[pick(df.columns, colmap_candidates["date_found"])]) if pick(df.columns, colmap_candidates["date_found"]) else datetime.now(timezone.utc),
                    link_type = link_type_val,
                    source_domain = (pick(df.columns, colmap_candidates["source_domain"]) and row[pick(df.columns, colmap_candidates["source_domain"])]),
                    risk_level = calculate_risk_level(da, nofollow_val, link_type_val)
                )
                s.add(bk)
                inserted += 1
            except Exception as e:
                errors += 1
                print(f"Error processing row {idx + 1}: {e}")
                continue
        s.commit()
    
    return {
        "status": "ok", 
        "inserted": inserted, 
        "errors": errors,
        "total_rows": len(df),
        "message": f"Successfully imported {inserted} backlinks. {errors} rows had errors."
    }

# ---- Intelligence summary for charts/cards ----
@app.get("/backlinkapi/backlinks/summary")
def backlinks_summary():
    with Session(engine) as s:
        rows = s.exec(select(Backlink)).all()
    total = len(rows)
    by_risk = {"low": 0, "medium": 0, "high": 0}
    anchor_buckets = {"Branded":0,"Exact Match":0,"Partial Match":0,"Generic":0,"Naked URL":0}

    for r in rows:
        if r.risk_level:
            by_risk[r.risk_level] = by_risk.get(r.risk_level, 0) + 1
        # naive anchor bucket
        a = (r.anchor_text or "").lower()
        if not a or a.startswith("http"):
            anchor_buckets["Naked URL"] += 1
        elif len(a.split()) == 1:
            anchor_buckets["Exact Match"] += 1
        elif any(k in a for k in ["click here","read more","visit site"]):
            anchor_buckets["Generic"] += 1
        elif any(k in a for k in ["brand","inc","llc"]):
            anchor_buckets["Branded"] += 1
        else:
            anchor_buckets["Partial Match"] += 1

    healthy = by_risk["low"]
    warning = by_risk["medium"]
    toxic = by_risk["high"]
    avg_da = int(sum([r.domain_authority or 0 for r in rows]) / total) if total else 0
    referring_domains = len({r.source_domain for r in rows if r.source_domain})

    return {
        "cards": {
            "total_backlinks": total,
            "referring_domains": referring_domains,
            "average_da": avg_da,
            "toxic_links": toxic
        },
        "health_scorecard": {
            "healthy": healthy, "warning": warning, "toxic": toxic
        },
        "anchor_distribution": anchor_buckets
    }

# =========================
# Google Search Console (GSC) - Enhanced
# =========================

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# Simple in-memory stores for demo (replace with DB in production)
_gsc_oauth_state_store: Dict[str, str] = {}
_gsc_token_store: Dict[str, Dict[str, Optional[str]]] = {}

def gsc_build_flow() -> Flow:
    # Use from_client_config to avoid Flow.__init__ keyword incompatibility with 'scopes'
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.getenv("GSC_CLIENT_ID"),
                "client_secret": os.getenv("GSC_CLIENT_SECRET"),
                "redirect_uris": [os.getenv("GSC_REDIRECT_URI")],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GSC_SCOPES,
        redirect_uri=os.getenv("GSC_REDIRECT_URI"),
    )

def gsc_build_service(creds: Credentials):
    return gbuild("searchconsole", "v1", credentials=creds)

def gsc_load_creds(user_key: str = "default") -> Optional[Credentials]:
    # Prefer in-memory token store (demo); fall back to environment variables
    stored = _gsc_token_store.get(user_key)
    access = stored.get("access_token") if stored else None
    refresh = stored.get("refresh_token") if stored else None
    if not (access or refresh):
        access = os.getenv("GSC_ACCESS_TOKEN")
        refresh = os.getenv("GSC_REFRESH_TOKEN")
        if not (access or refresh):
            return None
    return Credentials(
        token=access,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GSC_CLIENT_ID"),
        client_secret=os.getenv("GSC_CLIENT_SECRET"),
        scopes=GSC_SCOPES,
    )

@app.get("/backlinkapi/gsc/oauth/start")
def gsc_oauth_start(user_key: str = "default"):
    # Validate required environment variables
    missing = [
        name for name in ["GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REDIRECT_URI"]
        if not os.getenv(name)
    ]
    if missing:
        raise HTTPException(500, f"Missing environment variables: {', '.join(missing)}")
    try:
        flow = gsc_build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        # Store state for CSRF protection (use secure session/DB in production)
        _gsc_oauth_state_store[user_key] = state
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        raise HTTPException(500, f"Failed to start OAuth flow: {e}")

@app.get("/backlinkapi/gsc/oauth/callback")
def gsc_oauth_callback(code: str, state: Optional[str] = None, user_key: str = "default"):
    try:
        flow = gsc_build_flow()
        # Validate state (best-effort)
        expected_state = _gsc_oauth_state_store.get(user_key)
        if expected_state and state and expected_state != state:
            raise HTTPException(400, "Invalid OAuth state")
        flow.fetch_token(code=code)
        creds = flow.credentials
        # Persist tokens (replace with DB persistence)
        _gsc_token_store[user_key] = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
        }
        return {
            "status": "ok",
            "has_refresh": bool(creds.refresh_token),
            "user_key": user_key
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"OAuth callback failed: {e}")

@app.get("/backlinkapi/gsc/properties")
def gsc_properties():
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    mgmt = svc.sites().list().execute()
    return mgmt

@app.post("/backlinkapi/gsc/performance/summary")
def gsc_performance_summary(body: Dict[str, Any]):
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    prop = body.get("property_id") or os.getenv("GSC_DEFAULT_PROPERTY")
    query = {
        "startDate": body.get("startDate", "2024-01-01"),
        "endDate": body.get("endDate", "2024-12-31"),
        "dimensions": body.get("dimensions", ["date"]),
        "rowLimit": body.get("rowLimit", 1000)
    }
    resp = svc.searchanalytics().query(siteUrl=prop, body=query).execute()
    return resp

@app.get("/backlinkapi/gsc/pages/metrics")
def gsc_page_metrics(url: str, startDate: str = "2024-01-01", endDate: str = "2024-12-31"):
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    prop = os.getenv("GSC_DEFAULT_PROPERTY")
    body = {
        "startDate": startDate,
        "endDate": endDate,
        "dimensions": ["query"],
        "dimensionFilterGroups": [{
            "filters": [{"dimension": "page", "operator": "equals", "expression": url}]
        }]
    }
    return svc.searchanalytics().query(siteUrl=prop, body=body).execute()

@app.get("/backlinkapi/gsc/opportunities/queries")
def gsc_opportunities(minPos: int = 5, maxPos: int = 20, startDate: str = "2024-01-01", endDate: str = "2024-12-31"):
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    prop = os.getenv("GSC_DEFAULT_PROPERTY")
    body = {
        "startDate": startDate,
        "endDate": endDate,
        "dimensions": ["query", "page"],
        "rowLimit": 25000
    }
    data = svc.searchanalytics().query(siteUrl=prop, body=body).execute()
    rows = data.get("rows", [])
    filtered = []
    for r in rows:
        ctr = r.get("ctr")
        pos = r.get("position")
        if pos is not None and minPos <= pos <= maxPos:
            filtered.append(r)
    return {"rows": filtered}

@app.get("/backlinkapi/gsc/sitemaps")
def gsc_sitemaps_list():
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    prop = os.getenv("GSC_DEFAULT_PROPERTY")
    return svc.sitemaps().list(siteUrl=prop).execute()

@app.post("/backlinkapi/gsc/sitemaps/submit")
def gsc_sitemaps_submit(sitemap_url: str):
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    svc = gsc_build_service(creds)
    prop = os.getenv("GSC_DEFAULT_PROPERTY")
    return svc.sitemaps().submit(siteUrl=prop, feedpath=sitemap_url).execute()

@app.get("/backlinkapi/gsc/url-inspect")
def gsc_url_inspect(url: str):
    creds = gsc_load_creds()
    if not creds:
        raise HTTPException(401, "GSC not connected")
    insp = gbuild("searchconsole", "v1", credentials=creds)
    prop = os.getenv("GSC_DEFAULT_PROPERTY")

# ---- Enhanced Competitor Analysis with AI ----
class CompetitorAnalyzer:
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.openai_api_key and OpenAI:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                print(f"OpenAI client initialization failed: {e}")
    
    def analyze_domain_authority(self, domain: str) -> int:
        """Simulate domain authority analysis - in production, integrate with Moz/Ahrefs API"""
        # Simple heuristic based on domain characteristics
        if any(tld in domain for tld in ['.edu', '.gov']):
            return 85 + (hash(domain) % 15)
        elif any(brand in domain for brand in ['techcrunch', 'forbes', 'cnn', 'bbc']):
            return 80 + (hash(domain) % 20)
        elif len(domain.split('.')[0]) > 15:
            return 20 + (hash(domain) % 30)
        else:
            return 30 + (hash(domain) % 50)
    
    def determine_effort_level(self, da: int, domain: str) -> str:
        """Determine outreach effort level based on domain characteristics"""
        if da >= 80:
            return "Hard"
        elif da >= 50:
            return "Medium"
        else:
            return "Easy"
    
    def generate_link_opportunities(self, your_domain: str, competitors: List[str], min_da: int = 0) -> List[Dict]:
        """Generate realistic link gap opportunities"""
        # Sample high-authority domains that commonly link to business sites
        potential_domains = [
            "techcrunch.com", "forbes.com", "entrepreneur.com", "inc.com", "fastcompany.com",
            "businessinsider.com", "mashable.com", "venturebeat.com", "wired.com", "arstechnica.com",
            "industryblog.net", "smallbusiness.com", "startupnews.com", "digitaltrends.com",
            "marketingland.com", "searchengineland.com", "moz.com", "semrush.com", "hubspot.com",
            "contentmarketinginstitute.com", "socialmediaexaminer.com", "copyblogger.com"
        ]
        
        gaps = []
        for domain in potential_domains[:15]:  # Limit to 15 opportunities
            da = self.analyze_domain_authority(domain)
            if da >= min_da:
                # Simulate competitor link presence
                has_comp_a = hash(domain + competitors[0] if competitors else "") % 3 == 0
                has_comp_b = hash(domain + competitors[1] if len(competitors) > 1 else "") % 3 == 0
                your_site_linked = hash(domain + your_domain) % 5 == 0  # 20% chance you already have link
                
                # Only include if competitors have links but you don't
                if (has_comp_a or has_comp_b) and not your_site_linked:
                    gaps.append({
                        "linking_domain": domain,
                        "da": da,
                        "your_site": your_site_linked,
                        "competitor_a": has_comp_a,
                        "competitor_b": has_comp_b,
                        "effort_level": self.determine_effort_level(da, domain),
                        "potential_value": min(da, 100)  # Use DA as potential value
                    })
        
        return sorted(gaps, key=lambda x: x["da"], reverse=True)
    
    def generate_content_opportunities(self, your_domain: str, competitors: List[str]) -> List[Dict]:
        """Generate AI-powered content opportunities"""
        opportunities = []
        
        if self.client:
            try:
                # Generate content ideas using OpenAI
                prompt = f"""
Analyze the competitive landscape for {your_domain} against competitors {', '.join(competitors[:3])}.

Generate 3 specific content opportunities that could attract backlinks from high-authority sites. For each opportunity, provide:
1. Content type/format
2. Specific topic/angle
3. Why it would attract links
4. Estimated number of potential linking sites
5. Average DA of target sites

Format as JSON array with keys: type, topic, description, target_count, avg_da
"""
                
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.7
                )
                
                content = response.choices[0].message.content.strip()
                # Try to parse JSON response
                try:
                    import re
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        opportunities = json.loads(json_match.group())
                except:
                    pass
                    
            except Exception as e:
                print(f"OpenAI API error: {e}")
        
        # Fallback to predefined opportunities if AI fails
        if not opportunities:
            opportunities = [
                {
                    "type": "Comparison Guide",
                    "topic": f"Best {your_domain.split('.')[0].title()} Alternatives",
                    "description": "Comprehensive comparison including competitor analysis to attract resource page links.",
                    "target_count": 15,
                    "avg_da": 58
                },
                {
                    "type": "Industry Report",
                    "topic": "State of the Industry 2024",
                    "description": "Data-driven report with original research that journalists and bloggers will reference.",
                    "target_count": 23,
                    "avg_da": 67
                },
                {
                    "type": "Resource Collection",
                    "topic": "Ultimate Toolkit for Professionals",
                    "description": "Curated list of tools and resources that other sites will link to as a reference.",
                    "target_count": 31,
                    "avg_da": 41
                }
            ]
        
        return opportunities[:3]

# Global competitor analyzer instance
competitor_analyzer = None

def get_competitor_analyzer():
    """Get or create competitor analyzer instance"""
    global competitor_analyzer
    if competitor_analyzer is None:
        competitor_analyzer = CompetitorAnalyzer()
    return competitor_analyzer

# ---- Enhanced Competitor gap analysis endpoint ----
@app.post("/backlinkapi/competitors/analyze")
def competitor_analyze(payload: Dict[str, Any]):
    """Enhanced competitor analysis with AI-powered insights"""
    try:
        your_domain = payload.get("your_domain", "yourdomain.com")
        competitors = payload.get("competitors", [])[:5]
        min_da = int(payload.get("min_da", 0))
        link_type = payload.get("link_type", "All Types")
        
        analyzer = get_competitor_analyzer()
        
        # Generate link gap opportunities
        gaps = analyzer.generate_link_opportunities(your_domain, competitors, min_da)
        
        # Generate bubble chart data for effort vs reward
        bubbles = []
        for gap in gaps:
            effort_score = {"Easy": 20, "Medium": 50, "Hard": 80}.get(gap["effort_level"], 50)
            bubbles.append({
                "effort": effort_score,
                "value": gap["potential_value"],
                "radius": max(8, min(20, gap["da"] // 5)),
                "domain": gap["linking_domain"]
            })
        
        # Generate content opportunities
        content_opportunities = analyzer.generate_content_opportunities(your_domain, competitors)
        
        # Store analysis in database for future reference
        with Session(engine) as s:
            for gap in gaps:
                existing = s.exec(
                    select(CompetitorGapLink).where(
                        CompetitorGapLink.linking_domain == gap["linking_domain"]
                    )
                ).first()
                
                if not existing:
                    gap_link = CompetitorGapLink(
                        linking_domain=gap["linking_domain"],
                        da=gap["da"],
                        your_site=gap["your_site"],
                        competitor_a=gap["competitor_a"],
                        competitor_b=gap["competitor_b"],
                        effort_level=gap["effort_level"],
                        potential_value=gap["potential_value"]
                    )
                    s.add(gap_link)
            s.commit()
        
        return {
            "status": "success",
            "your_domain": your_domain,
            "competitors_analyzed": len(competitors),
            "gaps": gaps,
            "bubbles": bubbles,
            "content_opportunities": content_opportunities,
            "summary": {
                "total_opportunities": len(gaps),
                "easy_targets": len([g for g in gaps if g["effort_level"] == "Easy"]),
                "medium_targets": len([g for g in gaps if g["effort_level"] == "Medium"]),
                "hard_targets": len([g for g in gaps if g["effort_level"] == "Hard"]),
                "avg_da": sum(g["da"] for g in gaps) // len(gaps) if gaps else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(500, f"Competitor analysis failed: {str(e)}")

# ---- Mark for disavow + generate file ----
@app.post("/backlinkapi/disavow/generate")
def generate_disavow(domains: List[str]):
    # Create a simple disavow text in memory
    buf = io.StringIO()
    buf.write("# Created by Prometrix\n")
    buf.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}Z\n\n")
    for d in domains:
        d = d.strip()
        if d and not d.startswith("#"):
            buf.write(f"domain:{d}\n")
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]),
                             media_type="text/plain",
                             headers={"Content-Disposition": "attachment; filename=disavow.txt"})

# ---- Campaigns ----
@app.post("/backlinkapi/campaigns")
def create_campaign(payload: Dict[str, Any]):
    with Session(engine) as s:
        camp = OutreachCampaign(
            name=payload.get("name", "Untitled"),
            url_to_promote=payload.get("url_to_promote"),
            target_keywords=payload.get("target_keywords"),
            prospect_type=payload.get("prospect_type"),
            email_tone=payload.get("email_tone"),
            status="Active"
        )
        s.add(camp); s.commit(); s.refresh(camp)
    return {"status":"ok","campaign_id": camp.id}

@app.get("/backlinkapi/campaigns/metrics")
def campaign_metrics():
    # Return series for the chart
    return {
        "series": {
            "labels": ["Week 1","Week 2","Week 3","Week 4"],
            "open_rate": [65, 68, 72, 67],
            "reply_rate": [18, 21, 25, 23]
        },
        "totals": {"links_acquired": 12, "active_prospects": 156}
    }

# ---- AI Email Generation ----
from fastapi import Request

@app.post("/backlinkapi/emails/generate")
async def ai_generate_email(request: Request):
    # If no OpenAI client or key, fall back to the stubbed template
    api_key = os.getenv("OPENAI_API_KEY")
    use_openai = bool(api_key and OpenAI is not None)

    # Parse payload supporting both multipart/form-data and application/json
    var_dict: Dict[str, Any] = {}
    step: Optional[int] = None
    campaign_id: Optional[int] = None

    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        step_val = form.get("step")
        step = int(step_val) if step_val is not None and str(step_val).isdigit() else None
        cid = form.get("campaign_id")
        campaign_id = int(cid) if cid and str(cid).isdigit() else None
        variables_raw = form.get("variables")
        if variables_raw:
            try:
                var_dict = json.loads(variables_raw)
            except Exception:
                var_dict = {}
    else:
        try:
            body_json = await request.json()
            step = body_json.get("step")
            campaign_id = body_json.get("campaign_id")
            if isinstance(body_json.get("variables"), dict):
                var_dict.update(body_json.get("variables"))
        except Exception:
            pass

    if step is None:
        raise HTTPException(422, "Field 'step' is required and must be an integer.")

    # Defaults
    first_name = var_dict.get("first_name", "there")
    topic = var_dict.get("topic", "your industry")
    your_topic = var_dict.get("your_topic", "digital marketing")
    your_name = var_dict.get("your_name", "the team")

    subject = {
        1: f"Quick idea for your readers about {topic}",
        2: f"Following up on the {your_topic} guide",
        3: f"Final note about the {your_topic} resource"
    }.get(step, "Outreach message")

    # Default body (fallback)
    body = f"""Hi {first_name},

I found your recent article on {topic} really useful. I've put together a resource on {your_topic} that could add value to your audience.
Would you be open to a quick look?

Best,
{your_name}"""

    # Gather campaign context and previous emails (to inform step 2 and 3)
    campaign_ctx: Dict[str, Any] = {}
    previous_sequence_context = ""
    if campaign_id:
        try:
            with Session(engine) as s:
                camp = s.exec(select(OutreachCampaign).where(OutreachCampaign.id == campaign_id)).first()
                if camp:
                    campaign_ctx = {
                        "url_to_promote": camp.url_to_promote,
                        "target_keywords": camp.target_keywords,
                        "prospect_type": camp.prospect_type,
                        "email_tone": camp.email_tone,
                        "campaign_name": camp.name,
                    }
                if step and step in (2, 3):
                    prev = s.exec(
                        select(AIEmailOutput)
                        .where(AIEmailOutput.campaign_id == campaign_id)
                        .where(AIEmailOutput.step < step)
                        .order_by(AIEmailOutput.step.asc())
                    ).all()
                    if prev:
                        blocks = []
                        for p in prev:
                            blocks.append(
                                f"Step {p.step} Subject: {p.subject}\nStep {p.step} Body:\n{p.body}\n"
                            )
                        previous_sequence_context = "\n\n".join(blocks)
        except Exception:
            pass

    if use_openai:
        try:
            client = OpenAI(api_key=api_key)
            # Step-specific guidance
            url_to_promote = campaign_ctx.get("url_to_promote")
            email_tone = campaign_ctx.get("email_tone") or "friendly and professional"
            target_keywords = campaign_ctx.get("target_keywords")

            guidance_map = {
                1: (
                    "Step 1 (Initial Outreach): Introduce yourself briefly, reference their work on the topic, "
                    "share why your resource could help their audience, and include a soft, low-friction CTA to take a look. "
                    "Aim for 90-130 words."
                ),
                2: (
                    "Step 2 (Follow-up): Politely follow up on the initial outreach. Acknowledge they may be busy, "
                    "briefly restate the value, and optionally add one small, new angle or proof point. "
                    "Do not repeat the first email verbatim. Aim for 60-110 words."
                ),
                3: (
                    "Step 3 (Final Touch): Be concise and respectful. Signal this is the last email, "
                    "give permission to say no, and keep a helpful tone with a lightweight CTA. "
                    "Aim for 40-80 words."
                ),
            }

            context_lines = [
                f"First name: {first_name}",
                f"Topic: {topic}",
                f"Your topic: {your_topic}",
            ]
            if url_to_promote:
                context_lines.append(f"URL to mention (if natural): {url_to_promote}")
            if target_keywords:
                context_lines.append(f"Target keywords (optional context): {target_keywords}")
            context_lines.append(f"Tone: {email_tone}")
            if previous_sequence_context:
                context_lines.append("Previous emails in sequence (for context, do not duplicate):\n" + previous_sequence_context)

            prompt = (
                f"Write the body of an outreach email for step {step} in a 3-step sequence.\n"
                f"{guidance_map.get(step, '')}\n\n"
                + "\n".join(context_lines)
                + "\n\nConstraints:\n- Keep it in plain text.\n- No signatures beyond the sender's name.\n- No markdown.\n- Keep line length reasonable."
            )
            # Chat Completions API (OpenAI SDK v1)
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful outreach copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            if resp and resp.choices and resp.choices[0].message and resp.choices[0].message.content:
                body = resp.choices[0].message.content.strip()
        except Exception as e:
            # keep fallback body on any failure
            pass

    with Session(engine) as s:
        rec = AIEmailOutput(campaign_id=campaign_id, step=step, subject=subject, body=body)
        s.add(rec); s.commit(); s.refresh(rec)
    return {"subject": subject, "body": body, "id": rec.id}

# ---- Get individual backlink details ----
@app.get("/backlinkapi/backlinks/{backlink_id}")
def get_backlink(backlink_id: int):
    with Session(engine) as s:
        backlink = s.exec(select(Backlink).where(Backlink.id == backlink_id)).first()
        if not backlink:
            raise HTTPException(404, "Backlink not found")
        return backlink

# ---- Get backlinks with filtering ----
@app.get("/backlinkapi/backlinks")
def get_backlinks(
    risk_level: Optional[str] = None,
    min_da: Optional[int] = None,
    max_da: Optional[int] = None,
    link_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    with Session(engine) as s:
        query = select(Backlink)
        
        if risk_level:
            query = query.where(Backlink.risk_level == risk_level)
        if min_da is not None:
            query = query.where(Backlink.domain_authority >= min_da)
        if max_da is not None:
            query = query.where(Backlink.domain_authority <= max_da)
        if link_type:
            query = query.where(Backlink.link_type == link_type)
            
        query = query.offset(offset).limit(limit)
        backlinks = s.exec(query).all()
        
        return {
            "backlinks": backlinks,
            "total": len(backlinks),
            "limit": limit,
            "offset": offset
        }

# ---- Export (CSV / JSON) ----
@app.get("/backlinkapi/export/backlinks.csv")
def export_backlinks_csv():
    with Session(engine) as s:
        rows = s.exec(select(Backlink)).all()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["backlink_source","source_domain","anchor_text","target_url","domain_authority","nofollow","date_found","link_type","risk_level"])
    for r in rows:
        writer.writerow([r.backlink_source, r.source_domain, r.anchor_text, r.target_url, r.domain_authority, r.nofollow, r.date_found, r.link_type, r.risk_level])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue().encode("utf-8")]),
                             media_type="text/csv",
                             headers={"Content-Disposition":"attachment; filename=backlinks.csv"})

# ---- Export GSC Analysis Results ----
@app.get("/backlinkapi/export/gsc-analysis/{analysis_id}.csv")
def export_gsc_analysis_csv(analysis_id: int):
    """Export GSC analysis results to CSV"""
    with Session(engine) as s:
        analysis = s.exec(select(GSCAnalysis).where(GSCAnalysis.id == analysis_id)).first()
        if not analysis:
            raise HTTPException(404, "Analysis not found")
        
        try:
            data = json.loads(analysis.data_json) if analysis.data_json else {}
        except:
            raise HTTPException(500, "Invalid analysis data")
    
    out = io.StringIO()
    writer = csv.writer(out)
    
    # Export top queries
    top_queries = data.get("top_queries", [])
    if top_queries:
        writer.writerow(["Query", "Clicks", "Impressions", "CTR", "Position"])
        for query_data in top_queries:
            keys = query_data.get("keys", [""])
            query = keys[0] if keys else ""
            writer.writerow([
                query,
                query_data.get("clicks", 0),
                query_data.get("impressions", 0),
                f"{query_data.get('ctr', 0) * 100:.2f}%",
                f"{query_data.get('position', 0):.1f}"
            ])
    
    out.seek(0)
    return StreamingResponse(
        iter([out.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=gsc-analysis-{analysis_id}.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8882)