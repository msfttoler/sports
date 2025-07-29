#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced weighted prediction system.
This script tests the new statistical weighting capabilities.
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.weights import WeightConfig, StatCategory
from shared.weighted_features import WeightedFeatureExtractor
from game_predictor import EnhancedGamePredictor


def test_weight_configuration():
    """Test the weight configuration system."""
    print("🔧 Testing Weight Configuration System")
    print("=" * 50)
    
    config = WeightConfig()
    
    # Test weight retrieval for different sports
    for sport in ["nfl", "nba", "mlb", "nhl"]:
        print(f"\n{sport.upper()} Weight Configuration:")
        weights = config.get_weights_for_sport(sport)
        
        for category, weight in weights.items():
            print(f"  {category.value:25} -> {weight:.2f}")
    
    # Test feature categorization
    print(f"\nFeature Categories (sample):")
    sample_features = [
        "recent_win_percentage", "historical_record", "home_field_advantage",
        "head_to_head_record", "injury_impact", "rest_advantage"
    ]
    
    for feature in sample_features:
        category = config.feature_categories.get(feature, "Unknown")
        weight = config.get_feature_weight(feature, "nfl")
        print(f"  {feature:25} -> {category.value:20} (weight: {weight:.2f})")


def test_weighted_feature_extraction():
    """Test the weighted feature extraction system."""
    print("\n🔍 Testing Weighted Feature Extraction")
    print("=" * 50)
    
    extractor = WeightedFeatureExtractor()
    
    # Mock team statistics for testing
    home_stats = {
        "wins": 10, "losses": 6, "points_for": 380, "points_against": 320,
        "recent_games": [1, 1, 0, 1, 1],  # Last 5: 4-1
        "home_wins": 6, "home_losses": 2,
        "offensive_yards": 5500, "defensive_yards": 5200
    }
    
    away_stats = {
        "wins": 8, "losses": 8, "points_for": 340, "points_against": 360,
        "recent_games": [0, 1, 0, 0, 1],  # Last 5: 2-3
        "away_wins": 4, "away_losses": 4,
        "offensive_yards": 5100, "defensive_yards": 5600
    }
    
    matchup_data = {
        "historical_games": [
            {"home_score": 24, "away_score": 21},
            {"home_score": 17, "away_score": 28},
            {"home_score": 31, "away_score": 14}
        ],
        "days_since_last_game": {"home": 7, "away": 6},
        "injury_report": {"home": 2, "away": 1}  # Number of key injuries
    }
    
    print("Extracting weighted features for NFL matchup...")
    
    # Extract features with weights
    weighted_features = extractor.extract_weighted_features(
        home_stats, away_stats, matchup_data, "nfl"
    )
    
    print(f"\nExtracted {len(weighted_features)} weighted features:")
    
    # Group and display features by category
    config = WeightConfig()
    categories = {}
    
    for feature_name, value in weighted_features.items():
        category = config.feature_categories.get(feature_name, StatCategory.RECENT_PERFORMANCE)
        if category not in categories:
            categories[category] = []
        categories[category].append((feature_name, value))
    
    for category, features in categories.items():
        print(f"\n{category.value} Features:")
        for name, value in sorted(features, key=lambda x: abs(x[1]), reverse=True)[:3]:
            print(f"  {name:30} -> {value:6.3f}")


async def test_enhanced_predictions():
    """Test the enhanced prediction system with weights."""
    print("\n🎯 Testing Enhanced Prediction System")
    print("=" * 50)
    
    predictor = EnhancedGamePredictor()
    
    # Initialize models (this will create mock models for testing)
    await predictor.load_models()
    
    # Test weight breakdown functionality
    print("Weight breakdown for NFL:")
    nfl_weights = predictor.get_weight_breakdown(sport="nfl")
    print(json.dumps(nfl_weights, indent=2))
    
    # Create a mock game for prediction testing
    mock_game = {
        "id": "test_game_001",
        "sport": "nfl",
        "home_team": "Team A",
        "away_team": "Team B",
        "status": "scheduled",
        "scheduled_date": datetime.utcnow().isoformat()
    }
    
    print(f"\nGenerating enhanced prediction for mock game...")
    
    # For this test, we'll simulate the prediction process
    extractor = WeightedFeatureExtractor()
    
    # Mock realistic team data
    home_stats = {
        "wins": 12, "losses": 4, "points_for": 420, "points_against": 280,
        "recent_games": [1, 1, 1, 1, 0],  # Strong recent form
        "home_wins": 7, "home_losses": 1,
        "offensive_yards": 6200, "defensive_yards": 4800
    }
    
    away_stats = {
        "wins": 9, "losses": 7, "points_for": 360, "points_against": 340,
        "recent_games": [1, 0, 1, 0, 1],  # Moderate recent form
        "away_wins": 5, "away_losses": 3,
        "offensive_yards": 5400, "defensive_yards": 5400
    }
    
    matchup_data = {
        "historical_games": [
            {"home_score": 28, "away_score": 17},
            {"home_score": 21, "away_score": 24},
            {"home_score": 35, "away_score": 14},
            {"home_score": 24, "away_score": 21}
        ],
        "days_since_last_game": {"home": 7, "away": 7},
        "injury_report": {"home": 1, "away": 3}
    }
    
    # Extract weighted features
    weighted_features = extractor.extract_weighted_features(
        home_stats, away_stats, matchup_data, "nfl"
    )
    
    # Make weighted prediction
    prediction = predictor._make_weighted_prediction("nfl", weighted_features)
    
    print(f"\nPrediction Results:")
    print(f"Outcome: {prediction['outcome']}")
    print(f"Confidence: {prediction['confidence']:.1f}%")
    print(f"Predicted Score: {prediction['home_score']}-{prediction['away_score']}")
    print(f"Win Probabilities: Home {prediction['win_probabilities']['home']}%, Away {prediction['win_probabilities']['away']}%")
    print(f"\nReasoning: {prediction['reasoning']}")
    
    # Show feature importance
    print(f"\nTop Feature Contributions:")
    feature_importance = prediction.get('feature_importance', {})
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    for feature, importance in sorted_features[:5]:
        print(f"  {feature:30} -> {importance:.3f}")
    
    # Show category contributions
    print(f"\nCategory Contributions:")
    category_contributions = prediction.get('category_contributions', {})
    sorted_categories = sorted(category_contributions.items(), key=lambda x: x[1], reverse=True)
    
    for category, contribution in sorted_categories[:5]:
        print(f"  {category:25} -> {contribution:.3f}")


def test_weight_comparison():
    """Test how different weight configurations affect predictions."""
    print("\n⚖️  Testing Weight Impact on Predictions")
    print("=" * 50)
    
    extractor = WeightedFeatureExtractor()
    config = WeightConfig()
    
    # Mock baseline team data
    home_stats = {
        "wins": 10, "losses": 6, "points_for": 380, "points_against": 320,
        "recent_games": [1, 1, 1, 0, 1],  # Good recent form
        "home_wins": 6, "home_losses": 2,
        "offensive_yards": 5500, "defensive_yards": 5200
    }
    
    away_stats = {
        "wins": 10, "losses": 6, "points_for": 370, "points_against": 340,
        "recent_games": [0, 0, 1, 1, 1],  # Mixed recent form
        "away_wins": 5, "away_losses": 3,
        "offensive_yards": 5300, "defensive_yards": 5400
    }
    
    matchup_data = {
        "historical_games": [{"home_score": 24, "away_score": 21}],
        "days_since_last_game": {"home": 7, "away": 7},
        "injury_report": {"home": 1, "away": 1}
    }
    
    print("Comparing weight impact across sports:")
    
    for sport in ["nfl", "nba"]:
        print(f"\n{sport.upper()} Weight Configuration:")
        
        weighted_features = extractor.extract_weighted_features(
            home_stats, away_stats, matchup_data, sport
        )
        
        # Show top weighted features
        sorted_features = sorted(weighted_features.items(), key=lambda x: abs(x[1]), reverse=True)
        
        print("Top 5 weighted features:")
        for name, value in sorted_features[:5]:
            category = config.feature_categories.get(name, StatCategory.RECENT_PERFORMANCE)
            weight = config.get_feature_weight(name, sport)
            print(f"  {name:25} -> {value:6.3f} (base weight: {weight:.2f}, category: {category.value})")


async def main():
    """Run all tests."""
    print("🏈 Enhanced Sports Prediction System - Weight Testing")
    print("=" * 60)
    
    try:
        test_weight_configuration()
        test_weighted_feature_extraction()
        await test_enhanced_predictions()
        test_weight_comparison()
        
        print("\n✅ All tests completed successfully!")
        print("\nKey Improvements with Weighted System:")
        print("• Statistical categories can be prioritized based on sport and context")
        print("• Recent performance vs historical data weighting")
        print("• Enhanced reasoning with weight explanations")
        print("• Feature importance tracking and analysis")
        print("• Sport-specific bias adjustments")
        print("• Configurable weight overrides for different scenarios")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
