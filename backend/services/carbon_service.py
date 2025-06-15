import asyncio
import httpx
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class FuelGeneration:
    fuel_type: str
    generation_mwh: float
    percentage: float

@dataclass
class CarbonReading:
    gcp_region: str
    balancing_authority: str
    carbon_intensity: float  # gCO2/kWh
    renewable_percent: float
    fuel_mix: List[FuelGeneration]
    timestamp: datetime
    data_hour: str  # Hour the grid data represents

class EIACarbonService:
    def __init__(self, eia_api_key: str = None):
        self.eia_api_key = eia_api_key or os.getenv('EIA_API_KEY')
        if not self.eia_api_key:
            raise ValueError("EIA API key required. Get free key at https://www.eia.gov/opendata/")
        
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)  # EIA updates hourly, cache for 30min
        
        # EPA emission factors (lbs CO2/MWh) - Updated to match EIA API fuel codes
        # Source: EPA eGRID 2021 data
        self.emission_factors = {
            # EIA fuel codes
            "col": 2249,      # coal
            "pet": 1672,      # petroleum  
            "ng": 898,        # natural gas
            "oth": 500,       # other/unknown - conservative estimate
            "nuc": 0,         # nuclear
            "wat": 0,         # conventional hydroelectric (water)
            "ps": 0,          # pumped storage hydro
            "wnd": 0,         # wind
            "sun": 0,         # solar
            "geo": 0,         # geothermal
            "bio": 230,       # biomass - some emissions
            "bat": 0,         # battery storage (assume grid-charged, no direct emissions)
            
            # Alternative spellings that might appear
            "oil": 1672,      # oil (same as petroleum)
            "gas": 898,       # gas (same as natural gas)
            "hydro": 0,       # hydroelectric
            "wind": 0,        # wind (alternative spelling)
            "solar": 0,       # solar (alternative spelling)
            "nuclear": 0,     # nuclear (alternative spelling)
            "coal": 2249,     # coal (alternative spelling)
            "natural_gas": 898, # natural gas (alternative spelling)
            "biomass": 230,   # biomass (alternative spelling)
            "geothermal": 0,  # geothermal (alternative spelling)
            "other": 500,     # fallback
        }
        
        # Map GCP regions to EIA balancing authorities
        # Based on actual datacenter locations
        self.gcp_to_eia_mapping = {
            # West Coast
            "us-west1": {  # Oregon (The Dalles)
                "balancing_authority": "BPAT",  # Bonneville Power Administration
                "region_name": "Pacific Northwest"
            },
            "us-west2": {  # Los Angeles
                "balancing_authority": "CISO",  # California ISO
                "region_name": "California"
            },
            "us-west3": {  # Salt Lake City  
                "balancing_authority": "PACE",  # PacifiCorp East
                "region_name": "Utah"
            },
            "us-west4": {  # Las Vegas
                "balancing_authority": "NEVP",  # Nevada Power
                "region_name": "Nevada"
            },
            
            # Central
            "us-central1": {  # Iowa (Council Bluffs)
                "balancing_authority": "MISO",  # Midcontinent ISO
                "region_name": "Iowa/MISO"
            },
            "us-south1": {  # Dallas, Texas
                "balancing_authority": "ERCO",  # ERCOT
                "region_name": "Texas"
            },
            
            # East Coast
            "us-east1": {  # South Carolina (Moncks Corner)
                "balancing_authority": "SCEG",  # South Carolina Electric & Gas
                "region_name": "Southeast"
            },
            "us-east4": {  # Virginia (Ashburn)
                "balancing_authority": "PJM",   # PJM Interconnection
                "region_name": "Mid-Atlantic"
            },
            "us-east5": {  # Ohio (Columbus)
                "balancing_authority": "PJM",   # PJM Interconnection  
                "region_name": "Ohio Valley"
            }
        }

    async def get_all_regions_carbon_intensity(self) -> List[CarbonReading]:
        """Get carbon intensity for all GCP regions using EIA data"""
        tasks = []
        
        for gcp_region in self.gcp_to_eia_mapping.keys():
            tasks.append(self._get_region_carbon_reading(gcp_region))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        readings = []
        for result in results:
            if isinstance(result, CarbonReading):
                readings.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Failed to get carbon data for region: {result}")
                
        # Sort by carbon intensity (greenest first)
        return sorted(readings, key=lambda x: x.carbon_intensity)

    async def _get_region_carbon_reading(self, gcp_region: str) -> Optional[CarbonReading]:
        """Get carbon intensity for a specific GCP region"""
        
        # Check cache first
        cache_key = f"carbon_{gcp_region}"
        if cache_key in self.cache:
            cached_reading, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_reading
        
        region_config = self.gcp_to_eia_mapping.get(gcp_region)
        if not region_config:
            logger.warning(f"No EIA mapping for GCP region: {gcp_region}")
            return None
            
        # Get fuel mix from EIA API
        fuel_mix = await self._fetch_eia_fuel_mix(region_config["balancing_authority"])
        
        if not fuel_mix:
            logger.warning(f"No fuel mix data for {gcp_region}")
            return None
            
        # Calculate carbon intensity and renewable percentage
        carbon_intensity = self._calculate_carbon_intensity(fuel_mix)
        renewable_percent = self._calculate_renewable_percentage(fuel_mix)
        
        # Get the most recent data hour
        data_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        
        reading = CarbonReading(
            gcp_region=gcp_region,
            balancing_authority=region_config["balancing_authority"],
            carbon_intensity=carbon_intensity,
            renewable_percent=renewable_percent,
            fuel_mix=fuel_mix,
            timestamp=datetime.now(),
            data_hour=data_hour
        )
        
        # Cache the result
        self.cache[cache_key] = (reading, datetime.now())
        return reading

    async def _fetch_eia_fuel_mix(self, balancing_authority: str) -> Optional[List[FuelGeneration]]:
        """Fetch hourly fuel mix from EIA API for a balancing authority"""
        try:
            async with httpx.AsyncClient() as client:
                # EIA API v2 endpoint for electricity generation by fuel type
                url = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
                
                # Get the last 24 hours of data to find most recent
                params = {
                    "api_key": self.eia_api_key,
                    "frequency": "hourly",
                    "data[0]": "value",  # Generation value in MWh
                    "facets[respondent][]": balancing_authority,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 100  # Get recent data across all fuel types
                }
                
                response = await client.get(url, params=params, timeout=15)
                
                if response.status_code != 200:
                    logger.error(f"EIA API error {response.status_code} for {balancing_authority}")
                    return None
                    
                data = response.json()
                
                # Parse EIA response into fuel mix
                return self._parse_eia_response(data)
                
        except Exception as e:
            logger.error(f"EIA API request failed for {balancing_authority}: {e}")
            return None

    def _parse_eia_response(self, eia_data: dict) -> List[FuelGeneration]:
        """Parse EIA API response into fuel generation data"""
        if not eia_data.get("response", {}).get("data"):
            return []
            
        # Group by fuel type and get most recent hour for each fuel
        fuel_data = {}
        
        for record in eia_data["response"]["data"]:
            fuel_type = record.get("fueltype", "unknown").lower().replace("-", "_")
            generation_mwh = record.get("value", 0) or 0  # Handle None values
            period = record.get("period", "")
            
            # Keep most recent data for each fuel type
            if fuel_type not in fuel_data or period > fuel_data[fuel_type]["period"]:
                fuel_data[fuel_type] = {
                    "generation": float(generation_mwh),
                    "period": period
                }
        
        # Calculate total generation and percentages
        total_generation = sum(data["generation"] for data in fuel_data.values())
        
        if total_generation == 0:
            logger.warning("Zero total generation found in EIA data")
            return []
        
        # Create fuel generation objects
        fuel_mix = []
        for fuel_type, data in fuel_data.items():
            generation = data["generation"]
            percentage = (generation / total_generation) * 100
            
            fuel_mix.append(FuelGeneration(
                fuel_type=fuel_type,
                generation_mwh=generation,
                percentage=percentage
            ))
        
        # Sort by generation amount (largest first)
        return sorted(fuel_mix, key=lambda x: x.generation_mwh, reverse=True)

    def _calculate_carbon_intensity(self, fuel_mix: List[FuelGeneration]) -> float:
        """Calculate carbon intensity from fuel mix using EPA emission factors"""
        total_generation = sum(fuel.generation_mwh for fuel in fuel_mix)
        
        if total_generation == 0:
            return 500.0  # Default moderate value
            
        weighted_emissions = 0.0
        
        for fuel in fuel_mix:
            # Use the fuel type directly (already cleaned in parsing)
            fuel_key = fuel.fuel_type.lower()
            
            # Get emission factor - now matches EIA codes
            emission_factor = self.emission_factors.get(fuel_key, 500)
            
            # Weight by generation share
            weight = fuel.generation_mwh / total_generation
            weighted_emissions += emission_factor * weight
        
        # Convert from lbs CO2/MWh to gCO2/kWh
        # 1 lb = 453.592 grams, 1 MWh = 1000 kWh
        carbon_intensity_g_per_kwh = (weighted_emissions * 453.592) / 1000
        
        return round(carbon_intensity_g_per_kwh, 1)

    def _calculate_renewable_percentage(self, fuel_mix: List[FuelGeneration]) -> float:
        """Calculate percentage of renewable generation - Updated for EIA codes"""
        # Updated to use EIA fuel codes
        renewable_fuels = {
            "wnd",    # wind
            "sun",    # solar  
            "wat",    # conventional hydroelectric
            "ps",     # pumped storage hydro
            "geo",    # geothermal
            "bio",    # biomass (technically renewable)
            # Alternative spellings that might appear
            "wind", "solar", "hydro", "geothermal", "biomass"
        }
        
        total_generation = sum(fuel.generation_mwh for fuel in fuel_mix)
        renewable_generation = sum(
            fuel.generation_mwh for fuel in fuel_mix 
            if fuel.fuel_type.lower() in renewable_fuels
        )
        
        if total_generation == 0:
            return 0.0
            
        return round((renewable_generation / total_generation) * 100, 1)

    async def get_greenest_region(self) -> Optional[str]:
        """Get the GCP region with the lowest carbon intensity"""
        readings = await self.get_all_regions_carbon_intensity()
        return readings[0].gcp_region if readings else None

    async def get_carbon_rankings(self) -> List[Dict]:
        """Get all regions ranked by carbon intensity (greenest first)"""
        readings = await self.get_all_regions_carbon_intensity()
        
        rankings = []
        for idx, reading in enumerate(readings):
            rankings.append({
                "rank": idx + 1,
                "gcp_region": reading.gcp_region,
                "balancing_authority": reading.balancing_authority,
                "carbon_intensity": reading.carbon_intensity,
                "renewable_percent": reading.renewable_percent,
                "data_hour": reading.data_hour,
                "fuel_mix": [
                    {
                        "fuel": fuel.fuel_type,
                        "generation_mwh": fuel.generation_mwh,
                        "percentage": fuel.percentage
                    }
                    for fuel in reading.fuel_mix[:5]  # Top 5 fuel sources
                ]
            })
            
        return rankings

    async def get_region_carbon_intensity(self, gcp_region: str) -> Optional[Dict]:
        """Get carbon intensity for a specific GCP region"""
        reading = await self._get_region_carbon_reading(gcp_region)
        
        if not reading:
            return None
            
        return {
            "gcp_region": reading.gcp_region,
            "balancing_authority": reading.balancing_authority, 
            "carbon_intensity": reading.carbon_intensity,
            "renewable_percent": reading.renewable_percent,
            "data_hour": reading.data_hour,
            "fuel_mix": [
                {
                    "fuel": fuel.fuel_type,
                    "generation_mwh": fuel.generation_mwh,
                    "percentage": fuel.percentage
                }
                for fuel in reading.fuel_mix
            ]
        }

# Example usage and testing
async def test_carbon_service():
    """Test the EIA carbon service"""
    # You need to set EIA_API_KEY environment variable
    # Get free key at: https://www.eia.gov/opendata/
    
    service = EIACarbonService()
    
    print("Testing EIA Carbon Intensity Service")
    print("=" * 50)
    
    # Test single region
    print("\n1. Testing California (us-west2):")
    ca_data = await service.get_region_carbon_intensity("us-west2")
    if ca_data:
        print(f"   Carbon Intensity: {ca_data['carbon_intensity']} gCO2/kWh")
        print(f"   Renewable Percent: {ca_data['renewable_percent']}%")
        top_fuels = [f"{fuel['fuel']}: {fuel['percentage']:.1f}%" for fuel in ca_data['fuel_mix'][:3]]
        print(f"   Top fuels: {top_fuels}")
    
    # Test all regions ranking
    print("\n2. All regions ranking (greenest first):")
    rankings = await service.get_carbon_rankings()
    
    for rank in rankings:
        print(f"   {rank['rank']}. {rank['gcp_region']} ({rank['balancing_authority']}): "
              f"{rank['carbon_intensity']} gCO2/kWh ({rank['renewable_percent']}% renewable)")
    
    # Get greenest region
    greenest = await service.get_greenest_region()
    print(f"\n3. Greenest region right now: {greenest}")

if __name__ == "__main__":
    # To run this test:
    # 1. Get free EIA API key at https://www.eia.gov/opendata/
    # 2. Set environment variable: export EIA_API_KEY="your_key_here"
    # 3. Run: python carbon_service.py
    
    asyncio.run(test_carbon_service())