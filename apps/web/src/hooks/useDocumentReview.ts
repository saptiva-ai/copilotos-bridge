/**
 * useDocumentReview - Hook for document upload and review management
 */

import { useState, useCallback } from 'react'
import { useApiClient } from '../lib/api-client'

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

export interface DocumentMetadata {
  docId: string
  filename: string
  totalPages: number
  status: string
}

export interface ReviewJob {
  jobId: string
  status: string
  progress: number
  currentStage?: string
  errorMessage?: string
}

export interface UseDocumentReviewReturn {
  // Upload
  uploadFile: (file: File, conversationId?: string) => Promise<DocumentMetadata | null>
  uploadProgress: UploadProgress | null
  isUploading: boolean

  // Review
  startReview: (docId: string, options?: ReviewOptions) => Promise<string | null>
  getReviewStatus: (jobId: string) => Promise<ReviewJob | null>
  getReviewReport: (docId: string) => Promise<any | null>

  // State
  error: string | null
  clearError: () => void
}

export interface ReviewOptions {
  model?: string
  rewritePolicy?: 'conservative' | 'moderate' | 'aggressive'
  summary?: boolean
  colorAudit?: boolean
}

export function useDocumentReview(): UseDocumentReviewReturn {
  const apiClient = useApiClient()

  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const uploadFile = useCallback(
    async (file: File, conversationId?: string): Promise<DocumentMetadata | null> => {
      setError(null)
      setIsUploading(true)
      setUploadProgress({ loaded: 0, total: file.size, percentage: 0 })

      try {
        // Create FormData
        const formData = new FormData()
        formData.append('file', file)
        if (conversationId) {
          formData.append('conversation_id', conversationId)
        }

        // Upload with progress
        const response = await fetch('/api/documents/upload', {
          method: 'POST',
          body: formData,
          headers: {
            Authorization: `Bearer ${apiClient.getToken()}`,
          },
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Upload failed')
        }

        const data = await response.json()

        setUploadProgress({ loaded: file.size, total: file.size, percentage: 100 })

        return {
          docId: data.doc_id,
          filename: data.filename,
          totalPages: data.total_pages,
          status: data.status,
        }
      } catch (err: any) {
        setError(err.message || 'Failed to upload file')
        return null
      } finally {
        setIsUploading(false)
      }
    },
    [apiClient]
  )

  const startReview = useCallback(
    async (docId: string, options: ReviewOptions = {}): Promise<string | null> => {
      setError(null)

      try {
        const response = await fetch('/api/review/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiClient.getToken()}`,
          },
          body: JSON.stringify({
            doc_id: docId,
            model: options.model || 'Saptiva Turbo',
            rewrite_policy: options.rewritePolicy || 'conservative',
            summary: options.summary !== false,
            color_audit: options.colorAudit !== false,
          }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Failed to start review')
        }

        const data = await response.json()
        return data.job_id
      } catch (err: any) {
        setError(err.message || 'Failed to start review')
        return null
      }
    },
    [apiClient]
  )

  const getReviewStatus = useCallback(
    async (jobId: string): Promise<ReviewJob | null> => {
      try {
        const response = await fetch(`/api/review/status/${jobId}`, {
          headers: {
            Authorization: `Bearer ${apiClient.getToken()}`,
          },
        })

        if (!response.ok) {
          throw new Error('Failed to get review status')
        }

        const data = await response.json()
        return {
          jobId: data.job_id,
          status: data.status,
          progress: data.progress,
          currentStage: data.current_stage,
          errorMessage: data.error_message,
        }
      } catch (err: any) {
        setError(err.message || 'Failed to get status')
        return null
      }
    },
    [apiClient]
  )

  const getReviewReport = useCallback(
    async (docId: string): Promise<any | null> => {
      try {
        const response = await fetch(`/api/review/report/${docId}`, {
          headers: {
            Authorization: `Bearer ${apiClient.getToken()}`,
          },
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Failed to get report')
        }

        const data = await response.json()
        return data
      } catch (err: any) {
        setError(err.message || 'Failed to get report')
        return null
      }
    },
    [apiClient]
  )

  return {
    uploadFile,
    uploadProgress,
    isUploading,
    startReview,
    getReviewStatus,
    getReviewReport,
    error,
    clearError,
  }
}
