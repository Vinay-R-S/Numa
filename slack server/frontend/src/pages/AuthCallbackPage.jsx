/**
 * OAuth callback page — handles ?token= redirect from backend.
 */
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Spinner } from '../components/ui'

export default function AuthCallbackPage() {
  const [params]  = useSearchParams()
  const navigate  = useNavigate()
  const { setToken, fetchMe } = useAuthStore()

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      navigate('/login', { replace: true })
      return
    }
    setToken(token)
    fetchMe().then(() => navigate('/dashboard', { replace: true }))
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-4">
        <Spinner size={32} />
        <p className="text-sm text-gray-500">Signing you in…</p>
      </div>
    </div>
  )
}
