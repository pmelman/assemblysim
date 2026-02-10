'use client';

import { cn } from '@/lib/utils';

interface RoundDividerProps {
  round: number;
  phase?: string;
  theme?: string;
  className?: string;
}

export function RoundDivider({ round, phase, theme, className }: RoundDividerProps) {
  let label: string;

  if (phase === 'voting') {
    label = 'Voting Phase';
  } else if (phase === 'introduction' || phase === 'opening') {
    label = 'Introduction';
  } else if (phase === 'plenary') {
    label = 'Plenary Synthesis';
  } else if (phase === 'research') {
    label = `Follow-Up Research`;
  } else if (theme) {
    label = `Round ${round}: ${theme}`;
  } else {
    label = `Round ${round}`;
  }

  const isResearch = phase === 'research';

  return (
    <div className={cn('relative py-4', className)}>
      <div className="absolute inset-0 flex items-center">
        <div className={cn(
          'w-full border-t',
          isResearch ? 'border-blue-300' : 'border-muted'
        )} />
      </div>
      <div className="relative flex justify-center">
        <span className={cn(
          'px-3 bg-background text-xs font-medium uppercase tracking-wide',
          isResearch ? 'text-blue-600' : 'text-muted-foreground'
        )}>
          {label}
        </span>
      </div>
    </div>
  );
}
