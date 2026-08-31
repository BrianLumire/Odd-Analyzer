import sys
import io
import os
import re
import time
import csv
from datetime import datetime
from collections import defaultdict
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

def build_standings(league_display_name="EPL Betika", league_name="english", seasons=2):
    print(f"[START] Starting Betika Scraper (Wrapper + Fixtures + Results)")
    print(f"📊 Target League: {league_display_name}")
    print(f"📊 Seasons: {seasons}")
    print(f"📁 Files: results_{league_name}.csv, standings_{league_name}.csv")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        # --- STEP 1: Load Betika wrapper ---
        url = "https://www.betika.com/en-ke/virtual/english_league"
        print(f"🌐 Navigating to Betika wrapper: {url}")
        page.goto(url, timeout=60000)
        page.wait_for_load_state("load", timeout=60000)
        time.sleep(3)
        
        # --- STEP 2: Switch to iframe ---
        print("🔍 Searching for VirtusTec iframe...")
        target_frame = None
        for f in page.frames:
            if "virtustec" in str(f.url).lower():
                target_frame = f
                print(f"✅ Found VirtusTec frame")
                break
        if not target_frame:
            print("❌ No iframe found. Exiting.")
            browser.close()
            return
        page = target_frame
        print("⏳ Inside VirtusTec frame...")
        time.sleep(2)
        
        # --- STEP 3: Click sidebar league tab ---
        print(f"🔍 Clicking sidebar league tab: '{league_display_name}'...")
        try:
            tab_link = page.locator(f"ul.nav a[title='{league_display_name}']").first
            tab_link.wait_for(state="visible", timeout=10000)
            tab_link.scroll_into_view_if_needed()
            tab_link.click()
            print(f"✅ Clicked sidebar tab '{league_display_name}'. (Fixtures view)")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error clicking sidebar tab: {e}")
            browser.close()
            return
        
        # --- STEP 4: Capture reference ---
        print("📌 Capturing reference from Fixtures...")
        try:
            print(f"🔄 Reloading fixtures...")
            tab_link = page.locator(f"ul.nav a[title='{league_display_name}']").first
            tab_link.click()
            print(f"⏳ Waiting for fixtures to show '{league_display_name}'...")
            page.wait_for_function(
                f"""
                () => {{
                    const headers = document.querySelectorAll('app-market-header');
                    if (headers.length === 0) return false;
                    const desc = headers[0].querySelector('.event-description');
                    if (!desc) return false;
                    return desc.innerText.includes('{league_display_name}');
                }}
                """,
                timeout=15000
            )
            print(f"✅ Fixtures updated to '{league_display_name}'.")
            time.sleep(1)
            
            header = page.locator("app-market-header").first
            week_element = header.locator(".event-block-id").first
            week_text = week_element.inner_text().strip()
            week_match = re.search(r'Week\s+(\d+)', week_text, re.IGNORECASE)
            if week_match:
                current_week = int(week_match.group(1))
                print(f"📌 Week: {current_week}")
            else:
                print(f"⚠️ Could not parse week from: '{week_text}'")
                current_week = None
            
            timer_element = header.locator("app-countdown span").first
            timer_text = timer_element.inner_text().strip()
            print(f"📌 Countdown: {timer_text}")
            
            if current_week is not None and timer_text:
                from time_detection import WeekDetector
                detector = WeekDetector()
                detector.capture_reference(league_name, current_week, timer_text)
                print(f"✅ Reference captured: Week {current_week}, countdown {timer_text}")
        except Exception as e:
            print(f"⚠️ Could not capture reference: {e}")
            current_week = None
        
        # --- STEP 5: Scrape Over 1.5 odds from fixtures (CORRECTED week extraction) ---
        print("📊 Scraping Over 1.5 odds from fixtures...")
        try:
            # Click Over/Under tab
            ou_tab = page.locator("div.menu div.item[title='Over/Under']").first
            if ou_tab.count() > 0:
                ou_tab.click()
                print("   ✅ Switched to Over/Under tab")
                time.sleep(2)
            else:
                print("   ⚠️ Could not find Over/Under tab")
                ou_tab = None
            
            # Get all fixture rows (they contain both match info and odds)
            fixture_rows = page.locator("div.market-table-row").all()
            print(f"   Found {len(fixture_rows)} fixture rows")
            
            matched_odds = []
            match_id_pattern = re.compile(r'detail/(\d+)')
            odds_id_pattern = re.compile(r'ebid\d+-(\d+)')
            
            for row in fixture_rows:
                try:
                    # --- FIX: Find the correct week for this row ---
                    # Get the closest preceding app-market-header (which contains the week number)
                    week_header = row.locator("xpath=preceding::app-market-header[1]").first
                    week_num = None
                    if week_header.count() > 0:
                        week_text = week_header.locator(".event-block-id").inner_text().strip()
                        week_match = re.search(r'Week\s+(\d+)', week_text, re.IGNORECASE)
                        if week_match:
                            week_num = int(week_match.group(1))
                    
                    # Fallback: if no preceding header found, use the captured current_week
                    if week_num is None:
                        week_num = current_week
                    
                    # --- Extract match ID from the fixture row ---
                    match_cell = row.locator("app-match-cell a").first
                    if match_cell.count() == 0:
                        continue
                    href = match_cell.get_attribute("href") or ""
                    match_id_match = match_id_pattern.search(href)
                    if not match_id_match:
                        continue
                    match_id = match_id_match.group(1)
                    
                    # --- Extract home and away teams ---
                    home_elem = row.locator(".team-name--strong, .teamA").first
                    away_elem = row.locator(".team-name:not(.team-name--strong), .teamB").first
                    if home_elem.count() == 0 or away_elem.count() == 0:
                        continue
                    home = home_elem.inner_text().strip()
                    away = away_elem.inner_text().strip()
                    if not home or not away:
                        continue
                    
                    # --- Find the OV 1.5 odds within this row ---
                    odd_elements = row.locator("app-odd").all()
                    for odd in odd_elements:
                        cell = odd.locator(".odd.market-cell")
                        if cell.count() == 0:
                            continue
                        cell_id = cell.get_attribute("id") or ""
                        title = cell.get_attribute("title") or ""
                        if "Over 1.5" not in title:
                            continue
                        odd_match = odds_id_pattern.search(cell_id)
                        if not odd_match:
                            continue
                        odd_id = odd_match.group(1)
                        if odd_id == match_id:
                            value_elem = odd.locator(".odd-value")
                            if value_elem.count() == 0:
                                continue
                            odd_value = value_elem.inner_text().strip()
                            if not odd_value:
                                continue
                            matched_odds.append({
                                "week": week_num,
                                "match_id": match_id,
                                "home_team": home,
                                "away_team": away,
                                "over1.5_odds": float(odd_value)
                            })
                            break
                except Exception as e:
                    continue
            
            print(f"   Matched {len(matched_odds)} odds with fixtures")
            
            if matched_odds:
                odds_file = f"odds_{league_name}.csv"
                file_exists = os.path.isfile(odds_file)
                
                with open(odds_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["week", "match_id", "home_team", "away_team", "over1.5_odds"])
                    for m in matched_odds:
                        writer.writerow([
                            m["week"],
                            m["match_id"],
                            m["home_team"],
                            m["away_team"],
                            m["over1.5_odds"]
                        ])
                
                print(f"   ✅ Saved {len(matched_odds)} odds to {odds_file}")
                
                combined_file = "odds_all.csv"
                combined_exists = os.path.isfile(combined_file)
                with open(combined_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not combined_exists:
                        writer.writerow(["league", "week", "match_id", "home_team", "away_team", "over1.5_odds"])
                    for m in matched_odds:
                        writer.writerow([
                            league_name,
                            m["week"],
                            m["match_id"],
                            m["home_team"],
                            m["away_team"],
                            m["over1.5_odds"]
                        ])
            else:
                print("   ⚠️ No odds could be matched with fixtures.")
        except Exception as e:
            print(f"   ⚠️ Error scraping odds: {e}")
        
        # --- STEP 6: Switch to Results History ---
        print("🔍 Switching to Results History...")
        try:
            history_link = page.locator("ul.nav a[title='Results History']").first
            history_link.wait_for(state="visible", timeout=5000)
            history_link.scroll_into_view_if_needed()
            history_link.click()
            print("✅ Clicked Results History in sidebar.")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Could not click Results History: {e}")
            try:
                history_link = page.locator("text=Results History").first
                history_link.scroll_into_view_if_needed()
                history_link.click()
                print("✅ Clicked Results History (fallback).")
                time.sleep(3)
            except:
                print("❌ Could not switch to Results History. Exiting.")
                browser.close()
                return
        
        # --- STEP 7: Click horizontal league tab ---
        print(f"🔍 Searching for horizontal league tab: '{league_display_name}'...")
        try:
            page.wait_for_selector("div.menu", timeout=15000)
            tab = page.locator(f"div.menu div.item[title='{league_display_name}']").first
            tab.scroll_into_view_if_needed()
            tab.click()
            print(f"✅ Clicked horizontal '{league_display_name}' tab.")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error clicking horizontal tab: {e}")
            browser.close()
            return
        
        # --- STEP 8: Wait for Results ---
        try:
            page.wait_for_selector("div.panel-heading:has-text('Week')", timeout=30000)
            print("✅ Results history loaded successfully.")
        except:
            print("⚠️ No results found.")
            browser.close()
            return
        
        # --- STEP 9: Scraping loop (unchanged) ---
        all_weeks = []
        scraped_week_numbers = set()
        seen_match_ids = set()
        
        pattern_header = re.compile(r'Week\s+(\d+)', re.IGNORECASE)
        pattern_match_id = re.compile(r'#(\d+)')
        pattern_score = re.compile(r'([A-Z]{2,4})\s+(\d+)\s*[:–-]\s*(\d+)\s+([A-Z]{2,4})')
        
        target_weeks = seasons * 38
        weeks_collected = 0
        max_clicks = 30
        stall_counter = 0
        previous_collected = 0
        
        while weeks_collected < target_weeks and max_clicks > 0:
            week_headers = page.locator("div.panel-heading:has-text('Week')").all()
            print(f"   Found {len(week_headers)} week headers.")
            
            for header in week_headers:
                try:
                    container = header.locator("xpath=..")
                    match_rows = container.locator("text=/[A-Z]{2,4}\\s+\\d+\\s*[:–-]\\s*\\d+\\s+[A-Z]{2,4}/").all()
                    if not match_rows:
                        continue
                    
                    header_text = header.inner_text().strip()
                    week_match = pattern_header.search(header_text)
                    if not week_match:
                        continue
                    week_num = int(week_match.group(1))
                    
                    if week_num in scraped_week_numbers:
                        continue
                    
                    matches_this_week = []
                    for row in match_rows:
                        try:
                            row_text = ' '.join(row.inner_text().split())
                            score_match = pattern_score.search(row_text)
                            if not score_match:
                                continue
                            home = score_match.group(1)
                            hs = int(score_match.group(2))
                            aws = int(score_match.group(3))
                            away = score_match.group(4)
                            
                            match_id_match = pattern_match_id.search(row_text)
                            match_id = match_id_match.group(1) if match_id_match else None
                            if match_id and match_id in seen_match_ids:
                                continue
                            if match_id:
                                seen_match_ids.add(match_id)
                            
                            matches_this_week.append({
                                "home": home,
                                "hs": hs,
                                "aws": aws,
                                "away": away,
                                "match_id": match_id
                            })
                        except Exception as e:
                            continue
                    
                    if matches_this_week:
                        all_weeks.append({
                            "week": week_num,
                            "matches": matches_this_week
                        })
                        scraped_week_numbers.add(week_num)
                        weeks_collected += 1
                        print(f"   ✅ Week {week_num} ({len(matches_this_week)} matches) - Total: {weeks_collected}/{target_weeks}")
                except Exception as e:
                    continue
            
            if weeks_collected == previous_collected:
                stall_counter += 1
                if stall_counter >= 3:
                    print("🛑 No new weeks loading. Stopping.")
                    break
            else:
                stall_counter = 0
                previous_collected = weeks_collected
            
            if weeks_collected >= target_weeks:
                print(f"🎯 Target reached.")
                break
            
            load_button = page.locator("button:has-text('Load more events')")
            if load_button.count() == 0 or not load_button.is_visible():
                print("✅ No more 'Load more' button.")
                break
            
            print(f"🔄 Clicking 'Load more events'...")
            try:
                load_button.click(timeout=5000)
            except:
                break
            max_clicks -= 1
            time.sleep(5)
        
        browser.close()
        
        # --- STEP 10: Season splitting ---
        print(f"\n📊 Processing {len(all_weeks)} unique weeks...")
        if len(all_weeks) == 0:
            print("❌ No data scraped.")
            return
        
        has_week_1 = any(w["week"] == 1 for w in all_weeks)
        seasons_data = []
        current_season_weeks = []
        
        if has_week_1:
            for week_data in all_weeks:
                current_season_weeks.append(week_data)
                if week_data["week"] == 1:
                    max_week_in_season = max([w["week"] for w in current_season_weeks])
                    seasons_data.append({
                        "weeks": current_season_weeks.copy(),
                        "max_week": max_week_in_season
                    })
                    current_season_weeks = []
            if current_season_weeks:
                max_week_in_season = max([w["week"] for w in current_season_weeks])
                seasons_data.append({
                    "weeks": current_season_weeks.copy(),
                    "max_week": max_week_in_season
                })
        else:
            max_week = max([w["week"] for w in all_weeks])
            seasons_data.append({
                "weeks": all_weeks.copy(),
                "max_week": max_week
            })
            print(f"   ℹ️ No 'Week 1' found. Treating all as one incomplete season.")
        
        seasons_data = list(reversed(seasons_data))
        
        for idx, season in enumerate(seasons_data):
            season["season_number"] = idx + 1
            week_numbers = [w["week"] for w in season["weeks"]]
            expected_weeks = set(range(1, season["max_week"] + 1))
            actual_weeks = set(week_numbers)
            season["is_complete"] = (expected_weeks == actual_weeks)
            if season["is_complete"]:
                season["status"] = f"Complete ({season['max_week']} weeks)"
            else:
                season["status"] = f"Incomplete ({len(week_numbers)}/{season['max_week']} weeks)"
        
        seasons_data = seasons_data[:seasons]
        
        # --- STEP 11: Save CSVs ---
        results_file = f"results_{league_name}.csv"
        standings_file = f"standings_{league_name}.csv"
        
        print(f"\n📁 Saving results to '{results_file}'...")
        with open(results_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Season_ID", "Season_Status", "Week", "Match_ID", "Home_Team", "Home_Score", "Away_Score", "Away_Team"])
            for season in seasons_data:
                for week_data in season["weeks"]:
                    for match in week_data["matches"]:
                        writer.writerow([
                            season["season_number"],
                            "Complete" if season["is_complete"] else "Incomplete",
                            week_data["week"],
                            match.get("match_id", ""),
                            match["home"],
                            match["hs"],
                            match["aws"],
                            match["away"]
                        ])
        
        print(f"📁 Saving standings to '{standings_file}'...")
        with open(standings_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Season_ID", "Season_Status", "League_Weeks", "Team", "Played", "Goals_For", "Goals_Against", "Goal_Difference"])
            for season in seasons_data:
                stats = defaultdict(lambda: {"GF": 0, "GA": 0, "played": 0})
                for week_data in season["weeks"]:
                    for match in week_data["matches"]:
                        home, hs, aws, away = match["home"], match["hs"], match["aws"], match["away"]
                        stats[home]["GF"] += hs
                        stats[home]["GA"] += aws
                        stats[home]["played"] += 1
                        stats[away]["GF"] += aws
                        stats[away]["GA"] += hs
                        stats[away]["played"] += 1
                sorted_teams = sorted(stats.items(), key=lambda x: (x[1]["GF"] - x[1]["GA"]), reverse=True)
                for team, s in sorted_teams:
                    writer.writerow([
                        season["season_number"],
                        "Complete" if season["is_complete"] else "Incomplete",
                        season["max_week"],
                        team,
                        s["played"],
                        s["GF"],
                        s["GA"],
                        s["GF"] - s["GA"]
                    ])
        
        print("\n" + "="*60)
        print("📊 SCRAPE SUMMARY")
        print("="*60)
        print(f"League: {league_display_name} ({league_name})")
        print(f"Total seasons captured: {len(seasons_data)}")
        for season in seasons_data:
            print(f"  - Season {season['season_number']}: {season['status']}")
        print(f"\n✅ Results saved to: {results_file}")
        print(f"✅ Standings saved to: {standings_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="EPL Betika", help="League tab title (EPL Betika, Spain, Italy, Germany, Kenya)")
    parser.add_argument("--name", default="English", help="File prefix")
    parser.add_argument("--seasons", type=int, default=2, help="Number of seasons")
    args = parser.parse_args()
    
    build_standings(
        league_display_name=args.league,
        league_name=args.name,
        seasons=args.seasons
    )