import json
from datetime import datetime

INTERVAL_SECONDS = 120  # 2 minutes between virtual weeks
SEASON_WEEKS = 38

class WeekDetector:
    def __init__(self, state_file="week_state.json"):
        self.state_file = state_file
        self.state = self.load_state()
    
    def load_state(self):
        """Load the week state from file."""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_state(self):
        """Save the week state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def capture_reference(self, league, week, countdown_str):
        """
        Capture a reference point for a league.
        
        Args:
            league: League name (e.g., "Spanish")
            week: The week number displayed on the page
            countdown_str: Countdown timer string (e.g., "14:48" = 14 min 48 sec)
        """
        # Parse countdown (MM:SS)
        parts = countdown_str.split(':')
        countdown_seconds = int(parts[0]) * 60 + int(parts[1])
        
        self.state[league] = {
            "reference_week": week,
            "reference_timestamp": datetime.now().isoformat(),
            "countdown_seconds": countdown_seconds
        }
        self.save_state()
        print(f"📌 Captured reference for {league}: Week {week}, countdown {countdown_str}")
    
    def get_current_week(self, league):
        """
        Calculate the current week for a league based on its reference point.
        
        Returns:
            dict: {'league': league, 'current_week': week, 'weeks_passed': n}
            or {'error': 'No reference point for {league}'}
        """
        # Reload state from file every time (so we see updates without restarting)
        self.state = self.load_state()
        
        if league not in self.state:
            return {"error": f"No reference point for {league}"}
        
        ref = self.state[league]
        ref_time = datetime.fromisoformat(ref["reference_timestamp"])
        elapsed = (datetime.now() - ref_time).total_seconds()
        
        # The countdown tells us how many seconds until the week starts.
        # We add it so the elapsed time starts from the actual week start.
        elapsed_since_start = elapsed + ref["countdown_seconds"]
        
        intervals = elapsed_since_start / INTERVAL_SECONDS
        weeks_passed = int(intervals)
        
        # Map to 1-38 cycle
        current_week = ((ref["reference_week"] - 1 + weeks_passed) % SEASON_WEEKS) + 1
        
        return {
            "league": league,
            "current_week": current_week,
            "weeks_passed": weeks_passed
        }
    