from pydantic import BaseModel

class TaskRequest(BaseModel):
    text: str

class TaskResponse(BaseModel):
    result: str
    task_type: str
    region: str
    carbon_intensity: float
    carbon_saved: str
    response_time: float