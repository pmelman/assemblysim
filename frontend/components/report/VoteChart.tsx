'use client';

import { cn, calculateVotePercentages } from '@/lib/utils';
import type { VoteTally } from '@/lib/types';

interface VoteChartProps {
  voteTally: VoteTally | null;
  className?: string;
}

export function VoteChart({ voteTally, className }: VoteChartProps) {
  if (!voteTally || voteTally.total === 0) {
    return (
      <div className={cn('text-center py-8 text-muted-foreground', className)}>
        <p>No votes recorded</p>
      </div>
    );
  }

  const percentages = calculateVotePercentages(voteTally);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Horizontal bar chart */}
      <div className="h-8 w-full flex rounded-full overflow-hidden">
        {percentages.support > 0 && (
          <div
            className="bg-green-500 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${percentages.support}%` }}
          >
            {percentages.support > 10 && `${percentages.support}%`}
          </div>
        )}
        {percentages.oppose > 0 && (
          <div
            className="bg-red-500 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${percentages.oppose}%` }}
          >
            {percentages.oppose > 10 && `${percentages.oppose}%`}
          </div>
        )}
        {percentages.abstain > 0 && (
          <div
            className="bg-gray-400 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${percentages.abstain}%` }}
          >
            {percentages.abstain > 10 && `${percentages.abstain}%`}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-green-500" />
          <span>Support: {voteTally.support} ({percentages.support}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-red-500" />
          <span>Oppose: {voteTally.oppose} ({percentages.oppose}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-gray-400" />
          <span>Abstain: {voteTally.abstain} ({percentages.abstain}%)</span>
        </div>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Total votes: {voteTally.total}
      </p>
    </div>
  );
}
