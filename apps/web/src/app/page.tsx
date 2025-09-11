import { MODELS } from '@copilotos/shared'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-4xl font-bold text-center text-gray-900 mb-8">
          CopilotOS Bridge
        </h1>
        <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Welcome to Chat UI + Aletheia Deep Research
          </h2>
          <p className="text-gray-600 mb-6">
            A unified conversational interface combining direct LLM interactions 
            with deep research capabilities powered by Aletheia orchestrator.
          </p>
          
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-800">Available Models:</h3>
            <ul className="space-y-2">
              <li className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-gray-700">{MODELS.SAPTIVA.CORTEX}</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-gray-700">{MODELS.SAPTIVA.OPS}</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-gray-700">{MODELS.SAPTIVA.NEXUS}</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">🚀 Setup Status</h4>
            <p className="text-blue-800 text-sm">
              Project scaffold is complete. Next steps:
            </p>
            <ol className="text-blue-800 text-sm mt-2 space-y-1 list-decimal list-inside">
              <li>Configure environment variables</li>
              <li>Set up database and Redis</li>
              <li>Start Aletheia orchestrator</li>
              <li>Implement chat components</li>
            </ol>
          </div>
        </div>
      </div>
    </main>
  )
}