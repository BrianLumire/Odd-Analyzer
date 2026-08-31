import csv
import os
import json
import sys
import math
from collections import defaultdict

# (We keep WeekDetector import but won't use it for odds matching)
from time_detection import WeekDetector

def analyze_league(league_name="English", min_weeks=18):
    standings_file = f"standings_{league_name}.csv"
    results_file = f"results_{league_name}.csv"
    odds_file = f"odds_{league_name}.csv"

    if not os.path.exists(standings_file):
        return {"error": f"No standings file for {league_name}"}

    # --- Read standings ---
    with open(standings_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        standings = list(reader)

    # --- Find best season (most weeks) ---
    season_weeks = {}
    season_data = defaultdict(list)
    for row in standings:
        sid = row['Season_ID']
        played = int(row['Played'])
        if played >= min_weeks:
            season_data[sid].append(row)
            if sid not in season_weeks or played > season_weeks[sid]:
                season_weeks[sid] = played

    if not season_weeks:
        return {"error": f"No season with >= {min_weeks} weeks for {league_name}"}

    best_sid = max(season_weeks, key=season_weeks.get)
    best_weeks = season_weeks[best_sid]
    season_rows = season_data[best_sid]
    print(f"📋 Using Season {best_sid} ({best_weeks} weeks)", file=sys.stderr)

    # --- Load results for this season ---
    results_season = []
    if os.path.exists(results_file):
        with open(results_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Season_ID'] == best_sid:
                    results_season.append(row)

    # --- Build team stats from standings ---
    team_stats = {}
    for row in season_rows:
        team = row['Team']
        gf = int(row['Goals_For'])
        ga = int(row['Goals_Against'])
        played = int(row['Played'])
        gd = gf - ga
        team_stats[team] = {
            "gf": gf,
            "ga": ga,
            "gd": gd,
            "played": played,
            "avg_gf": gf / played,
            "avg_ga": ga / played,
            "avg_total": (gf + ga) / played
        }

    # --- Calculate Over 1.5 Hit Rate and Consistency per team ---
    hit_rates = {}
    consistency = {}
    team_totals = defaultdict(list)

    for row in results_season:
        home = row['Home_Team']
        away = row['Away_Team']
        total = int(row['Home_Score']) + int(row['Away_Score'])
        week = int(row['Week'])
        if week < min_weeks:
            continue
        for team in [home, away]:
            team_totals[team].append(total)

    for team, totals in team_totals.items():
        if not totals:
            continue
        over_count = sum(1 for t in totals if t >= 2)
        hit_rates[team] = over_count / len(totals)
        if len(totals) > 1:
            mean = sum(totals) / len(totals)
            variance = sum((x - mean) ** 2 for x in totals) / len(totals)
            std_dev = math.sqrt(variance)
            consistency[team] = max(0, 1 - (std_dev / 2.5))
        else:
            consistency[team] = 0.5

    # --- Combine into team info ---
    team_info = []
    for team, stats in team_stats.items():
        if team not in hit_rates:
            hit_rates[team] = 0
        if team not in consistency:
            consistency[team] = 0.5
        score = (
            (hit_rates[team] * 0.35) +
            (stats["avg_total"] * 0.25) +
            (stats["avg_ga"] * 0.15) +
            (stats["avg_gf"] * 0.10) +
            (consistency[team] * 0.15)
        )
        team_info.append({
            "team": team,
            "gf": stats["gf"],
            "ga": stats["ga"],
            "gd": stats["gd"],
            "played": stats["played"],
            "avg_gf": round(stats["avg_gf"], 2),
            "avg_ga": round(stats["avg_ga"], 2),
            "avg_total": round(stats["avg_total"], 2),
            "hit_rate": round(hit_rates[team] * 100, 1),
            "consistency": round(consistency[team], 3),
            "score": round(score, 3)
        })

    # --- Sort by GD ascending (worst GD = bottom) ---
    team_info.sort(key=lambda x: x["gd"])
    total_teams = len(team_info)
    bottom_count = total_teams // 2
    bottom_teams = team_info[:bottom_count]

    # --- Sort bottom by score descending ---
    bottom_teams.sort(key=lambda x: x["score"], reverse=True)
    top_four = bottom_teams[:4]

    if not top_four:
        return {"error": "No bottom-half teams found"}

    # --- Attach matches (Week >= min_weeks) to each target ---
    matches_data = {}
    for row in results_season:
        week = int(row['Week'])
        if week < min_weeks:
            continue
        home = row['Home_Team']
        away = row['Away_Team']
        total = int(row['Home_Score']) + int(row['Away_Score'])
        for team in [home, away]:
            if team not in matches_data:
                matches_data[team] = []
            matches_data[team].append({
                "week": week,
                "home": home,
                "away": away,
                "hs": int(row['Home_Score']),
                "aws": int(row['Away_Score']),
                "total": total,
                "over": total >= 2
            })
    for team in matches_data:
        matches_data[team].sort(key=lambda x: x["week"])

    # --- 🆕 Read odds – use the latest available week ---
    team_odds = {}
    target_week = None
    if os.path.exists(odds_file):
        with open(odds_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Find the maximum week in the file
            max_week = 0
            rows_by_week = {}
            for row in reader:
                week = int(row['week'])
                if week > max_week:
                    max_week = week
                rows_by_week.setdefault(week, []).append(row)
            
            if max_week > 0:
                target_week = max_week
                # Use the rows for that week
                for row in rows_by_week[target_week]:
                    home = row['home_team']
                    away = row['away_team']
                    odds = float(row['over1.5_odds'])
                    team_odds[home] = odds
                    team_odds[away] = odds
                print(f"📊 Loaded odds for {len(team_odds)} teams from week {target_week} (latest available)", file=sys.stderr)
            else:
                print(f"⚠️ No valid odds found in {odds_file}", file=sys.stderr)
    else:
        print(f"⚠️ Odds file not found – no odds attached.", file=sys.stderr)

    # --- Build output targets with odds and recommendation ---
    output_targets = []
    for t in top_four:
        team = t["team"]
        matches = matches_data.get(team, [])
        last_match = matches[-1] if matches else None
        cold_streak = False
        if last_match and not last_match["over"]:
            cold_streak = True

        # Attach odds if available
        odds = team_odds.get(team)
        if odds is not None:
            recommendation = "Bet" if (odds >= 1.15 and t["hit_rate"] >= 70) else "Skip"
        else:
            recommendation = "N/A"

        output_targets.append({
            "team": team,
            "avg_gf": t["avg_gf"],
            "avg_ga": t["avg_ga"],
            "avg_total": t["avg_total"],
            "hit_rate": t["hit_rate"],
            "score": t["score"],
            "played": t["played"],
            "gf": t["gf"],
            "ga": t["ga"],
            "matches": matches,
            "cold_streak": cold_streak,
            "last_match": last_match,
            "season_id": best_sid,
            "season_weeks": best_weeks,
            "current_odds": odds,
            "recommendation": recommendation
        })

    return {
        "league": league_name,
        "targets": output_targets,
        "top_target": output_targets[0] if len(output_targets) > 0 else None,
        "secondary_target": output_targets[1] if len(output_targets) > 1 else None,
        "third_target": output_targets[2] if len(output_targets) > 2 else None,
        "fourth_target": output_targets[3] if len(output_targets) > 3 else None,
        "season_id": best_sid,
        "season_weeks": best_weeks
    }

if __name__ == "__main__":
    import sys
    league = sys.argv[1] if len(sys.argv) > 1 else "English"
    result = analyze_league(league)
    print(json.dumps(result, indent=2))