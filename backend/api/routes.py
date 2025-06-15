from fastapi import APIRouter
from models.schemas import TaskRequest, TaskResponse
from services.task_classifier import classify_task
from services.region_router import select_optimal_region, get_region_carbon_data
from services.model_service import process_with_model

router = APIRouter()

@router.post("/process", response_model=TaskResponse)
async def process_task(request: TaskRequest):
    # 1. Classify the task
    task_type = classify_task(request.text)
    
    # 2. Select greenest region
    region = await select_optimal_region()
    
    # 3. Process with appropriate model
    result = await process_with_model(task_type, request.text)
    
    # 4. Get carbon impact data
    carbon_data = await get_region_carbon_data(region)
    
    return TaskResponse(
        result=result,
        task_type=task_type,
        region=region,
        carbon_intensity=carbon_data["carbon_intensity"],
        carbon_saved="Estimated 30% lower than average",  # You can calculate this properly later
        response_time=1.5  # Placeholder
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/regions/ranking")
async def get_regions_ranking():
    """Get all regions ranked by carbon intensity"""
    try:
        from services.carbon_service import EIACarbonService
        from config import settings
        
        carbon_service = EIACarbonService(settings.eia_api_key)
        rankings = await carbon_service.get_carbon_rankings()
        return {"rankings": rankings}
    except Exception as e:
        return {"error": str(e), "rankings": []}