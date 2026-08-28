"use client"

import {
  EntryScreen,
  GuidedSession,
  MeditationSession,
  MentalPeacePageHeader,
  MoodSelector,
  PreparingSession,
  SESSION_STAGES,
  SessionDashboard,
  useMentalPeaceSession,
} from "@/features/mental-peace"

export default function MentalPeacePage() {
  const {
    stage,
    selectedMood,
    begin,
    selectMood,
    startGuidedSession,
    finishPreparing,
    endGuidedSession,
    goBack,
  } = useMentalPeaceSession()

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-hidden bg-background px-4 py-4 text-foreground sm:px-6 sm:py-6">
      {stage !== SESSION_STAGES.GUIDED_SESSION && (
        <MentalPeacePageHeader showBack={stage !== SESSION_STAGES.ENTRY} onBack={goBack} />
      )}

      <div className="min-h-0 flex-1">
        {stage === SESSION_STAGES.ENTRY && <EntryScreen onBegin={begin} />}

        {stage === SESSION_STAGES.MOOD_SELECT && <MoodSelector onSelect={selectMood} />}

        {stage === SESSION_STAGES.PREPARING && selectedMood && (
          <PreparingSession mood={selectedMood} onComplete={finishPreparing} />
        )}

        {stage === SESSION_STAGES.DASHBOARD && selectedMood && (
          <SessionDashboard mood={selectedMood} onBeginSession={startGuidedSession} />
        )}

        {stage === SESSION_STAGES.GUIDED_SESSION && selectedMood && (
          <div className="fixed inset-0 z-50">
            <GuidedSession mood={selectedMood} onEnd={endGuidedSession} />
          </div>
        )}

        {stage === SESSION_STAGES.MEDITATION && <MeditationSession />}
      </div>
    </div>
  )
}
