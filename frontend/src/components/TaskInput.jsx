import { useState } from 'react'
import { processTask } from '@/lib/api'

export default function TaskInput({ onResult, onLoading }) {
  const [text, setText] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return

    onLoading(true)
    try {
      const result = await processTask(text)
      onResult(result)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      onLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter your task (grammar check, email draft, question)..."
        className="w-full p-4 border rounded-lg min-h-32"
      />
      <button 
        type="submit"
        className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
      >
        Process with Green AI
      </button>
    </form>
  )
}