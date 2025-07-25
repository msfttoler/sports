"""
Get Team Statistics API Endpoint
RESTful API to retrieve team statistics and performance data.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import azure.functions as func
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import cosmos_client


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get team statistics API endpoint.
    
    Query parameters:
    - team_id: Specific team ID
    - sport: Filter by sport (nfl, nba, mlb, nhl, soccer)
    - season: Filter by season
    - include_recent_games: Include recent game results (true/false)
    - limit: Maximum number of results (default: 20)
    """
    logging.info('Get team statistics API called.')
    
    try:
        # Parse query parameters
        team_id = req.params.get('team_id')
        sport = req.params.get('sport')
        season = req.params.get('season')
        include_recent_games = req.params.get('include_recent_games', 'false').lower() == 'true'
        limit = int(req.params.get('limit', 20))
        
        # Validate limit
        limit = min(limit, 100)  # Max 100 results
        
        team_stats = []
        
        if team_id:
            # Get specific team statistics
            stats = await get_team_statistics(team_id, season, include_recent_games)
            if stats:
                team_stats = [stats]
        else:
            # Get multiple team statistics
            team_stats = await get_multiple_team_statistics(sport, season, limit, include_recent_games)
        
        # Prepare response
        response_data = {
            "status": "success",
            "team_statistics": team_stats,
            "total_results": len(team_stats),
            "timestamp": datetime.utcnow().isoformat(),
            "filters_applied": {
                "team_id": team_id,
                "sport": sport,
                "season": season,
                "include_recent_games": include_recent_games
            }
        }
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
    
    except Exception as e:
        logging.error(f"Error in get team statistics API: {e}")
        
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


async def get_team_statistics(team_id: str, season: Optional[str] = None, include_recent_games: bool = False) -> Optional[Dict[str, Any]]:
    """Get statistics for a specific team."""
    try:
        # Build query for team stats
        query = "SELECT * FROM c WHERE c.team_id = @team_id"
        parameters = [{"name": "@team_id", "value": team_id}]
        
        if season:
            query += " AND c.season = @season"
            parameters.append({"name": "@season", "value": season})
        
        query += " ORDER BY c.updated_at DESC"
        
        stats_list = await cosmos_client.query_items("team_stats", query, parameters)
        
        if not stats_list:
            return None
        
        stats = stats_list[0]  # Get the most recent stats
        
        # Add computed metrics
        stats = add_computed_metrics(stats)
        
        # Add recent games if requested
        if include_recent_games:
            recent_games = await get_team_recent_games(team_id, 10)
            stats["recent_games"] = recent_games
        
        # Get team information
        team_info = await get_team_info(team_id)
        if team_info:
            stats["team_info"] = team_info
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting team statistics: {e}")
        return None


async def get_multiple_team_statistics(sport: Optional[str] = None, season: Optional[str] = None, 
                                     limit: int = 20, include_recent_games: bool = False) -> List[Dict[str, Any]]:
    """Get statistics for multiple teams."""
    try:
        # Build query
        query_parts = ["SELECT * FROM c WHERE 1=1"]
        parameters = []
        
        if season:
            query_parts.append("AND c.season = @season")
            parameters.append({"name": "@season", "value": season})
        
        query_parts.append("ORDER BY c.updated_at DESC")
        query_parts.append(f"OFFSET 0 LIMIT {limit}")
        
        query = " ".join(query_parts)
        
        stats_list = await cosmos_client.query_items("team_stats", query, parameters)
        
        # Filter by sport if needed (since sport is in team_id)
        if sport:
            stats_list = [stats for stats in stats_list if stats.get("team_id", "").startswith(sport)]
        
        # Add computed metrics and additional data
        enhanced_stats = []
        for stats in stats_list:
            stats = add_computed_metrics(stats)
            
            # Add team information
            team_info = await get_team_info(stats["team_id"])
            if team_info:
                stats["team_info"] = team_info
            
            # Add recent games if requested
            if include_recent_games:
                recent_games = await get_team_recent_games(stats["team_id"], 5)
                stats["recent_games"] = recent_games
            
            enhanced_stats.append(stats)
        
        return enhanced_stats
        
    except Exception as e:
        logging.error(f"Error getting multiple team statistics: {e}")
        return []


async def get_team_info(team_id: str) -> Optional[Dict[str, Any]]:
    """Get team information from games data."""
    try:
        # Query games to get team info
        query = """
        SELECT c.home_team FROM c 
        WHERE c.home_team.id = @team_id
        OFFSET 0 LIMIT 1
        """
        parameters = [{"name": "@team_id", "value": team_id}]
        
        games = await cosmos_client.query_items("games", query, parameters)
        
        if games:
            return games[0]["home_team"]
        
        # Try away team if not found as home team
        query = """
        SELECT c.away_team FROM c 
        WHERE c.away_team.id = @team_id
        OFFSET 0 LIMIT 1
        """
        
        games = await cosmos_client.query_items("games", query, parameters)
        
        if games:
            return games[0]["away_team"]
        
        return None
        
    except Exception as e:
        logging.error(f"Error getting team info: {e}")
        return None


async def get_team_recent_games(team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent games for a team."""
    try:
        query = """
        SELECT * FROM c 
        WHERE (c.home_team.id = @team_id OR c.away_team.id = @team_id)
        AND c.status = 'completed'
        ORDER BY c.scheduled_date DESC
        OFFSET 0 LIMIT @limit
        """
        parameters = [
            {"name": "@team_id", "value": team_id},
            {"name": "@limit", "value": limit}
        ]
        
        games = await cosmos_client.query_items("games", query, parameters)
        
        # Add result for each game
        for game in games:
            if game["home_team"]["id"] == team_id:
                home_score = game.get("score", {}).get("home_score", 0) or 0
                away_score = game.get("score", {}).get("away_score", 0) or 0
                game["result"] = "W" if home_score > away_score else "L" if away_score > home_score else "T"
                game["team_score"] = home_score
                game["opponent_score"] = away_score
                game["opponent"] = game["away_team"]
                game["home_away"] = "home"
            else:
                home_score = game.get("score", {}).get("home_score", 0) or 0
                away_score = game.get("score", {}).get("away_score", 0) or 0
                game["result"] = "W" if away_score > home_score else "L" if home_score > away_score else "T"
                game["team_score"] = away_score
                game["opponent_score"] = home_score
                game["opponent"] = game["home_team"]
                game["home_away"] = "away"
        
        return games
        
    except Exception as e:
        logging.error(f"Error getting recent games: {e}")
        return []


def add_computed_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed metrics to team statistics."""
    try:
        games_played = stats.get("games_played", 0)
        
        if games_played > 0:
            # Win percentage
            wins = stats.get("wins", 0)
            stats["win_percentage"] = round(wins / games_played, 3)
            
            # Points per game
            points_for = stats.get("points_for", 0)
            points_against = stats.get("points_against", 0)
            stats["points_per_game"] = round(points_for / games_played, 1)
            stats["points_allowed_per_game"] = round(points_against / games_played, 1)
            stats["point_differential"] = round((points_for - points_against) / games_played, 1)
            
            # Home/Away percentages
            home_record = stats.get("home_record", {})
            home_games = home_record.get("games", 0)
            if home_games > 0:
                stats["home_win_percentage"] = round(home_record.get("wins", 0) / home_games, 3)
            
            away_record = stats.get("away_record", {})
            away_games = away_record.get("games", 0)
            if away_games > 0:
                stats["away_win_percentage"] = round(away_record.get("wins", 0) / away_games, 3)
            
            # Recent form percentage
            recent_form = stats.get("recent_form", [])
            if recent_form:
                recent_wins = sum(1 for result in recent_form if result == "W")
                stats["recent_form_percentage"] = round(recent_wins / len(recent_form), 3)
        
        # Performance rating (simple calculation)
        win_pct = stats.get("win_percentage", 0)
        point_diff = stats.get("point_differential", 0)
        
        # Normalize point differential (assuming typical range is -20 to +20)
        normalized_diff = max(-1, min(1, point_diff / 20))
        
        # Combine win percentage (70%) and point differential (30%)
        performance_rating = round((win_pct * 0.7 + (normalized_diff + 1) / 2 * 0.3) * 100, 1)
        stats["performance_rating"] = performance_rating
        
        return stats
        
    except Exception as e:
        logging.error(f"Error adding computed metrics: {e}")
        return stats
