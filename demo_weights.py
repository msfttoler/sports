#!/usr/bin/env python3
"""
Simple demonstration of the weighted prediction system.
"""

import sys
import json
import asyncio
sys.path.append('.')

from shared.weights import WeightConfig, StatCategory
from shared.weighted_features import WeightedFeatureExtractor


def demo_weights():
    """Demonstrate the weight configuration system."""
    print("🏈 Enhanced Sports Prediction System - Weighted Statistics")
    print("=" * 60)
    
    config = WeightConfig()
    
    print("\n📊 Weight Configuration by Sport:")
    print("-" * 40)
    
    for sport in ["nfl", "nba", "mlb", "nhl"]:
        print(f"\n{sport.upper()} Statistical Category Weights:")
        weights = config.get_weights_for_sport(sport)
        
        # Sort by weight value (highest first)
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        for category, weight in sorted_weights:
            bar = "█" * int(weight * 50)  # Visual bar representation
            print(f"  {category.value:25} {weight:5.2f} {bar}")


async def demo_feature_extraction():
    """Demonstrate weighted feature extraction."""
    print("\n🔍 Weighted Feature Extraction Demo:")
    print("-" * 40)
    
    extractor = WeightedFeatureExtractor()
    
    # Example: Strong home team vs weak away team
    home_stats = {
        "wins": 12, "losses": 4, "points_for": 420, "points_against": 280,
        "recent_games": [1, 1, 1, 1, 0],  # 4-1 in last 5
        "home_wins": 7, "home_losses": 1,
        "offensive_yards": 6200, "defensive_yards": 4800
    }
    
    away_stats = {
        "wins": 6, "losses": 10, "points_for": 300, "points_against": 380,
        "recent_games": [0, 0, 1, 0, 0],  # 1-4 in last 5
        "away_wins": 3, "away_losses": 5,
        "offensive_yards": 4800, "defensive_yards": 5800
    }
    
    matchup_data = {
        "historical_games": [
            {"home_score": 28, "away_score": 17},
            {"home_score": 21, "away_score": 14},
            {"home_score": 35, "away_score": 10}
        ],
        "days_since_last_game": {"home": 7, "away": 6},
        "injury_report": {"home": 1, "away": 4}  # Away team has more injuries
    }
    
    print("\nExtracting features for NFL matchup...")
    print("Home Team: 12-4 (Strong), Away Team: 6-10 (Weak)")
    
    weighted_features = await extractor.extract_weighted_game_features(
        home_stats, away_stats, matchup_data, "nfl"
    )
    
    # Group features by category for better presentation
    config = WeightConfig()
    categories = {}
    
    for feature_name, value in weighted_features.items():
        category = config.feature_categories.get(feature_name, StatCategory.RECENT_PERFORMANCE)
        if category not in categories:
            categories[category] = []
        categories[category].append((feature_name, value))
    
    print(f"\nGenerated {len(weighted_features)} weighted features:")
    
    # Show top features per category
    for category, features in categories.items():
        if features:  # Only show categories that have features
            print(f"\n{category.value} (Weight: {config.get_weights_for_sport('nfl')[category]:.2f}):")
            # Sort by absolute value to show most impactful features
            sorted_features = sorted(features, key=lambda x: abs(x[1]), reverse=True)
            for name, value in sorted_features[:2]:  # Show top 2 per category
                direction = "+" if value > 0 else ""
                print(f"  {name:30} -> {direction}{value:6.3f}")


async def demo_weight_impact():
    """Show how weights affect different sports."""
    print("\n⚖️  Weight Impact Across Sports:")
    print("-" * 40)
    
    config = WeightConfig()
    extractor = WeightedFeatureExtractor()
    
    # Same team stats for all sports (normalized)
    home_stats = {
        "wins": 10, "losses": 6, "points_for": 100, "points_against": 90,
        "recent_games": [1, 1, 0, 1, 1],  # 4-1 recent
        "home_wins": 6, "home_losses": 2,
        "offensive_yards": 1000, "defensive_yards": 900
    }
    
    away_stats = {
        "wins": 8, "losses": 8, "points_for": 95, "points_against": 100,
        "recent_games": [0, 1, 0, 0, 1],  # 2-3 recent
        "away_wins": 4, "away_losses": 4,
        "offensive_yards": 950, "defensive_yards": 1050
    }
    
    matchup_data = {
        "historical_games": [{"home_score": 105, "away_score": 95}],
        "days_since_last_game": {"home": 7, "away": 7},
        "injury_report": {"home": 1, "away": 2}
    }
    
    print("\nSame team matchup weighted differently by sport:")
    
    for sport in ["nfl", "nba"]:
        weighted_features = await extractor.extract_weighted_game_features(
            home_stats, away_stats, matchup_data, sport
        )
        
        # Calculate overall advantage
        total_advantage = sum(weighted_features.values())
        
        print(f"\n{sport.upper()}:")
        print(f"  Overall weighted advantage: {total_advantage:+.3f}")
        
        # Show which categories matter most for this sport
        sport_weights = config.get_weights_for_sport(sport)
        top_categories = sorted(sport_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        
        print("  Top priority categories:")
        for category, weight in top_categories:
            print(f"    {category.value:25} -> {weight:.2f}")


def demo_key_improvements():
    """Highlight the key improvements in the weighted system."""
    print("\n✨ Key Improvements with Weighted Statistics:")
    print("=" * 50)
    
    improvements = [
        ("🎯 Configurable Priorities", "Different sports can prioritize different statistical categories"),
        ("📈 Recent vs Historical", "Adjust importance of recent form vs long-term performance"),
        ("🏠 Context Awareness", "Home field advantage, head-to-head, and situational factors"),
        ("🔍 Feature Importance", "Track which statistics contribute most to each prediction"),
        ("📊 Category Breakdown", "See how each statistical category influences outcomes"),
        ("⚙️  Sport-Specific Tuning", "NFL emphasizes H2H, NBA emphasizes recent performance"),
        ("🎪 Enhanced Reasoning", "Explanations include weight impact and feature importance"),
        ("🔧 API Extensions", "New endpoints for weight configuration and breakdowns")
    ]
    
    for title, description in improvements:
        print(f"\n{title}")
        print(f"   {description}")
    
    print(f"\n🚀 Next Steps for Further Enhancement:")
    print("   • Machine learning weight optimization based on historical accuracy")
    print("   • Dynamic weight adjustment based on game context and time of season")
    print("   • Player-level statistical integration with injury impact weighting")
    print("   • Real-time weight adjustment based on live game conditions")


async def main():
    demo_weights()
    await demo_feature_extraction()
    await demo_weight_impact()
    demo_key_improvements()
    print("\n🎉 Weighted Prediction System Demo Complete!")

if __name__ == "__main__":
    asyncio.run(main())
