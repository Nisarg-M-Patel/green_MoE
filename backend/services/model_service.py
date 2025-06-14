import httpx
from config import settings

async def process_with_model(task_type: str, text: str) -> str:
    """Route to appropriate AI model based on task type"""
    
    if task_type == "grammar":
        return await call_huggingface_model(
            "pszemraj/flan-t5-large-grammar-synthesis", 
            text
        )
    elif task_type == "email":
        return await call_huggingface_model(
            "google/flan-t5-base", 
            f"Write a professional email: {text}"
        )
    elif task_type == "search":
        # Placeholder for search functionality
        return f"Search results for: {text}"
    
async def call_huggingface_model(model_name: str, text: str) -> str:
    """Call Hugging Face Inference API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{model_name}",
            headers={"Authorization": f"Bearer {settings.huggingface_token}"},
            json={"inputs": text}
        )
        result = response.json()
        return result[0]["generated_text"] if result else "Error processing request"