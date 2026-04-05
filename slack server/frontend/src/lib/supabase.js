/**
 * Supabase client — uses the ANON key (safe for frontend).
 * Used exclusively for Realtime subscriptions.
 * All data mutations go through the FastAPI backend.
 */
import { createClient } from '@supabase/supabase-js'

const supabaseUrl  = import.meta.env.VITE_SUPABASE_URL
const supabaseAnon = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnon) {
  console.warn('[NUMA] Missing Supabase env vars. Realtime will not work.')
}

export const supabase = createClient(supabaseUrl, supabaseAnon, {
  realtime: { params: { eventsPerSecond: 10 } },
})
