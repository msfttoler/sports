"""
Game Prediction Function
Uses ML models to predict game outcomes with confidence scores.
Processes upcoming games and generates predictions.
"""

import json
import logging
import asyncio
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import azure.functions as func
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import cosmos_client, config, FeatureExtractor


class GamePredictor:
    """ML-based game prediction system with confidence scoring."""
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.models = {}
        self.model_version = "v1.0.0"
        
        # Model performance metrics (would be loaded from storage in production)
        self.model_metrics = {
            "nfl": {"accuracy": 0.68, "calibration_score": 0.75},
            "nba": {"accuracy": 0.64, "calibration_score": 0.72}
        }
    
    async def load_models(self):
        """Load pre-trained ML models from Azure Storage."""
        # In production, this would load actual trained models from Azure ML or Blob Storage
        # For demo purposes, we'll create simple mock models
        
        try:
            # Mock model creation - in production, load from storage
            for sport in ["nfl", "nba"]:
                self.models[sport] = self._create_mock_model(sport)
            
            logging.info("Successfully loaded ML models")
            
        except Exception as e:
            logging.error(f"Error loading models: {e}")
            # Create fallback models
            for sport in ["nfl", "nba"]:
                self.models[sport] = self._create_mock_model(sport)
    
    def _create_mock_model(self, sport: str) -> Dict[str, Any]:
        """Create a mock model for demonstration purposes."""
        # In production, this would be a trained scikit-learn model, TensorFlow model, etc.
        return {
            "type": "mock_classifier",
            "sport": sport,
            "features": [
                "home_win_percentage", "away_win_percentage",
                "home_points_per_game", "away_points_per_game",
                "home_points_allowed_per_game", "away_points_allowed_per_game",
                "home_recent_form", "away_recent_form",
                "head_to_head_record", "home_field_advantage"
            ],
            "weights": np.random.random(10),  # Random weights for demo
            "bias": np.random.random()
        }
    
    async def predict_game_outcome(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Predict outcome for a specific game."""
        try:
            # Fetch game data
            game = await self._get_game_data(game_id)
            if not game:
                logging.error(f"Game {game_id} not found")
                return None
            
            sport = game["sport"]
            if sport not in self.models:
                logging.error(f"No model available for sport: {sport}")
                return None
            
            # Extract features
            features = await self._extract_game_features(game)
            if not features:
                logging.error(f"Failed to extract features for game {game_id}")
                return None
            
            # Make prediction
            prediction_result = self._make_prediction(sport, features)
            
            # Create prediction record
            prediction = {
                "id": f"pred_{game_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "game_id": game_id,
                "predicted_outcome": prediction_result["outcome"],
                "confidence_score": prediction_result["confidence"],
                "predicted_home_score": prediction_result.get("home_score"),
                "predicted_away_score": prediction_result.get("away_score"),
                "win_probability": prediction_result["win_probabilities"],
                "model_version": self.model_version,
                "features_used": list(features.keys()),
                "prediction_reasoning": prediction_result["reasoning"],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "model_accuracy": self.model_metrics.get(sport, {}).get("accuracy", 0.6),
                    "features": features
                }
            }
            
            # Store prediction
            await cosmos_client.upsert_item("predictions", prediction)
            
            return prediction
            
        except Exception as e:
            logging.error(f"Error predicting game outcome: {e}")
            return None
    
    async def _get_game_data(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Fetch game data from Cosmos DB."""
        try:
            query = "SELECT * FROM c WHERE c.id = @game_id"
            parameters = [{"name": "@game_id", "value": game_id}]
            
            games = await cosmos_client.query_items("games", query, parameters)
            return games[0] if games else None
            
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            return None
    
    async def _extract_game_features(self, game: Dict[str, Any]) -> Dict[str, float]:
        """Extract ML features for a game."""
        try:
            home_team_id = game["home_team"]["id"]
            away_team_id = game["away_team"]["id"]
            season = game["season"]
            sport = game["sport"]
            
            features = {}
            
            # Get team statistics
            home_stats = await self._get_team_stats(home_team_id, season)
            away_stats = await self._get_team_stats(away_team_id, season)
            
            if home_stats and away_stats:
                # Extract team-specific features
                home_features = self.feature_extractor.extract_team_features(
                    home_stats, await self._get_recent_games(home_team_id, 10)
                )
                away_features = self.feature_extractor.extract_team_features(
                    away_stats, await self._get_recent_games(away_team_id, 10)
                )
                
                # Add prefixes to distinguish home vs away
                for key, value in home_features.items():
                    features[f"home_{key}"] = value
                
                for key, value in away_features.items():
                    features[f"away_{key}"] = value
                
                # Head-to-head features
                h2h_games = await self._get_head_to_head_games(home_team_id, away_team_id)
                h2h_features = self.feature_extractor.extract_matchup_features(
                    home_team_id, away_team_id, h2h_games
                )
                features.update(h2h_features)
                
                # Contextual features
                features["home_field_advantage"] = 0.55  # Historical home field advantage
                features["rest_days_home"] = 7.0  # Mock data - would calculate from schedule
                features["rest_days_away"] = 7.0
                
                # Handle missing values
                for key, value in features.items():
                    if value is None or np.isnan(value):
                        features[key] = 0.0
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting game features: {e}")
            return {}
    
    async def _get_team_stats(self, team_id: str, season: str) -> Optional[Dict[str, Any]]:
        """Get team statistics for a season."""
        try:
            query = "SELECT * FROM c WHERE c.team_id = @team_id AND c.season = @season"
            parameters = [
                {"name": "@team_id", "value": team_id},
                {"name": "@season", "value": season}
            ]
            
            stats = await cosmos_client.query_items("team_stats", query, parameters)
            return stats[0] if stats else None
            
        except Exception as e:
            logging.error(f"Error fetching team stats: {e}")
            return None
    
    async def _get_recent_games(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
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
                else:
                    home_score = game.get("score", {}).get("home_score", 0) or 0
                    away_score = game.get("score", {}).get("away_score", 0) or 0
                    game["result"] = "W" if away_score > home_score else "L" if home_score > away_score else "T"
            
            return games
            
        except Exception as e:
            logging.error(f"Error fetching recent games: {e}")
            return []
    
    async def _get_head_to_head_games(self, team1_id: str, team2_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get head-to-head games between two teams."""
        try:
            query = """
            SELECT * FROM c 
            WHERE ((c.home_team.id = @team1_id AND c.away_team.id = @team2_id) 
                   OR (c.home_team.id = @team2_id AND c.away_team.id = @team1_id))
            AND c.status = 'completed'
            ORDER BY c.scheduled_date DESC
            OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@team1_id", "value": team1_id},
                {"name": "@team2_id", "value": team2_id},
                {"name": "@limit", "value": limit}
            ]
            
            return await cosmos_client.query_items("games", query, parameters)
            
        except Exception as e:
            logging.error(f"Error fetching head-to-head games: {e}")
            return []
    
    def _make_prediction(self, sport: str, features: Dict[str, float]) -> Dict[str, Any]:
        """Make prediction using the ML model."""
        try:
            model = self.models[sport]
            
            # Extract feature values in consistent order
            feature_names = model["features"]
            feature_values = [features.get(name, 0.0) for name in feature_names]
            
            # Simple mock prediction logic (replace with actual model inference)
            # Calculate weighted sum
            weighted_sum = np.dot(feature_values, model["weights"]) + model["bias"]
            
            # Convert to probabilities using sigmoid
            home_win_prob = 1 / (1 + np.exp(-weighted_sum))
            away_win_prob = 1 - home_win_prob
            
            # Determine outcome
            if home_win_prob > away_win_prob:
                outcome = "home_win"
                confidence = home_win_prob * 100
            else:
                outcome = "away_win"
                confidence = away_win_prob * 100
            
            # Adjust confidence based on model accuracy
            model_accuracy = self.model_metrics.get(sport, {}).get("accuracy", 0.6)
            adjusted_confidence = confidence * model_accuracy
            
            # Generate reasoning
            reasoning = self._generate_reasoning(features, outcome, confidence)
            
            # Mock score predictions (would be from separate regression model)
            home_expected = features.get("home_points_per_game", 20.0)
            away_expected = features.get("away_points_per_game", 20.0)
            
            return {
                "outcome": outcome,
                "confidence": min(95.0, max(55.0, adjusted_confidence)),  # Cap between 55-95%
                "home_score": round(home_expected + np.random.normal(0, 3), 1),
                "away_score": round(away_expected + np.random.normal(0, 3), 1),
                "win_probabilities": {
                    "home": round(home_win_prob * 100, 1),
                    "away": round(away_win_prob * 100, 1)
                },
                "reasoning": reasoning
            }
            
        except Exception as e:
            logging.error(f"Error making prediction: {e}")
            return {
                "outcome": "home_win",
                "confidence": 60.0,
                "home_score": 20.0,
                "away_score": 17.0,
                "win_probabilities": {"home": 60.0, "away": 40.0},
                "reasoning": "Prediction based on default model due to error"
            }
    
    def _generate_reasoning(self, features: Dict[str, float], outcome: str, confidence: float) -> str:
        """Generate human-readable reasoning for the prediction."""
        reasoning_parts = []
        
        # Win percentage comparison
        home_win_pct = features.get("home_win_percentage", 0.5)
        away_win_pct = features.get("away_win_percentage", 0.5)
        
        if abs(home_win_pct - away_win_pct) > 0.1:
            better_team = "home" if home_win_pct > away_win_pct else "away"
            reasoning_parts.append(f"The {better_team} team has a significantly better win percentage ({max(home_win_pct, away_win_pct):.1%} vs {min(home_win_pct, away_win_pct):.1%})")
        
        # Recent form
        home_recent = features.get("home_recent_win_percentage", 0.5)
        away_recent = features.get("away_recent_win_percentage", 0.5)
        
        if abs(home_recent - away_recent) > 0.2:
            hot_team = "home" if home_recent > away_recent else "away"
            reasoning_parts.append(f"The {hot_team} team is in better recent form")
        
        # Home field advantage
        if features.get("home_field_advantage", 0.5) > 0.52:
            reasoning_parts.append("Home field advantage is a factor")
        
        # Head-to-head
        h2h_rate = features.get("historical_home_win_rate")
        if h2h_rate is not None:
            if h2h_rate > 0.6:
                reasoning_parts.append("Home team has dominated this matchup historically")
            elif h2h_rate < 0.4:
                reasoning_parts.append("Away team has performed well in this matchup historically")
        
        if not reasoning_parts:
            reasoning_parts.append("Teams appear evenly matched based on available data")
        
        reasoning = ". ".join(reasoning_parts) + f". Confidence: {confidence:.0f}%"
        
        return reasoning
    
    async def predict_upcoming_games(self, sport: str = None, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Predict outcomes for upcoming games."""
        try:
            # Query for upcoming games
            cutoff_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
            
            query = """
            SELECT * FROM c 
            WHERE c.status = 'scheduled' 
            AND c.scheduled_date <= @cutoff_date
            """
            parameters = [{"name": "@cutoff_date", "value": cutoff_date}]
            
            if sport:
                query += " AND c.sport = @sport"
                parameters.append({"name": "@sport", "value": sport})
            
            games = await cosmos_client.query_items("games", query, parameters)
            
            predictions = []
            for game in games:
                prediction = await self.predict_game_outcome(game["id"])
                if prediction:
                    predictions.append(prediction)
            
            logging.info(f"Generated {len(predictions)} predictions for upcoming games")
            return predictions
            
        except Exception as e:
            logging.error(f"Error predicting upcoming games: {e}")
            return []


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main function entry point."""
    logging.info('Game predictor function triggered.')
    
    predictor = GamePredictor()
    
    try:
        # Load ML models
        await predictor.load_models()
        
        # Get request parameters
        game_id = req.params.get('game_id')
        sport = req.params.get('sport')
        days_ahead = int(req.params.get('days_ahead', 7))
        
        results = {
            "status": "success",
            "predictions": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if game_id:
            # Predict specific game
            prediction = await predictor.predict_game_outcome(game_id)
            if prediction:
                results["predictions"] = [prediction]
            else:
                results["status"] = "error"
                results["message"] = f"Could not generate prediction for game {game_id}"
        else:
            # Predict upcoming games
            predictions = await predictor.predict_upcoming_games(sport, days_ahead)
            results["predictions"] = predictions
            results["total_predictions"] = len(predictions)
        
        return func.HttpResponse(
            json.dumps(results, default=str),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    
    except Exception as e:
        logging.error(f"Error in game predictor: {e}")
        
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
