'use client'
import { useState } from 'react'
import TaskInput from '@/components/TaskInput'
import ResultDisplay from '@/components/ResultDisplay'
import CarbonMetrics from '@/components/CarbonMetrics'

export default function Home() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Green AI Router</h1>
      <p className="text-gray-600 mb-8">
        AI tasks routed to the greenest datacenters available
      </p>
      
      <TaskInput 
        onResult={setResult} 
        onLoading={setLoading} 
      />
      
      {loading && (
        <div className="mt-6 text-center">Processing with green energy...</div>
      )}
      
      {result && (
        <div className="mt-6 space-y-4">
          <ResultDisplay result={result} />
          <CarbonMetrics data={result} />
        </div>
      )}
    </main>
  )
}