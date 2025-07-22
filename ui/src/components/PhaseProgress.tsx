import { cn } from '../utils';

type Phase =
  | 'initialization'
  | 'downloading'
  | 'transcription'
  | 'embedding'
  | 'storing'
  | 'completed';

interface PhaseProgressProps {
  phases: Array<{
    phase: Phase;
    is_current_phase: boolean;
    percentage: number;
  }>;
  isCompact?: boolean;
  className?: string;
}

const phaseLabels: Record<Phase, string> = {
  initialization: 'Initializing',
  downloading: 'Downloading',
  transcription: 'Transcribing',
  embedding: 'Embedding',
  storing: 'Storing',
  completed: 'Completed',
};

const phaseIcons: Record<Phase, string> = {
  initialization: '⚡',
  downloading: '↓',
  transcription: '🎙',
  embedding: '🧠',
  storing: '💾',
  completed: '✓',
};

export function PhaseProgress({ phases, isCompact = false, className }: PhaseProgressProps) {
  const currentPhase = phases.find((p) => p.is_current_phase);

  if (isCompact && currentPhase) {
    // Compact view: single progress bar with current phase label
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className="flex-1 relative">
          <div className="h-1.5 bg-background-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${currentPhase.percentage}%` }}
            />
          </div>
        </div>
        <span className="text-xs text-foreground-secondary min-w-[80px] text-right">
          {phaseLabels[currentPhase.phase]}
        </span>
      </div>
    );
  }

  // Full view: all phases with individual progress
  return (
    <div className={cn('space-y-3', className)}>
      {phases.map((phase) => {
        const isActive = phase.is_current_phase;
        const isCompleted = phase.percentage === 100;

        return (
          <div
            key={phase.phase}
            className={cn('relative transition-all duration-200', isActive && 'scale-[1.02]')}
          >
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs transition-all',
                  isActive && 'bg-primary text-primary-foreground shadow-glow-primary',
                  !isActive && isCompleted && 'bg-accent-success/20 text-accent-success',
                  !isActive && !isCompleted && 'bg-background-elevated text-foreground-tertiary'
                )}
              >
                {phaseIcons[phase.phase]}
              </div>

              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={cn(
                      'text-sm font-medium transition-colors',
                      isActive && 'text-foreground',
                      !isActive && isCompleted && 'text-foreground-secondary',
                      !isActive && !isCompleted && 'text-foreground-tertiary'
                    )}
                  >
                    {phaseLabels[phase.phase]}
                  </span>
                  <span
                    className={cn(
                      'text-xs transition-colors',
                      isActive && 'text-foreground-secondary',
                      !isActive && 'text-foreground-tertiary'
                    )}
                  >
                    {phase.percentage}%
                  </span>
                </div>

                <div className="h-1.5 bg-background-elevated rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all duration-300 ease-out',
                      isActive && 'bg-primary shadow-glow-primary',
                      !isActive && isCompleted && 'bg-accent-success',
                      !isActive && !isCompleted && 'bg-foreground/10'
                    )}
                    style={{ width: `${phase.percentage}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
