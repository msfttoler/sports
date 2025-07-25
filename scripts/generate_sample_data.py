"""
Sample data generator for testing the Sports Prediction System.
Creates mock sports data for development and testing purposes.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4


class SampleDataGenerator:
    """Generate sample sports data for testing."""
    
    def __init__(self):
        self.sports = ["nfl", "nba"]
        self.current_year = datetime.now().year
        
        # Sample team data
        self.nfl_teams = [
            {"name": "Kansas City Chiefs", "city": "Kansas City", "abbr": "KC"},
            {"name": "Buffalo Bills", "city": "Buffalo", "abbr": "BUF"},
            {"name": "Miami Dolphins", "city": "Miami", "abbr": "MIA"},
            {"name": "Cincinnati Bengals", "city": "Cincinnati", "abbr": "CIN"},
            {"name": "Dallas Cowboys", "city": "Dallas", "abbr": "DAL"},
            {"name": "San Francisco 49ers", "city": "San Francisco", "abbr": "SF"},
            {"name": "Green Bay Packers", "city": "Green Bay", "abbr": "GB"},
            {"name": "Philadelphia Eagles", "city": "Philadelphia", "abbr": "PHI"}
        ]
        
        self.nba_teams = [
            {"name": "Lakers", "city": "Los Angeles", "abbr": "LAL"},
            {"name": "Warriors", "city": "Golden State", "abbr": "GSW"},
            {"name": "Celtics", "city": "Boston", "abbr": "BOS"},
            {"name": "Heat", "city": "Miami", "abbr": "MIA"},
            {"name": "Bulls", "city": "Chicago", "abbr": "CHI"},
            {"name": "Knicks", "city": "New York", "abbr": "NYK"},
            {"name": "Nets", "city": "Brooklyn", "abbr": "BRK"},
            {"name": "Nuggets", "city": "Denver", "abbr": "DEN"}
        ]
    
    def generate_teams(self, sport: str) -> List[Dict[str, Any]]:
        """Generate team objects for a sport."""
        teams = []
        
        if sport == "nfl":
            team_data = self.nfl_teams
        elif sport == "nba":
            team_data = self.nba_teams
        else:
            return []
        
        for i, team_info in enumerate(team_data):
            team = {
                "id": f"{sport}_{i+1}",
                "name": team_info["name"],
                "city": team_info["city"],
                "abbreviation": team_info["abbr"],
                "sport": sport,
                "conference": "AFC" if sport == "nfl" and i < 4 else "NFC" if sport == "nfl" else "Eastern" if i < 4 else "Western",
                "metadata": {
                    "founded": random.randint(1950, 2000),
                    "championships": random.randint(0, 5)
                }
            }
            teams.append(team)
        
        return teams
    
    def generate_games(self, sport: str, num_games: int = 20) -> List[Dict[str, Any]]:
        """Generate sample games for a sport."""
        teams = self.generate_teams(sport)
        games = []
        
        season = str(self.current_year) if sport == "nfl" else f"{self.current_year-1}-{str(self.current_year)[2:]}"
        
        for i in range(num_games):
            # Pick random teams
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t["id"] != home_team["id"]])
            
            # Generate game date (mix of past and future)
            days_offset = random.randint(-30, 30)
            game_date = datetime.now() + timedelta(days=days_offset)
            
            # Determine game status and scores
            if days_offset < -1:  # Past games
                status = "completed"
                home_score = random.randint(14, 35) if sport == "nfl" else random.randint(85, 125)
                away_score = random.randint(14, 35) if sport == "nfl" else random.randint(85, 125)
            elif days_offset <= 1:  # Recent or today
                status = random.choice(["in_progress", "completed"])
                home_score = random.randint(14, 35) if sport == "nfl" else random.randint(85, 125)
                away_score = random.randint(14, 35) if sport == "nfl" else random.randint(85, 125)
            else:  # Future games
                status = "scheduled"
                home_score = None
                away_score = None
            
            game = {
                "id": f"{sport}_game_{i+1}",
                "sport": sport,
                "home_team": home_team,
                "away_team": away_team,
                "scheduled_date": game_date.isoformat(),
                "status": status,
                "score": {
                    "home_score": home_score,
                    "away_score": away_score,
                    "period_scores": [],
                    "current_period": None
                },
                "season": season,
                "week": random.randint(1, 17) if sport == "nfl" else None,
                "venue": f"{home_team['city']} Stadium",
                "weather": None,
                "officials": [],
                "metadata": {
                    "source": "sample_data",
                    "attendance": random.randint(50000, 80000) if sport == "nfl" else random.randint(15000, 20000)
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            games.append(game)
        
        return games
    
    def generate_team_stats(self, sport: str) -> List[Dict[str, Any]]:
        """Generate sample team statistics."""
        teams = self.generate_teams(sport)
        team_stats = []
        
        season = str(self.current_year) if sport == "nfl" else f"{self.current_year-1}-{str(self.current_year)[2:]}"
        
        for team in teams:
            games_played = random.randint(10, 16) if sport == "nfl" else random.randint(60, 82)
            wins = random.randint(0, games_played)
            losses = games_played - wins
            
            # Generate realistic scoring based on sport
            if sport == "nfl":
                points_per_game = random.uniform(18, 30)
                points_allowed = random.uniform(18, 30)
            else:  # NBA
                points_per_game = random.uniform(100, 120)
                points_allowed = random.uniform(100, 120)
            
            stats = {
                "team_id": team["id"],
                "season": season,
                "games_played": games_played,
                "wins": wins,
                "losses": losses,
                "ties": 0,
                "points_for": round(points_per_game * games_played, 1),
                "points_against": round(points_allowed * games_played, 1),
                "home_record": {
                    "games": games_played // 2,
                    "wins": random.randint(0, games_played // 2)
                },
                "away_record": {
                    "games": games_played // 2,
                    "wins": random.randint(0, games_played // 2)
                },
                "recent_form": [random.choice(["W", "L"]) for _ in range(min(10, games_played))],
                "advanced_stats": {
                    "offensive_rating": round(random.uniform(90, 120), 1),
                    "defensive_rating": round(random.uniform(90, 120), 1),
                    "pace": round(random.uniform(95, 105), 1) if sport == "nba" else None
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            
            team_stats.append(stats)
        
        return team_stats
    
    def generate_predictions(self, sport: str, num_predictions: int = 10) -> List[Dict[str, Any]]:
        """Generate sample predictions."""
        predictions = []
        
        for i in range(num_predictions):
            game_id = f"{sport}_game_{i+1}"
            
            # Generate realistic confidence scores
            confidence = round(random.uniform(55, 85), 1)
            
            # Generate win probabilities
            home_prob = round(random.uniform(30, 70), 1)
            away_prob = round(100 - home_prob, 1)
            
            outcome = "home_win" if home_prob > away_prob else "away_win"
            
            # Generate score predictions
            if sport == "nfl":
                home_score = round(random.uniform(17, 28), 1)
                away_score = round(random.uniform(17, 28), 1)
            else:  # NBA
                home_score = round(random.uniform(105, 115), 1)
                away_score = round(random.uniform(105, 115), 1)
            
            prediction = {
                "id": f"pred_{game_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "game_id": game_id,
                "predicted_outcome": outcome,
                "confidence_score": confidence,
                "predicted_home_score": home_score,
                "predicted_away_score": away_score,
                "win_probability": {
                    "home": home_prob,
                    "away": away_prob
                },
                "model_version": "v1.0.0",
                "features_used": [
                    "home_win_percentage", "away_win_percentage",
                    "home_points_per_game", "away_points_per_game",
                    "home_recent_form", "away_recent_form",
                    "head_to_head_record"
                ],
                "prediction_reasoning": f"Model predicts {outcome.replace('_', ' ')} with {confidence}% confidence based on recent form and historical matchups.",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "source": "sample_data",
                    "model_accuracy": round(random.uniform(0.6, 0.7), 3)
                }
            }
            
            predictions.append(prediction)
        
        return predictions
    
    def generate_all_sample_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete sample dataset."""
        all_data = {
            "games": [],
            "team_stats": [],
            "predictions": []
        }
        
        for sport in self.sports:
            all_data["games"].extend(self.generate_games(sport, 20))
            all_data["team_stats"].extend(self.generate_team_stats(sport))
            all_data["predictions"].extend(self.generate_predictions(sport, 10))
        
        return all_data
    
    def save_sample_data(self, filename: str = "sample_data.json"):
        """Save sample data to JSON file."""
        data = self.generate_all_sample_data()
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Sample data saved to {filename}")
        print(f"Generated:")
        print(f"  - {len(data['games'])} games")
        print(f"  - {len(data['team_stats'])} team stat records")
        print(f"  - {len(data['predictions'])} predictions")


if __name__ == "__main__":
    # Generate and save sample data
    generator = SampleDataGenerator()
    generator.save_sample_data("scripts/sample_data.json")
    
    # Also generate individual files for easier testing
    for sport in ["nfl", "nba"]:
        data = {
            "games": generator.generate_games(sport, 10),
            "team_stats": generator.generate_team_stats(sport),
            "predictions": generator.generate_predictions(sport, 5)
        }
        
        with open(f"scripts/sample_{sport}_data.json", 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Sample {sport.upper()} data saved to scripts/sample_{sport}_data.json")
