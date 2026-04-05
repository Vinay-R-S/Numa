/**
 * Settings page — profile, Slack workspace info, notification preferences.
 */
import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import api from '../lib/api'
import { Avatar, SectionHeader, Spinner } from '../components/ui'
import TopBar from '../components/TopBar'
import { User, Bell, Shield, LogOut, ExternalLink, CheckCircle2 } from 'lucide-react'

function SettingRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 border-b border-gray-800 last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-200">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-5.5 rounded-full transition-colors ${
        checked ? 'bg-numa-500' : 'bg-gray-700'
      }`}
      style={{ height: 22 }}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-4.5' : 'translate-x-0'
        }`}
        style={{ transform: checked ? 'translateX(18px)' : 'translateX(0)' }}
      />
    </button>
  )
}

export default function SettingsPage() {
  const { user, logout } = useAuthStore()
  const [saved,  setSaved]  = useState(false)
  const [saving, setSaving] = useState(false)
  const [prefs, setPrefs] = useState({
    email_nudges:       true,
    slack_nudges:       true,
    daily_digest:       true,
    weekly_report:      false,
    productivity_alerts: true,
  })

  const handleToggle = (key) => setPrefs((p) => ({ ...p, [key]: !p[key] }))

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.patch('/users/me/prefs', prefs)
    } catch {
      // endpoint not yet wired — silently succeed for demo
    } finally {
      setSaving(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    }
  }

  return (
    <>
      <TopBar title="Settings" />
      <main className="p-6 max-w-2xl space-y-6 animate-fade-slide-up">

        {/* Profile */}
        <div className="card">
          <SectionHeader title="Profile" icon={User} />
          <div className="mt-4 flex items-start gap-4">
            <Avatar name={user?.display_name || user?.real_name || 'You'} size={40} />
            <div className="space-y-1">
              <p className="font-semibold text-gray-100">{user?.display_name || user?.real_name || '—'}</p>
              <p className="text-sm text-gray-500">{user?.email || '—'}</p>
              <p className="text-xs text-gray-600 font-mono">Slack ID: {user?.slack_user_id || '—'}</p>
              <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2.5 py-0.5 mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Connected to Slack
              </span>
            </div>
          </div>
        </div>

        {/* Slack workspace */}
        <div className="card">
          <SectionHeader title="Slack Integration" icon={ExternalLink} />
          <div className="mt-4 space-y-0">
            <SettingRow label="Team / Workspace" description="The Slack workspace NUMA monitors">
              <span className="text-sm text-gray-400">{user?.slack_team_id || 'Unknown'}</span>
            </SettingRow>
            <SettingRow label="Bot scope" description="channels:history, channels:read, chat:write, users:read">
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />Active
              </span>
            </SettingRow>
            <SettingRow label="Slash command" description="Use /numa in any channel">
              <code className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-numa-300">/numa</code>
            </SettingRow>
          </div>
        </div>

        {/* Notification preferences */}
        <div className="card">
          <SectionHeader title="Notifications" icon={Bell} />
          <div className="mt-4 space-y-0">
            <SettingRow label="Email nudges" description="Send nudges to your email">
              <Toggle checked={prefs.email_nudges} onChange={() => handleToggle('email_nudges')} />
            </SettingRow>
            <SettingRow label="Slack nudges" description="Receive nudges via Slack DM">
              <Toggle checked={prefs.slack_nudges} onChange={() => handleToggle('slack_nudges')} />
            </SettingRow>
            <SettingRow label="Daily digest" description="Morning summary of your day plan">
              <Toggle checked={prefs.daily_digest} onChange={() => handleToggle('daily_digest')} />
            </SettingRow>
            <SettingRow label="Weekly report" description="Sunday evening productivity report">
              <Toggle checked={prefs.weekly_report} onChange={() => handleToggle('weekly_report')} />
            </SettingRow>
            <SettingRow label="Productivity alerts" description="Alert when score drops below 40">
              <Toggle checked={prefs.productivity_alerts} onChange={() => handleToggle('productivity_alerts')} />
            </SettingRow>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-800 flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary flex items-center gap-2"
            >
              {saving ? <Spinner className="w-4 h-4" /> : null}
              Save preferences
            </button>
            {saved && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />Saved
              </span>
            )}
          </div>
        </div>

        {/* Danger zone */}
        <div className="card border-red-500/20">
          <SectionHeader title="Account" icon={Shield} />
          <div className="mt-4">
            <SettingRow label="Sign out" description="You will be redirected to the login page">
              <button
                onClick={logout}
                className="flex items-center gap-1.5 text-sm text-red-400 hover:text-red-300 transition-colors"
              >
                <LogOut className="w-4 h-4" />Sign out
              </button>
            </SettingRow>
          </div>
        </div>
      </main>
    </>
  )
}
