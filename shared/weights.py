"""
Statistical Weights Configuration
Defines importance weights for different statistical categories in ML predictions.
Higher weights indicate more important factors for prediction accuracy.
"""

from typing import Dict, Any, List
from enum import Enum


class StatCategory(Enum):
    """Categories of statistics for weighting."""
    RECENT_PERFORMANCE = "recent_performance"
    HISTORICAL_PERFORMANCE = "historical_performance"
    HEAD_TO_HEAD = "head_to_head"
    HOME_ADVANTAGE = "home_advantage"
    OFFENSIVE_STATS = "offensive_stats"
    DEFENSIVE_STATS = "defensive_stats"
    SITUATIONAL = "situational"
    INJURY_REPORTS = "injury_reports"
    WEATHER = "weather"
    MOMENTUM = "momentum"


class WeightConfig:
    """Configuration class for statistical weights."""
    
    def __init__(self):
        # Default weights (can be overridden per sport)
        self.default_weights = {
            StatCategory.RECENT_PERFORMANCE: 0.25,     # Last 5-10 games
            StatCategory.HISTORICAL_PERFORMANCE: 0.15, # Season/career stats
            StatCategory.HEAD_TO_HEAD: 0.20,          # H2H matchup history
            StatCategory.HOME_ADVANTAGE: 0.12,         # Home field advantage
            StatCategory.OFFENSIVE_STATS: 0.10,        # Scoring ability
            StatCategory.DEFENSIVE_STATS: 0.10,        # Defensive ability
            StatCategory.SITUATIONAL: 0.05,           # Rest days, travel, etc.
            StatCategory.INJURY_REPORTS: 0.03,        # Key player injuries
            StatCategory.WEATHER: 0.00,               # Weather conditions (outdoor sports)
            StatCategory.MOMENTUM: 0.00               # Winning/losing streaks
        }
        
        # Sport-specific weight overrides
        self.sport_weights = {
            "nfl": {
                StatCategory.RECENT_PERFORMANCE: 0.20,
                StatCategory.HEAD_TO_HEAD: 0.25,
                StatCategory.HOME_ADVANTAGE: 0.15,
                StatCategory.WEATHER: 0.05,
                StatCategory.INJURY_REPORTS: 0.08,
                StatCategory.SITUATIONAL: 0.07
            },
            "nba": {
                StatCategory.RECENT_PERFORMANCE: 0.30,
                StatCategory.HISTORICAL_PERFORMANCE: 0.20,
                StatCategory.HEAD_TO_HEAD: 0.15,
                StatCategory.HOME_ADVANTAGE: 0.10,
                StatCategory.MOMENTUM: 0.10,
                StatCategory.INJURY_REPORTS: 0.10,
                StatCategory.SITUATIONAL: 0.05
            },
            "mlb": {
                StatCategory.RECENT_PERFORMANCE: 0.25,
                StatCategory.HEAD_TO_HEAD: 0.20,
                StatCategory.HOME_ADVANTAGE: 0.08,
                StatCategory.WEATHER: 0.12,
                StatCategory.HISTORICAL_PERFORMANCE: 0.18,
                StatCategory.OFFENSIVE_STATS: 0.12,
                StatCategory.DEFENSIVE_STATS: 0.05
            },
            "nhl": {
                StatCategory.RECENT_PERFORMANCE: 0.28,
                StatCategory.HEAD_TO_HEAD: 0.22,
                StatCategory.HOME_ADVANTAGE: 0.12,
                StatCategory.MOMENTUM: 0.15,
                StatCategory.INJURY_REPORTS: 0.13,
                StatCategory.SITUATIONAL: 0.10
            }
        }
        
        # Feature mappings - which features belong to which categories
        self.feature_categories = {
            # Recent Performance Features
            "recent_win_percentage": StatCategory.RECENT_PERFORMANCE,
            "recent_form_home": StatCategory.RECENT_PERFORMANCE,
            "recent_form_away": StatCategory.RECENT_PERFORMANCE,
            "last_5_games_avg_score": StatCategory.RECENT_PERFORMANCE,
            "last_10_games_win_rate": StatCategory.RECENT_PERFORMANCE,
            "recent_points_per_game": StatCategory.RECENT_PERFORMANCE,
            "recent_points_allowed": StatCategory.RECENT_PERFORMANCE,
            
            # Historical Performance Features
            "season_win_percentage": StatCategory.HISTORICAL_PERFORMANCE,
            "career_win_percentage": StatCategory.HISTORICAL_PERFORMANCE,
            "season_points_per_game": StatCategory.HISTORICAL_PERFORMANCE,
            "season_points_allowed": StatCategory.HISTORICAL_PERFORMANCE,
            "overall_record": StatCategory.HISTORICAL_PERFORMANCE,
            
            # Head-to-Head Features
            "h2h_win_percentage": StatCategory.HEAD_TO_HEAD,
            "h2h_avg_score_diff": StatCategory.HEAD_TO_HEAD,
            "h2h_games_played": StatCategory.HEAD_TO_HEAD,
            "h2h_recent_meetings": StatCategory.HEAD_TO_HEAD,
            "h2h_home_advantage": StatCategory.HEAD_TO_HEAD,
            
            # Home Advantage Features
            "home_field_advantage": StatCategory.HOME_ADVANTAGE,
            "home_win_percentage": StatCategory.HOME_ADVANTAGE,
            "away_win_percentage": StatCategory.HOME_ADVANTAGE,
            "venue_familiarity": StatCategory.HOME_ADVANTAGE,
            "travel_distance": StatCategory.HOME_ADVANTAGE,
            
            # Offensive Stats Features
            "points_per_game": StatCategory.OFFENSIVE_STATS,
            "offensive_efficiency": StatCategory.OFFENSIVE_STATS,
            "scoring_consistency": StatCategory.OFFENSIVE_STATS,
            "red_zone_efficiency": StatCategory.OFFENSIVE_STATS,
            "yards_per_play": StatCategory.OFFENSIVE_STATS,
            
            # Defensive Stats Features
            "points_allowed_per_game": StatCategory.DEFENSIVE_STATS,
            "defensive_efficiency": StatCategory.DEFENSIVE_STATS,
            "turnovers_forced": StatCategory.DEFENSIVE_STATS,
            "defensive_stops": StatCategory.DEFENSIVE_STATS,
            "yards_allowed_per_play": StatCategory.DEFENSIVE_STATS,
            
            # Situational Features
            "days_rest": StatCategory.SITUATIONAL,
            "back_to_back_games": StatCategory.SITUATIONAL,
            "road_trip_game_number": StatCategory.SITUATIONAL,
            "time_zone_changes": StatCategory.SITUATIONAL,
            "altitude_difference": StatCategory.SITUATIONAL,
            
            # Injury Report Features
            "key_players_injured": StatCategory.INJURY_REPORTS,
            "injury_impact_score": StatCategory.INJURY_REPORTS,
            "starter_availability": StatCategory.INJURY_REPORTS,
            "depth_chart_changes": StatCategory.INJURY_REPORTS,
            
            # Weather Features
            "temperature": StatCategory.WEATHER,
            "wind_speed": StatCategory.WEATHER,
            "precipitation": StatCategory.WEATHER,
            "dome_vs_outdoor": StatCategory.WEATHER,
            
            # Momentum Features
            "current_streak": StatCategory.MOMENTUM,
            "momentum_score": StatCategory.MOMENTUM,
            "confidence_index": StatCategory.MOMENTUM,
            "media_sentiment": StatCategory.MOMENTUM
        }
    
    def get_weights_for_sport(self, sport: str) -> Dict[StatCategory, float]:
        """Get weights for a specific sport."""
        weights = self.default_weights.copy()
        if sport.lower() in self.sport_weights:
            weights.update(self.sport_weights[sport.lower()])
        
        # Normalize weights to ensure they sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def get_feature_weight(self, feature_name: str, sport: str) -> float:
        """Get the weight for a specific feature."""
        category = self.feature_categories.get(feature_name)
        if category is None:
            return 0.01  # Default low weight for unknown features
        
        sport_weights = self.get_weights_for_sport(sport)
        return sport_weights.get(category, 0.01)
    
    def get_weighted_features(self, features: Dict[str, float], sport: str) -> Dict[str, float]:
        """Apply weights to features and return weighted values."""
        weighted_features = {}
        
        for feature_name, feature_value in features.items():
            weight = self.get_feature_weight(feature_name, sport)
            weighted_features[feature_name] = feature_value * weight
        
        return weighted_features
    
    def update_sport_weights(self, sport: str, new_weights: Dict[StatCategory, float]):
        """Update weights for a specific sport."""
        if sport.lower() not in self.sport_weights:
            self.sport_weights[sport.lower()] = {}
        
        # Normalize new weights
        total_weight = sum(new_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in new_weights.items()}
            self.sport_weights[sport.lower()].update(normalized_weights)
    
    def add_feature_mapping(self, feature_name: str, category: StatCategory):
        """Add a new feature to category mapping."""
        self.feature_categories[feature_name] = category
    
    def get_category_importance_ranking(self, sport: str) -> List[tuple]:
        """Get categories ranked by importance for a sport."""
        weights = self.get_weights_for_sport(sport)
        return sorted(weights.items(), key=lambda x: x[1], reverse=True)


# Global weight configuration instance
weight_config = WeightConfig()
