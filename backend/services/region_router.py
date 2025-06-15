import logging
from typing import Optional
from .carbon_service import EIACarbonService
from config import settings

logger = logging.getLogger(__name__)

async def select_optimal_region() -> str:
    """Select the optimal GCP region based on carbon intensity"""
    try:
        # Initialize carbon service
        carbon_service = EIACarbonService(settings.eia_api_key)
        
        # Get the greenest region
        greenest_region = await carbon_service.get_greenest_region()
        
        if greenest_region:
            logger.info(f"Selected greenest region: {greenest_region}")
            return greenest_region
        else:
            logger.warning("Could not determine greenest region, using fallback")
            return "us-west1"  # Fallback to Oregon (typically clean)
            
    except Exception as e:
        logger.error(f"Error selecting optimal region: {e}")
        # Fallback to a known clean region
        return "us-west1"  # Oregon - typically has low carbon intensity

async def get_region_carbon_data(region: str) -> dict:
    """Get carbon intensity data for a specific region"""
    try:
        carbon_service = EIACarbonService(settings.eia_api_key)
        carbon_data = await carbon_service.get_region_carbon_intensity(region)
        
        if carbon_data:
            return {
                "carbon_intensity": carbon_data["carbon_intensity"],
                "renewable_percent": carbon_data["renewable_percent"],
                "balancing_authority": carbon_data["balancing_authority"],
                "data_hour": carbon_data["data_hour"]
            }
        else:
            # Return estimated values if API fails
            return {
                "carbon_intensity": 350.0,  # Moderate estimate
                "renewable_percent": 30.0,
                "balancing_authority": "unknown",
                "data_hour": "estimated"
            }
            
    except Exception as e:
        logger.error(f"Error getting carbon data for {region}: {e}")
        # Return fallback values
        return {
            "carbon_intensity": 350.0,
            "renewable_percent": 30.0,
            "balancing_authority": "unknown", 
            "data_hour": "error"
        }