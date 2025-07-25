"""
Shared utilities and configuration for the Sports Prediction System.
Handles Azure service connections, logging, and common functions.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.cosmos import CosmosClient, DatabaseProxy, ContainerProxy
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
import json


class Config:
    """Configuration management using environment variables and Key Vault."""
    
    def __init__(self):
        self.cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.keyvault_url = os.getenv("KEYVAULT_URL")
        self.storage_account_url = os.getenv("STORAGE_ACCOUNT_URL")
        self.ml_workspace_name = os.getenv("ML_WORKSPACE_NAME")
        self.sports_api_key = os.getenv("SPORTS_API_KEY")
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        
        # Initialize credential
        try:
            self.credential = ManagedIdentityCredential()
        except Exception:
            self.credential = DefaultAzureCredential()
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from Azure Key Vault."""
        if not self.keyvault_url:
            return None
        
        try:
            secret_client = SecretClient(
                vault_url=self.keyvault_url,
                credential=self.credential
            )
            secret = secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logging.error(f"Failed to retrieve secret {secret_name}: {e}")
            return None


class CosmosDBClient:
    """Azure Cosmos DB client with connection pooling and retry logic."""
    
    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._containers: Dict[str, ContainerProxy] = {}
        
    async def get_client(self) -> CosmosClient:
        """Get or create Cosmos DB client with managed identity."""
        if not self._client:
            try:
                self._client = CosmosClient(
                    url=self.config.cosmos_endpoint,
                    credential=self.config.credential,
                    connection_retry_policy={
                        "retry_count": 3,
                        "retry_interval": 2,
                        "max_retry_wait_time": 30
                    }
                )
                logging.info("Successfully connected to Cosmos DB")
            except Exception as e:
                logging.error(f"Failed to connect to Cosmos DB: {e}")
                raise
        return self._client
    
    async def get_database(self, database_name: str = "SportsData") -> DatabaseProxy:
        """Get or create database."""
        if not self._database:
            client = await self.get_client()
            self._database = client.get_database_client(database_name)
        return self._database
    
    async def get_container(self, container_name: str, partition_key: str = "/id") -> ContainerProxy:
        """Get or create container with caching."""
        if container_name not in self._containers:
            database = await self.get_database()
            try:
                self._containers[container_name] = database.get_container_client(container_name)
            except Exception:
                # Container doesn't exist, create it
                self._containers[container_name] = database.create_container(
                    id=container_name,
                    partition_key={"paths": [partition_key], "kind": "Hash"}
                )
                logging.info(f"Created container: {container_name}")
        return self._containers[container_name]
    
    async def upsert_item(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert item to container with retry logic."""
        container = await self.get_container(container_name)
        
        for attempt in range(3):
            try:
                result = container.upsert_item(item)
                return result
            except Exception as e:
                if attempt == 2:
                    logging.error(f"Failed to upsert item after 3 attempts: {e}")
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def query_items(self, container_name: str, query: str, parameters: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query items from container."""
        container = await self.get_container(container_name)
        
        try:
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            return items
        except Exception as e:
            logging.error(f"Failed to query items: {e}")
            raise


class Logger:
    """Enhanced logging configuration for Azure Functions."""
    
    @staticmethod
    def setup_logging():
        """Configure logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        # Suppress verbose Azure SDK logs
        logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
        logging.getLogger('azure.cosmos').setLevel(logging.WARNING)


class DataValidator:
    """Data validation and cleaning utilities."""
    
    @staticmethod
    def validate_game_data(game_data: Dict[str, Any]) -> bool:
        """Validate game data structure."""
        required_fields = ["id", "sport", "home_team", "away_team", "scheduled_date"]
        return all(field in game_data for field in required_fields)
    
    @staticmethod
    def clean_team_name(name: str) -> str:
        """Clean and normalize team names."""
        if not name:
            return ""
        return name.strip().title()
    
    @staticmethod
    def normalize_score(score: Any) -> Optional[int]:
        """Normalize score values."""
        if score is None:
            return None
        try:
            return int(float(score))
        except (ValueError, TypeError):
            return None


class APIClient:
    """Generic API client with retry logic and rate limiting."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make GET request with retry logic."""
        import aiohttp
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        if not headers:
            headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        for attempt in range(3):
            try:
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        response.raise_for_status()
            except Exception as e:
                if attempt == 2:
                    logging.error(f"API request failed after 3 attempts: {e}")
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class FeatureExtractor:
    """Extract ML features from sports data."""
    
    @staticmethod
    def extract_team_features(team_stats: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract features for a team."""
        features = {}
        
        # Basic stats
        games_played = team_stats.get("games_played", 0)
        if games_played > 0:
            features["win_percentage"] = team_stats.get("wins", 0) / games_played
            features["points_per_game"] = team_stats.get("points_for", 0) / games_played
            features["points_allowed_per_game"] = team_stats.get("points_against", 0) / games_played
            features["point_differential"] = features["points_per_game"] - features["points_allowed_per_game"]
        
        # Recent form (last 5 games)
        if recent_games:
            recent_wins = sum(1 for game in recent_games[-5:] if game.get("result") == "W")
            features["recent_win_percentage"] = recent_wins / min(5, len(recent_games))
        
        # Home/Away splits
        home_games = team_stats.get("home_record", {}).get("games", 0)
        if home_games > 0:
            features["home_win_percentage"] = team_stats.get("home_record", {}).get("wins", 0) / home_games
        
        return features
    
    @staticmethod
    def extract_matchup_features(home_team_id: str, away_team_id: str, historical_games: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract head-to-head matchup features."""
        features = {}
        
        if not historical_games:
            return features
        
        home_wins = sum(1 for game in historical_games 
                       if game.get("home_team_id") == home_team_id and 
                       game.get("home_score", 0) > game.get("away_score", 0))
        
        features["historical_home_win_rate"] = home_wins / len(historical_games)
        features["games_played_h2h"] = len(historical_games)
        
        # Average score differential
        score_diffs = []
        for game in historical_games:
            if game.get("home_team_id") == home_team_id:
                diff = game.get("home_score", 0) - game.get("away_score", 0)
            else:
                diff = game.get("away_score", 0) - game.get("home_score", 0)
            score_diffs.append(diff)
        
        if score_diffs:
            features["avg_score_differential_h2h"] = sum(score_diffs) / len(score_diffs)
        
        return features


# Initialize global instances
config = Config()
cosmos_client = CosmosDBClient(config)
Logger.setup_logging()
