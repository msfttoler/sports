import logging
import json
import azure.functions as func
from typing import Dict, Any

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for testing and monitoring
    
    Returns:
        func.HttpResponse: Health status of the service
    """
    logging.info('Health check endpoint called')
    
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": func.DateTime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "Sports Prediction System",
            "checks": {
                "api": "ok",
                "functions": "ok"
            }
        }
        
        # Additional health checks could be added here:
        # - Database connectivity
        # - External API availability
        # - Memory/CPU usage
        
        return func.HttpResponse(
            json.dumps(health_status),
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        
        error_status = {
            "status": "unhealthy",
            "timestamp": func.DateTime.utcnow().isoformat(),
            "error": "Health check failed",
            "service": "Sports Prediction System"
        }
        
        return func.HttpResponse(
            json.dumps(error_status),
            status_code=503,
            headers={'Content-Type': 'application/json'}
        )
