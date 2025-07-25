"""
Get Predictions API Endpoint
RESTful API to retrieve game predictions with filtering and pagination.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import azure.functions as func
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import cosmos_client


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get predictions API endpoint.
    
    Query parameters:
    - sport: Filter by sport (nfl, nba, mlb, nhl, soccer)
    - confidence_min: Minimum confidence score (0-100)
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    - team: Filter by team ID
    - limit: Maximum number of results (default: 50)
    - offset: Offset for pagination (default: 0)
    """
    logging.info('Get predictions API called.')
    
    try:
        # Parse query parameters
        sport = req.params.get('sport')
        confidence_min = req.params.get('confidence_min')
        date_from = req.params.get('date_from')
        date_to = req.params.get('date_to')
        team = req.params.get('team')
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        
        # Validate limit and offset
        limit = min(limit, 1000)  # Max 1000 results
        offset = max(offset, 0)
        
        # Build query
        query_parts = ["SELECT * FROM c WHERE 1=1"]
        parameters = []
        
        # Add filters
        if sport:
            # Need to join with games to filter by sport
            query_parts = ["""
                SELECT p.*, g.sport, g.home_team, g.away_team, g.scheduled_date as game_date
                FROM predictions p
                JOIN games g ON p.game_id = g.id
                WHERE 1=1
            """]
            query_parts.append("AND g.sport = @sport")
            parameters.append({"name": "@sport", "value": sport.lower()})
        
        if confidence_min:
            try:
                min_conf = float(confidence_min)
                query_parts.append("AND p.confidence_score >= @confidence_min")
                parameters.append({"name": "@confidence_min", "value": min_conf})
            except ValueError:
                pass
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").isoformat()
                if sport:
                    query_parts.append("AND g.scheduled_date >= @date_from")
                else:
                    query_parts.append("AND p.created_at >= @date_from")
                parameters.append({"name": "@date_from", "value": from_date})
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").isoformat()
                if sport:
                    query_parts.append("AND g.scheduled_date <= @date_to")
                else:
                    query_parts.append("AND p.created_at <= @date_to")
                parameters.append({"name": "@date_to", "value": to_date})
            except ValueError:
                pass
        
        if team:
            if sport:
                query_parts.append("AND (g.home_team.id = @team OR g.away_team.id = @team)")
            else:
                # This requires a more complex query to join with games
                query_parts.append("AND p.game_id LIKE @team_pattern")
                parameters.append({"name": "@team_pattern", "value": f"%{team}%"})
            
            if sport:
                parameters.append({"name": "@team", "value": team})
        
        # Add ordering and pagination
        if sport:
            query_parts.append("ORDER BY g.scheduled_date DESC")
        else:
            query_parts.append("ORDER BY p.created_at DESC")
        
        query_parts.append(f"OFFSET {offset} LIMIT {limit}")
        
        final_query = " ".join(query_parts)
        
        # Execute query
        if sport:
            # Use a simpler approach for sport filtering
            simple_query = "SELECT * FROM c ORDER BY c.created_at DESC"
            all_predictions = await cosmos_client.query_items("predictions", simple_query, [])
            
            # Filter in Python (not ideal for large datasets, but works for demo)
            filtered_predictions = []
            for pred in all_predictions:
                # Get game data for filtering
                game_query = "SELECT * FROM c WHERE c.id = @game_id"
                game_params = [{"name": "@game_id", "value": pred["game_id"]}]
                games = await cosmos_client.query_items("games", game_query, game_params)
                
                if games:
                    game = games[0]
                    
                    # Apply filters
                    if sport and game.get("sport") != sport.lower():
                        continue
                    
                    if confidence_min and pred.get("confidence_score", 0) < float(confidence_min):
                        continue
                    
                    if team and (game.get("home_team", {}).get("id") != team and 
                               game.get("away_team", {}).get("id") != team):
                        continue
                    
                    # Add game info to prediction
                    pred["game_info"] = {
                        "sport": game.get("sport"),
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                        "scheduled_date": game.get("scheduled_date"),
                        "status": game.get("status")
                    }
                    
                    filtered_predictions.append(pred)
            
            # Apply pagination
            predictions = filtered_predictions[offset:offset + limit]
        
        else:
            predictions = await cosmos_client.query_items("predictions", final_query, parameters)
            
            # Add game info for each prediction
            for pred in predictions:
                game_query = "SELECT * FROM c WHERE c.id = @game_id"
                game_params = [{"name": "@game_id", "value": pred["game_id"]}]
                games = await cosmos_client.query_items("games", game_query, game_params)
                
                if games:
                    game = games[0]
                    pred["game_info"] = {
                        "sport": game.get("sport"),
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                        "scheduled_date": game.get("scheduled_date"),
                        "status": game.get("status")
                    }
        
        # Prepare response
        response_data = {
            "status": "success",
            "predictions": predictions,
            "total_results": len(predictions),
            "offset": offset,
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat(),
            "filters_applied": {
                "sport": sport,
                "confidence_min": confidence_min,
                "date_from": date_from,
                "date_to": date_to,
                "team": team
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
        logging.error(f"Error in get predictions API: {e}")
        
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
