"""
Sports Data Ingestion Function
Collects sports data from various APIs and stores in Cosmos DB.
Triggered by HTTP requests or scheduled execution.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import azure.functions as func
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import cosmos_client, config, APIClient, DataValidator


class SportsDataIngester:
    """Handles ingestion of sports data from multiple sources."""
    
    def __init__(self):
        self.api_clients = {}
        self.data_validator = DataValidator()
    
    async def initialize_api_clients(self):
        """Initialize API clients for different sports data providers."""
        # ESPN API (free tier)
        self.api_clients['espn'] = APIClient("https://site.api.espn.com/apis/site/v2/sports")
        
        # Sports data.io (requires API key)
        sports_api_key = config.get_secret("sports-api-key") or config.sports_api_key
        if sports_api_key:
            self.api_clients['sportsdata'] = APIClient(
                "https://api.sportsdata.io",
                api_key=sports_api_key
            )
    
    async def fetch_nfl_games(self, season: str = None, week: int = None) -> List[Dict[str, Any]]:
        """Fetch NFL games from ESPN API."""
        try:
            if not season:
                season = str(datetime.now().year)
            
            endpoint = f"football/nfl/scoreboard"
            params = {"dates": datetime.now().strftime("%Y%m%d")}
            
            if week:
                params["week"] = week
            
            data = await self.api_clients['espn'].get(endpoint, params=params)
            
            games = []
            for event in data.get("events", []):
                game_data = self._parse_espn_game(event, "nfl", season)
                if self.data_validator.validate_game_data(game_data):
                    games.append(game_data)
            
            logging.info(f"Fetched {len(games)} NFL games")
            return games
            
        except Exception as e:
            logging.error(f"Error fetching NFL games: {e}")
            return []
    
    async def fetch_nba_games(self, season: str = None) -> List[Dict[str, Any]]:
        """Fetch NBA games from ESPN API."""
        try:
            if not season:
                season = f"{datetime.now().year - 1}-{str(datetime.now().year)[2:]}"
            
            endpoint = f"basketball/nba/scoreboard"
            params = {"dates": datetime.now().strftime("%Y%m%d")}
            
            data = await self.api_clients['espn'].get(endpoint, params=params)
            
            games = []
            for event in data.get("events", []):
                game_data = self._parse_espn_game(event, "nba", season)
                if self.data_validator.validate_game_data(game_data):
                    games.append(game_data)
            
            logging.info(f"Fetched {len(games)} NBA games")
            return games
            
        except Exception as e:
            logging.error(f"Error fetching NBA games: {e}")
            return []
    
    def _parse_espn_game(self, event: Dict[str, Any], sport: str, season: str) -> Dict[str, Any]:
        """Parse ESPN API game data into our standardized format."""
        try:
            # Extract basic game information
            game_id = event.get("id", "")
            status = event.get("status", {})
            
            # Parse teams
            competitions = event.get("competitions", [{}])
            if not competitions:
                return {}
            
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            
            if len(competitors) < 2:
                return {}
            
            # Determine home and away teams
            home_team = None
            away_team = None
            
            for competitor in competitors:
                team_data = competitor.get("team", {})
                if competitor.get("homeAway") == "home":
                    home_team = self._parse_espn_team(team_data, sport)
                else:
                    away_team = self._parse_espn_team(team_data, sport)
            
            if not home_team or not away_team:
                return {}
            
            # Parse scores
            home_score = None
            away_score = None
            
            for competitor in competitors:
                score = self.data_validator.normalize_score(competitor.get("score"))
                if competitor.get("homeAway") == "home":
                    home_score = score
                else:
                    away_score = score
            
            # Parse game status
            game_status = "scheduled"
            if status.get("type", {}).get("completed"):
                game_status = "completed"
            elif status.get("type", {}).get("state") == "in":
                game_status = "in_progress"
            
            # Parse date
            date_str = event.get("date", "")
            scheduled_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.utcnow()
            
            # Parse venue
            venue = competition.get("venue", {}).get("fullName", "")
            
            return {
                "id": f"{sport}_{game_id}",
                "sport": sport,
                "home_team": home_team,
                "away_team": away_team,
                "scheduled_date": scheduled_date.isoformat(),
                "status": game_status,
                "score": {
                    "home_score": home_score,
                    "away_score": away_score,
                    "period_scores": [],
                    "current_period": None
                },
                "season": season,
                "week": competition.get("week", {}).get("number"),
                "venue": venue,
                "weather": None,
                "officials": [],
                "metadata": {
                    "source": "espn",
                    "raw_data": event
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error parsing ESPN game data: {e}")
            return {}
    
    def _parse_espn_team(self, team_data: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """Parse ESPN team data into our standardized format."""
        return {
            "id": f"{sport}_{team_data.get('id', '')}",
            "name": self.data_validator.clean_team_name(team_data.get("displayName", "")),
            "city": self.data_validator.clean_team_name(team_data.get("location", "")),
            "abbreviation": team_data.get("abbreviation", ""),
            "sport": sport,
            "conference": None,
            "metadata": {
                "logo": team_data.get("logo", ""),
                "color": team_data.get("color", ""),
                "alternateColor": team_data.get("alternateColor", "")
            }
        }
    
    async def store_games(self, games: List[Dict[str, Any]]) -> int:
        """Store games in Cosmos DB."""
        stored_count = 0
        
        try:
            for game in games:
                await cosmos_client.upsert_item("games", game)
                stored_count += 1
            
            logging.info(f"Successfully stored {stored_count} games")
            return stored_count
            
        except Exception as e:
            logging.error(f"Error storing games: {e}")
            return stored_count
    
    async def fetch_team_stats(self, sport: str, season: str) -> List[Dict[str, Any]]:
        """Fetch team statistics and store in Cosmos DB."""
        # This would typically fetch from a more comprehensive API
        # For now, we'll calculate basic stats from existing game data
        try:
            query = """
            SELECT * FROM c 
            WHERE c.sport = @sport 
            AND c.season = @season 
            AND c.status = 'completed'
            """
            
            parameters = [
                {"name": "@sport", "value": sport},
                {"name": "@season", "value": season}
            ]
            
            games = await cosmos_client.query_items("games", query, parameters)
            
            # Calculate team stats
            team_stats = {}
            for game in games:
                home_team_id = game["home_team"]["id"]
                away_team_id = game["away_team"]["id"]
                
                # Initialize team stats if not exists
                for team_id in [home_team_id, away_team_id]:
                    if team_id not in team_stats:
                        team_stats[team_id] = {
                            "team_id": team_id,
                            "season": season,
                            "games_played": 0,
                            "wins": 0,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 0,
                            "points_against": 0,
                            "home_record": {"games": 0, "wins": 0},
                            "away_record": {"games": 0, "wins": 0},
                            "recent_form": [],
                            "advanced_stats": {},
                            "updated_at": datetime.utcnow().isoformat()
                        }
                
                # Update stats based on game result
                home_score = game.get("score", {}).get("home_score", 0) or 0
                away_score = game.get("score", {}).get("away_score", 0) or 0
                
                # Home team stats
                team_stats[home_team_id]["games_played"] += 1
                team_stats[home_team_id]["points_for"] += home_score
                team_stats[home_team_id]["points_against"] += away_score
                team_stats[home_team_id]["home_record"]["games"] += 1
                
                if home_score > away_score:
                    team_stats[home_team_id]["wins"] += 1
                    team_stats[home_team_id]["home_record"]["wins"] += 1
                    team_stats[home_team_id]["recent_form"].append("W")
                    team_stats[away_team_id]["recent_form"].append("L")
                elif away_score > home_score:
                    team_stats[home_team_id]["losses"] += 1
                    team_stats[away_team_id]["recent_form"].append("W")
                else:
                    team_stats[home_team_id]["ties"] += 1
                    team_stats[away_team_id]["ties"] += 1
                    team_stats[home_team_id]["recent_form"].append("T")
                    team_stats[away_team_id]["recent_form"].append("T")
                
                # Away team stats
                team_stats[away_team_id]["games_played"] += 1
                team_stats[away_team_id]["points_for"] += away_score
                team_stats[away_team_id]["points_against"] += home_score
                team_stats[away_team_id]["away_record"]["games"] += 1
                
                if away_score > home_score:
                    team_stats[away_team_id]["wins"] += 1
                    team_stats[away_team_id]["away_record"]["wins"] += 1
                elif home_score > away_score:
                    team_stats[away_team_id]["losses"] += 1
            
            # Store team stats
            stored_stats = []
            for stats in team_stats.values():
                # Keep only last 10 games in recent form
                stats["recent_form"] = stats["recent_form"][-10:]
                await cosmos_client.upsert_item("team_stats", stats)
                stored_stats.append(stats)
            
            logging.info(f"Updated stats for {len(stored_stats)} teams")
            return stored_stats
            
        except Exception as e:
            logging.error(f"Error fetching team stats: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup API clients."""
        for client in self.api_clients.values():
            await client.close()


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main function entry point."""
    logging.info('Sports data ingestion function triggered.')
    
    ingester = SportsDataIngester()
    
    try:
        # Initialize API clients
        await ingester.initialize_api_clients()
        
        # Get request parameters
        sport = req.params.get('sport', 'nfl')
        season = req.params.get('season')
        week = req.params.get('week')
        
        # Convert week to int if provided
        if week:
            try:
                week = int(week)
            except ValueError:
                week = None
        
        results = {
            "status": "success",
            "games_ingested": 0,
            "teams_updated": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Fetch and store games based on sport
        if sport.lower() == 'nfl':
            games = await ingester.fetch_nfl_games(season, week)
            results["games_ingested"] = await ingester.store_games(games)
            
            # Update team stats
            if season:
                team_stats = await ingester.fetch_team_stats('nfl', season)
                results["teams_updated"] = len(team_stats)
        
        elif sport.lower() == 'nba':
            games = await ingester.fetch_nba_games(season)
            results["games_ingested"] = await ingester.store_games(games)
            
            # Update team stats
            if season:
                team_stats = await ingester.fetch_team_stats('nba', season)
                results["teams_updated"] = len(team_stats)
        
        else:
            results["status"] = "error"
            results["message"] = f"Sport '{sport}' not supported yet"
        
        await ingester.cleanup()
        
        return func.HttpResponse(
            json.dumps(results),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    
    except Exception as e:
        logging.error(f"Error in sports data ingestion: {e}")
        
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await ingester.cleanup()
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
