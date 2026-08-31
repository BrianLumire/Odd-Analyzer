from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os
from datetime import datetime
from time_detection import WeekDetector
from analyzer import analyze_league

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

week_detector = WeekDetector()

LEAGUES = ["English", "Spanish", "Italian", "German", "Kenyan"]

@app.get("/api/status")
def get_status():
    status = {}
    for league in LEAGUES:
        week_info = week_detector.get_current_week(league)
        last_scrape = None
        fname = f"standings_{league}.csv"
        if os.path.exists(fname):
            last_scrape = datetime.fromtimestamp(os.path.getmtime(fname)).isoformat()
        status[league] = {
            "current_week": week_info.get("current_week", "unknown"),
            "last_scrape": last_scrape
        }
    return {"leagues": status}

@app.post("/api/scrape")
def scrape_league(league: str = Query(..., description="League name: English, Spanish, Italian, German, Kenyan")):
    league_map = {
        "English": ("EPL Betika", "English"),
        "Spanish": ("Spain", "Spanish"),
        "Italian": ("Italy", "Italian"),
        "German": ("Germany", "German"),
        "Kenyan": ("Kenya", "Kenyan")
    }
    display_name, file_name = league_map.get(league, (league, league))
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "standings_builder.py")
    
    print(f"🔍 Running scraper: {script_path}")
    print(f"   League: {display_name}, Name: {file_name}, Seasons: 2")
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    try:
        result = subprocess.run(
            [
                "python3", script_path,   # <-- changed from "python" to "python3"
                "--league", display_name,
                "--name", file_name,
                "--seasons", "2"
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300,
            cwd=script_dir,
            env=env
        )
        
        print(f"📤 STDOUT: {result.stdout}")
        if result.stderr:
            print(f"📤 STDERR: {result.stderr}")
        
        analysis = analyze_league(file_name)
        with open(f"analysis_{file_name}.json", "w", encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "league": league,
            "output": result.stdout,
            "error": result.stderr,
            "analysis": analysis
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Scraper timed out after 300 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/analysis")
def get_analysis(league: str = Query(..., description="League name: English, Spanish, Italian, German, Kenyan")):
    try:
        with open(f"analysis_{league}.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"No analysis found for {league}"}
    except json.JSONDecodeError:
        return {"error": f"Analysis file for {league} is corrupted"}
    except Exception as e:
        return {"error": f"Error reading analysis: {str(e)}"}