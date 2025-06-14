const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function processTask(text) {
  const response = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    throw new Error('Failed to process task')
  }

  return response.json()
}