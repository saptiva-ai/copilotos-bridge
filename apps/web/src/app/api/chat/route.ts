import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // Get the API base URL from environment
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Forward the request to the backend API
    const response = await fetch(`${apiBaseUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`)
    }

    const data = await response.json()

    // Return the response from the backend
    return NextResponse.json(data)
  } catch (error) {
    console.error('API route error:', error)
    return NextResponse.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    )
  }
}