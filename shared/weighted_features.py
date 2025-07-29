"""
Enhanced Feature Extractor with Statistical Weights
Extracts and weights ML features based on configurable importance categories.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from shared.weights import weight_config, StatCategory


class WeightedFeatureExtractor:
    """Enhanced feature extractor with statistical weighting capabilities."""
    
    def __init__(self):
        self.weight_config = weight_config
        self.feature_cache = {}
        
    async def extract_weighted_game_features(self, game: Dict[str, Any], 
                                           home_team_stats: Optional[Dict[str, Any]] = None,
                                           away_team_stats: Optional[Dict[str, Any]] = None,
                                           h2h_games: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
        """Extract comprehensive weighted features for a game."""
        sport = game.get("sport", "").lower()
        home_team_id = game.get("home_team", {}).get("id")
        away_team_id = game.get("away_team", {}).get("id")
        
        if not all([sport, home_team_id, away_team_id]):
            logging.error("Missing required game information for feature extraction")
            return {}
        
        try:
            # Extract all feature categories
            features = {}
            
            # Recent Performance Features
            recent_features = await self._extract_recent_performance_features(
                home_team_id, away_team_id, sport, home_team_stats, away_team_stats
            )
            features.update(recent_features)
            
            # Historical Performance Features
            historical_features = await self._extract_historical_features(
                home_team_stats, away_team_stats, sport
            )
            features.update(historical_features)
            
            # Head-to-Head Features
            h2h_features = await self._extract_h2h_features(
                home_team_id, away_team_id, sport, h2h_games
            )
            features.update(h2h_features)
            
            # Home Advantage Features
            home_advantage_features = await self._extract_home_advantage_features(
                game, home_team_stats, away_team_stats
            )
            features.update(home_advantage_features)
            
            # Offensive/Defensive Features
            offensive_features = await self._extract_offensive_features(
                home_team_stats, away_team_stats, sport
            )
            features.update(offensive_features)
            
            defensive_features = await self._extract_defensive_features(
                home_team_stats, away_team_stats, sport
            )
            features.update(defensive_features)
            
            # Situational Features
            situational_features = await self._extract_situational_features(
                game, home_team_id, away_team_id
            )
            features.update(situational_features)
            
            # Apply weights to all features
            weighted_features = self.weight_config.get_weighted_features(features, sport)
            
            # Add feature importance scores
            weighted_features.update(self._calculate_feature_importance_scores(features, sport))
            
            return weighted_features
            
        except Exception as e:
            logging.error(f"Error extracting weighted features: {e}")
            return {}
    
    async def _extract_recent_performance_features(self, home_team_id: str, away_team_id: str, 
                                                 sport: str, home_stats: Optional[Dict], 
                                                 away_stats: Optional[Dict]) -> Dict[str, float]:
        """Extract recent performance features (last 5-10 games)."""
        features = {}
        
        try:
            # Get recent games for both teams
            home_recent = await self._get_recent_team_games(home_team_id, 10)
            away_recent = await self._get_recent_team_games(away_team_id, 10)
            
            # Home team recent performance
            if home_recent:
                features["recent_win_percentage_home"] = self._calculate_recent_win_rate(home_recent, home_team_id)
                features["recent_points_per_game_home"] = self._calculate_recent_scoring(home_recent, home_team_id)
                features["recent_points_allowed_home"] = self._calculate_recent_defense(home_recent, home_team_id)
                features["recent_form_trend_home"] = self._calculate_form_trend(home_recent, home_team_id)
                features["last_5_games_win_rate_home"] = self._calculate_recent_win_rate(home_recent[-5:], home_team_id)
            
            # Away team recent performance
            if away_recent:
                features["recent_win_percentage_away"] = self._calculate_recent_win_rate(away_recent, away_team_id)
                features["recent_points_per_game_away"] = self._calculate_recent_scoring(away_recent, away_team_id)
                features["recent_points_allowed_away"] = self._calculate_recent_defense(away_recent, away_team_id)
                features["recent_form_trend_away"] = self._calculate_form_trend(away_recent, away_team_id)
                features["last_5_games_win_rate_away"] = self._calculate_recent_win_rate(away_recent[-5:], away_team_id)
            
            # Comparative recent performance
            if home_recent and away_recent:
                features["recent_performance_differential"] = (
                    features.get("recent_win_percentage_home", 0) - 
                    features.get("recent_win_percentage_away", 0)
                )
                features["recent_scoring_differential"] = (
                    features.get("recent_points_per_game_home", 0) - 
                    features.get("recent_points_per_game_away", 0)
                )
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting recent performance features: {e}")
            return {}
    
    async def _extract_historical_features(self, home_stats: Optional[Dict], 
                                         away_stats: Optional[Dict], sport: str) -> Dict[str, float]:
        """Extract season/career historical performance features."""
        features = {}
        
        try:
            if home_stats:
                games_played_home = home_stats.get("games_played", 0)
                if games_played_home > 0:
                    features["season_win_percentage_home"] = home_stats.get("wins", 0) / games_played_home
                    features["season_points_per_game_home"] = home_stats.get("points_for", 0) / games_played_home
                    features["season_points_allowed_home"] = home_stats.get("points_against", 0) / games_played_home
                    features["season_point_differential_home"] = (
                        features["season_points_per_game_home"] - features["season_points_allowed_home"]
                    )
            
            if away_stats:
                games_played_away = away_stats.get("games_played", 0)
                if games_played_away > 0:
                    features["season_win_percentage_away"] = away_stats.get("wins", 0) / games_played_away
                    features["season_points_per_game_away"] = away_stats.get("points_for", 0) / games_played_away
                    features["season_points_allowed_away"] = away_stats.get("points_against", 0) / games_played_away
                    features["season_point_differential_away"] = (
                        features["season_points_per_game_away"] - features["season_points_allowed_away"]
                    )
            
            # Historical performance comparison
            if "season_win_percentage_home" in features and "season_win_percentage_away" in features:
                features["historical_win_rate_differential"] = (
                    features["season_win_percentage_home"] - features["season_win_percentage_away"]
                )
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting historical features: {e}")
            return {}
    
    async def _extract_h2h_features(self, home_team_id: str, away_team_id: str, 
                                  sport: str, h2h_games: Optional[List[Dict]]) -> Dict[str, float]:
        """Extract head-to-head matchup features."""
        features = {}
        
        try:
            if not h2h_games:
                # Default neutral values if no H2H history
                features["h2h_games_played"] = 0.0
                features["h2h_win_percentage_home"] = 0.5
                features["h2h_avg_score_diff"] = 0.0
                features["h2h_recent_trend"] = 0.5
                return features
            
            total_games = len(h2h_games)
            features["h2h_games_played"] = float(total_games)
            
            # Calculate H2H win rate for home team
            home_wins = 0
            score_diffs = []
            recent_results = []  # Last 5 H2H games
            
            for game in h2h_games:
                home_score = game.get("score", {}).get("home_score", 0)
                away_score = game.get("score", {}).get("away_score", 0)
                game_home_team = game.get("home_team", {}).get("id")
                
                # Determine if current home team won this historical game
                if game_home_team == home_team_id:
                    if home_score > away_score:
                        home_wins += 1
                        recent_results.append(1)
                    else:
                        recent_results.append(0)
                    score_diffs.append(home_score - away_score)
                else:
                    if away_score > home_score:
                        home_wins += 1
                        recent_results.append(1)
                    else:
                        recent_results.append(0)
                    score_diffs.append(away_score - home_score)
            
            features["h2h_win_percentage_home"] = home_wins / total_games if total_games > 0 else 0.5
            features["h2h_avg_score_diff"] = np.mean(score_diffs) if score_diffs else 0.0
            
            # Recent H2H trend (last 5 games)
            if len(recent_results) >= 3:
                features["h2h_recent_trend"] = np.mean(recent_results[-5:])
            else:
                features["h2h_recent_trend"] = features["h2h_win_percentage_home"]
            
            # H2H consistency
            if len(score_diffs) > 1:
                features["h2h_consistency"] = 1.0 / (1.0 + np.std(score_diffs))
            else:
                features["h2h_consistency"] = 0.5
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting H2H features: {e}")
            return {}
    
    async def _extract_home_advantage_features(self, game: Dict[str, Any], 
                                             home_stats: Optional[Dict], 
                                             away_stats: Optional[Dict]) -> Dict[str, float]:
        """Extract home field advantage features."""
        features = {}
        
        try:
            # Basic home field advantage (venue-specific)
            venue = game.get("venue", {})
            features["home_field_advantage"] = 0.55  # Default 55% home advantage
            
            # Home/away record analysis
            if home_stats:
                home_record = home_stats.get("home_record", {})
                home_games = home_record.get("games", 0)
                if home_games > 0:
                    features["home_win_percentage"] = home_record.get("wins", 0) / home_games
                else:
                    features["home_win_percentage"] = 0.5
            
            if away_stats:
                away_record = away_stats.get("away_record", {})
                away_games = away_record.get("games", 0)
                if away_games > 0:
                    features["away_win_percentage"] = away_record.get("wins", 0) / away_games
                else:
                    features["away_win_percentage"] = 0.5
            
            # Calculate adjusted home advantage
            if "home_win_percentage" in features and "away_win_percentage" in features:
                features["adjusted_home_advantage"] = (
                    features["home_win_percentage"] + (1.0 - features["away_win_percentage"])
                ) / 2.0
            
            # Venue-specific factors
            if venue.get("type") == "outdoor":
                features["venue_type_factor"] = 0.02  # Slight advantage for outdoor venues
            elif venue.get("type") == "dome":
                features["venue_type_factor"] = -0.01  # Slight disadvantage for domes
            else:
                features["venue_type_factor"] = 0.0
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting home advantage features: {e}")
            return {}
    
    async def _extract_offensive_features(self, home_stats: Optional[Dict], 
                                        away_stats: Optional[Dict], sport: str) -> Dict[str, float]:
        """Extract offensive capability features."""
        features = {}
        
        try:
            if home_stats:
                games_played = home_stats.get("games_played", 0)
                if games_played > 0:
                    features["offensive_efficiency_home"] = home_stats.get("points_for", 0) / games_played
                    features["scoring_consistency_home"] = self._calculate_scoring_consistency(home_stats)
            
            if away_stats:
                games_played = away_stats.get("games_played", 0)
                if games_played > 0:
                    features["offensive_efficiency_away"] = away_stats.get("points_for", 0) / games_played
                    features["scoring_consistency_away"] = self._calculate_scoring_consistency(away_stats)
            
            # Offensive differential
            if "offensive_efficiency_home" in features and "offensive_efficiency_away" in features:
                features["offensive_differential"] = (
                    features["offensive_efficiency_home"] - features["offensive_efficiency_away"]
                )
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting offensive features: {e}")
            return {}
    
    async def _extract_defensive_features(self, home_stats: Optional[Dict], 
                                        away_stats: Optional[Dict], sport: str) -> Dict[str, float]:
        """Extract defensive capability features."""
        features = {}
        
        try:
            if home_stats:
                games_played = home_stats.get("games_played", 0)
                if games_played > 0:
                    features["defensive_efficiency_home"] = home_stats.get("points_against", 0) / games_played
                    # Lower points allowed = better defense, so invert
                    features["defensive_strength_home"] = 1.0 / (1.0 + features["defensive_efficiency_home"] / 20.0)
            
            if away_stats:
                games_played = away_stats.get("games_played", 0)
                if games_played > 0:
                    features["defensive_efficiency_away"] = away_stats.get("points_against", 0) / games_played
                    features["defensive_strength_away"] = 1.0 / (1.0 + features["defensive_efficiency_away"] / 20.0)
            
            # Defensive differential (lower is better for points against)
            if "defensive_efficiency_home" in features and "defensive_efficiency_away" in features:
                features["defensive_differential"] = (
                    features["defensive_efficiency_away"] - features["defensive_efficiency_home"]
                )
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting defensive features: {e}")
            return {}
    
    async def _extract_situational_features(self, game: Dict[str, Any], 
                                          home_team_id: str, away_team_id: str) -> Dict[str, float]:
        """Extract situational factors like rest, travel, etc."""
        features = {}
        
        try:
            # Days of rest calculation
            game_date = datetime.fromisoformat(game.get("scheduled_date", "").replace("Z", "+00:00"))
            
            # Get last games for both teams to calculate rest
            home_last_game = await self._get_last_game_date(home_team_id)
            away_last_game = await self._get_last_game_date(away_team_id)
            
            if home_last_game:
                home_rest_days = (game_date - home_last_game).days
                features["home_rest_days"] = min(home_rest_days, 14)  # Cap at 14 days
                features["home_rest_advantage"] = self._calculate_rest_advantage(home_rest_days)
            
            if away_last_game:
                away_rest_days = (game_date - away_last_game).days
                features["away_rest_days"] = min(away_rest_days, 14)
                features["away_rest_advantage"] = self._calculate_rest_advantage(away_rest_days)
            
            # Rest differential
            if "home_rest_days" in features and "away_rest_days" in features:
                features["rest_differential"] = features["home_rest_days"] - features["away_rest_days"]
            
            # Time factors
            features["game_hour"] = game_date.hour
            features["game_day_of_week"] = game_date.weekday()
            
            # Playoff/regular season context
            features["playoff_context"] = 1.0 if game.get("playoff") else 0.0
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting situational features: {e}")
            return {}
    
    def _calculate_feature_importance_scores(self, features: Dict[str, float], sport: str) -> Dict[str, float]:
        """Calculate importance scores for feature categories."""
        importance_scores = {}
        category_weights = self.weight_config.get_weights_for_sport(sport)
        
        for category, weight in category_weights.items():
            importance_scores[f"{category.value}_importance"] = weight
        
        return importance_scores
    
    # Helper methods
    def _calculate_recent_win_rate(self, games: List[Dict], team_id: str) -> float:
        """Calculate win rate from recent games."""
        if not games:
            return 0.5
        
        wins = 0
        for game in games:
            if self._did_team_win(game, team_id):
                wins += 1
        
        return wins / len(games)
    
    def _calculate_recent_scoring(self, games: List[Dict], team_id: str) -> float:
        """Calculate average scoring from recent games."""
        if not games:
            return 20.0  # Default
        
        total_points = 0
        for game in games:
            points = self._get_team_score_in_game(game, team_id)
            total_points += points
        
        return total_points / len(games)
    
    def _calculate_recent_defense(self, games: List[Dict], team_id: str) -> float:
        """Calculate average points allowed from recent games."""
        if not games:
            return 20.0  # Default
        
        total_allowed = 0
        for game in games:
            allowed = self._get_opponent_score_in_game(game, team_id)
            total_allowed += allowed
        
        return total_allowed / len(games)
    
    def _calculate_form_trend(self, games: List[Dict], team_id: str) -> float:
        """Calculate trend in recent form (improving/declining)."""
        if len(games) < 3:
            return 0.5
        
        # Weight recent games more heavily
        weights = [0.4, 0.3, 0.2, 0.1]  # Last 4 games
        weighted_results = []
        
        for i, game in enumerate(games[-4:]):
            result = 1.0 if self._did_team_win(game, team_id) else 0.0
            weight = weights[min(i, len(weights) - 1)]
            weighted_results.append(result * weight)
        
        return sum(weighted_results)
    
    def _calculate_scoring_consistency(self, team_stats: Dict[str, Any]) -> float:
        """Calculate scoring consistency metric."""
        # This is a simplified calculation - in production, you'd analyze game-by-game variance
        points_per_game = team_stats.get("points_for", 0) / max(team_stats.get("games_played", 1), 1)
        # Normalize to 0-1 scale where higher = more consistent
        return min(1.0, points_per_game / 35.0)
    
    def _calculate_rest_advantage(self, rest_days: int) -> float:
        """Calculate advantage/disadvantage from rest days."""
        if rest_days < 2:
            return -0.1  # Disadvantage for insufficient rest
        elif rest_days <= 4:
            return 0.05  # Slight advantage for optimal rest
        elif rest_days <= 7:
            return 0.0   # Neutral
        else:
            return -0.05  # Slight disadvantage for too much rest
    
    def _did_team_win(self, game: Dict[str, Any], team_id: str) -> bool:
        """Determine if team won the game."""
        home_team_id = game.get("home_team", {}).get("id")
        home_score = game.get("score", {}).get("home_score", 0)
        away_score = game.get("score", {}).get("away_score", 0)
        
        if home_team_id == team_id:
            return home_score > away_score
        else:
            return away_score > home_score
    
    def _get_team_score_in_game(self, game: Dict[str, Any], team_id: str) -> int:
        """Get team's score in a game."""
        home_team_id = game.get("home_team", {}).get("id")
        home_score = game.get("score", {}).get("home_score", 0)
        away_score = game.get("score", {}).get("away_score", 0)
        
        return home_score if home_team_id == team_id else away_score
    
    def _get_opponent_score_in_game(self, game: Dict[str, Any], team_id: str) -> int:
        """Get opponent's score in a game."""
        home_team_id = game.get("home_team", {}).get("id")
        home_score = game.get("score", {}).get("home_score", 0)
        away_score = game.get("score", {}).get("away_score", 0)
        
        return away_score if home_team_id == team_id else home_score
    
    async def _get_recent_team_games(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent games for a team."""
        # This would be implemented to query Cosmos DB
        # Placeholder for the actual implementation
        return []
    
    async def _get_last_game_date(self, team_id: str) -> Optional[datetime]:
        """Get the date of team's last game."""
        # This would be implemented to query Cosmos DB
        # Placeholder for the actual implementation
        return None
