'use client';

import { cn } from '@/lib/utils';

interface RoundDividerProps {
  round: number;
  phase?: string;
  className?: string;
}

export function RoundDivider({ round, phase, className }: RoundDividerProps) {
  const label = phase === 'voting'
    ? 'Voting Phase'
    : phase === 'introduction'
    ? 'Introduction'
    : `Round ${round}`;

  return (
    <div className={cn('relative py-4', className)}>
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-muted" />
      </div>
      <div className="relative flex justify-center">
        <span className="px-3 bg-background text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </span>
      </div>
    </div>
  );
}
