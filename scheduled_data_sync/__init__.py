"""
Scheduled Data Sync Function
Automatically syncs sports data every 6 hours and generates predictions.
Timer trigger: "0 0 */6 * * *" (every 6 hours)
"""

import logging
from datetime import datetime, timedelta
import azure.functions as func
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import cosmos_client, config
from sports_data_ingestion import SportsDataIngester
from game_predictor import EnhancedGamePredictor


async def main(timer: func.TimerRequest) -> None:
    """
    Scheduled function to sync sports data and generate predictions.
    
    This function:
    1. Ingests latest sports data for all supported sports
    2. Updates team statistics
    3. Generates predictions for upcoming games
    4. Logs performance metrics
    """
    utc_timestamp = datetime.utcnow().replace(tzinfo=None).isoformat()
    
    if timer.past_due:
        logging.info('The timer is past due!')
    
    logging.info(f'Scheduled data sync started at {utc_timestamp}')
    
    sync_results = {
        "start_time": utc_timestamp,
        "sports_processed": [],
        "total_games_ingested": 0,
        "total_teams_updated": 0,
        "total_predictions_generated": 0,
        "errors": []
    }
    
    try:
        # Initialize services
        ingester = SportsDataIngester()
        predictor = EnhancedGamePredictor()
        
        await ingester.initialize_api_clients()
        await predictor.load_models()
        
        # Process each sport
        sports_to_process = ["nfl", "nba"]
        current_year = datetime.now().year
        
        for sport in sports_to_process:
            sport_results = await process_sport_data(ingester, predictor, sport, current_year)
            sync_results["sports_processed"].append(sport_results)
            sync_results["total_games_ingested"] += sport_results["games_ingested"]
            sync_results["total_teams_updated"] += sport_results["teams_updated"]
            sync_results["total_predictions_generated"] += sport_results["predictions_generated"]
            
            if sport_results["errors"]:
                sync_results["errors"].extend(sport_results["errors"])
        
        # Cleanup
        await ingester.cleanup()
        
        # Log summary
        sync_results["end_time"] = datetime.utcnow().isoformat()
        sync_results["duration_minutes"] = calculate_duration(sync_results["start_time"], sync_results["end_time"])
        
        logging.info(f"Scheduled data sync completed successfully:")
        logging.info(f"  - Games ingested: {sync_results['total_games_ingested']}")
        logging.info(f"  - Teams updated: {sync_results['total_teams_updated']}")
        logging.info(f"  - Predictions generated: {sync_results['total_predictions_generated']}")
        logging.info(f"  - Duration: {sync_results['duration_minutes']} minutes")
        
        if sync_results["errors"]:
            logging.warning(f"  - Errors encountered: {len(sync_results['errors'])}")
        
        # Store sync results for monitoring
        await store_sync_results(sync_results)
        
    except Exception as e:
        error_msg = f"Critical error in scheduled data sync: {e}"
        logging.error(error_msg)
        sync_results["errors"].append(error_msg)
        sync_results["end_time"] = datetime.utcnow().isoformat()
        
        # Store error results
        await store_sync_results(sync_results)


async def process_sport_data(ingester: 'SportsDataIngester', predictor: 'EnhancedGamePredictor', sport: str, year: int) -> dict:
    """Process data for a specific sport."""
    sport_results = {
        "sport": sport,
        "games_ingested": 0,
        "teams_updated": 0,
        "predictions_generated": 0,
        "errors": []
    }
    
    try:
        logging.info(f"Processing {sport} data...")
        
        # Determine season format based on sport
        if sport == "nfl":
            season = str(year)
            games = await ingester.fetch_nfl_games(season)
        elif sport == "nba":
            season = f"{year-1}-{str(year)[2:]}"  # NBA seasons span two years
            games = await ingester.fetch_nba_games(season)
        else:
            logging.warning(f"Sport {sport} not yet implemented")
            return sport_results
        
        # Store games
        if games:
            sport_results["games_ingested"] = await ingester.store_games(games)
            logging.info(f"Stored {sport_results['games_ingested']} {sport} games")
        
        # Update team statistics
        try:
            team_stats = await ingester.fetch_team_stats(sport, season)
            sport_results["teams_updated"] = len(team_stats)
            logging.info(f"Updated {sport_results['teams_updated']} {sport} team statistics")
        except Exception as e:
            error_msg = f"Error updating {sport} team stats: {e}"
            logging.error(error_msg)
            sport_results["errors"].append(error_msg)
        
        # Generate predictions for upcoming games
        try:
            predictions = await predictor.predict_upcoming_games(sport, days_ahead=7)
            sport_results["predictions_generated"] = len(predictions)
            logging.info(f"Generated {sport_results['predictions_generated']} {sport} predictions")
        except Exception as e:
            error_msg = f"Error generating {sport} predictions: {e}"
            logging.error(error_msg)
            sport_results["errors"].append(error_msg)
        
    except Exception as e:
        error_msg = f"Error processing {sport} data: {e}"
        logging.error(error_msg)
        sport_results["errors"].append(error_msg)
    
    return sport_results


async def store_sync_results(results: dict) -> None:
    """Store sync results for monitoring and analysis."""
    try:
        sync_record = {
            "id": f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "type": "scheduled_sync",
            "results": results,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await cosmos_client.upsert_item("sync_logs", sync_record)
        logging.info("Sync results stored successfully")
        
    except Exception as e:
        logging.error(f"Error storing sync results: {e}")


def calculate_duration(start_time: str, end_time: str) -> float:
    """Calculate duration in minutes between two ISO timestamps."""
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        duration = (end - start).total_seconds() / 60
        return round(duration, 2)
    except Exception:
        return 0.0


async def cleanup_old_data() -> None:
    """Clean up old data to manage storage costs."""
    try:
        # Clean up old predictions (keep last 30 days)
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        query = "SELECT c.id FROM c WHERE c.created_at < @cutoff_date"
        parameters = [{"name": "@cutoff_date", "value": cutoff_date}]
        
        old_predictions = await cosmos_client.query_items("predictions", query, parameters)
        
        # In a real implementation, you would delete these items
        # For now, just log the count
        logging.info(f"Found {len(old_predictions)} old predictions for potential cleanup")
        
        # Clean up old sync logs (keep last 90 days)
        sync_cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
        
        query = "SELECT c.id FROM c WHERE c.created_at < @cutoff_date"
        parameters = [{"name": "@cutoff_date", "value": sync_cutoff}]
        
        old_sync_logs = await cosmos_client.query_items("sync_logs", query, parameters)
        logging.info(f"Found {len(old_sync_logs)} old sync logs for potential cleanup")
        
    except Exception as e:
        logging.error(f"Error in cleanup process: {e}")
