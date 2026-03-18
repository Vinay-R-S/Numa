import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version',
};

// Mock AI responses — will be replaced with real AI agent
function getMockAgentResponse(query: string): string {
  const lower = query.toLowerCase();
  if (lower.includes("schedule") || lower.includes("meeting")) {
    return "Your event has been scheduled for tomorrow at 4pm.";
  }
  if (lower.includes("cancel")) {
    return "Event cancelled successfully. Your calendar has been updated.";
  }
  if (lower.includes("remind")) {
    return "Reminder set. I'll notify you 15 minutes before.";
  }
  if (lower.includes("summarize") || lower.includes("summary")) {
    return "Here's your day summary: You have 5 events today, starting with Team Standup at 9am and ending with AI Strategy Call at 4:30pm.";
  }
  return `Understood — "${query}". I've processed your request. Check your calendar for updates.`;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { query } = await req.json();

    if (!query || typeof query !== "string") {
      return new Response(JSON.stringify({ error: "Missing 'query' field" }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // TODO: Replace with real AI agent logic
    const response = getMockAgentResponse(query);

    return new Response(JSON.stringify({ response, refreshCalendar: query.toLowerCase().includes("schedule") || query.toLowerCase().includes("cancel") }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
