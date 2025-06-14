from fastapi import APIRouter
from models.schemas import TaskRequest, TaskResponse
from services.task_classifier import classify_task
from services.region_router import select_optimal_region
from services.model_service import process_with_model
from services.carbon_service import calculate_carbon_impact

router = APIRouter()

@router.post("/process", response_model=TaskResponse)
async def process_task(request: TaskRequest):
    # 1. Classify the task
    task_type = classify_task(request.text)
    
    # 2. Select greenest region
    region = select_optimal_region()
    
    # 3. Process with appropriate model
    result = await process_with_model(task_type, request.text)
    
    # 4. Calculate carbon impact
    carbon_data = calculate_carbon_impact(task_type, region)
    
    return TaskResponse(
        result=result,
        task_type=task_type,
        region=region,
        **carbon_data
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy"}