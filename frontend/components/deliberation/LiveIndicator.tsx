'use client';

import { cn } from '@/lib/utils';

interface LiveIndicatorProps {
  isLive: boolean;
  className?: string;
}

export function LiveIndicator({ isLive, className }: LiveIndicatorProps) {
  if (!isLive) {
    return null;
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
      </span>
      <span className="text-sm font-medium text-red-600">Live</span>
    </div>
  );
}
