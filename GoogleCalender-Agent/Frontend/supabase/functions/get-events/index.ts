import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version',
};

// Mock events — will be replaced with Google Calendar integration
const today = new Date();
const yyyy = today.getFullYear();
const mm = today.getMonth();
const dd = today.getDate();

const mockEvents = [
  { id: "1", title: "Team Standup", date: new Date(yyyy, mm, dd).toISOString(), startTime: "09:00", endTime: "09:30", description: "Daily sync with engineering team", color: "primary" },
  { id: "2", title: "Product Review", date: new Date(yyyy, mm, dd).toISOString(), startTime: "11:00", endTime: "12:00", description: "Review Q1 product roadmap and priorities", color: "secondary" },
  { id: "3", title: "Lunch with Investor", date: new Date(yyyy, mm, dd).toISOString(), startTime: "12:30", endTime: "13:30", description: "Discuss Series B funding at The Capital Grille", color: "primary" },
  { id: "4", title: "Design Sprint", date: new Date(yyyy, mm, dd).toISOString(), startTime: "14:00", endTime: "16:00", description: "Workshop on new dashboard components", color: "secondary" },
  { id: "5", title: "AI Strategy Call", date: new Date(yyyy, mm, dd).toISOString(), startTime: "16:30", endTime: "17:00", description: "Align on AI feature rollout timeline", color: "primary" },
  { id: "6", title: "Marketing Sync", date: new Date(yyyy, mm, dd + 1).toISOString(), startTime: "10:00", endTime: "10:45", description: "Campaign performance review", color: "secondary" },
  { id: "7", title: "Board Prep", date: new Date(yyyy, mm, dd + 2).toISOString(), startTime: "09:00", endTime: "11:00", description: "Prepare board deck and financials", color: "primary" },
];

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // TODO: Replace with Google Calendar API fetch
    return new Response(JSON.stringify({ events: mockEvents }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
