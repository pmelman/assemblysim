'use client';

import { cn } from '@/lib/utils';
import type { VoteValue } from '@/lib/types';
import { ThumbsUp, ThumbsDown, Minus } from 'lucide-react';

interface VoteIndicatorProps {
  vote: VoteValue | null;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

const voteConfig = {
  support: {
    icon: ThumbsUp,
    label: 'Support',
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    iconClass: 'text-green-600',
  },
  oppose: {
    icon: ThumbsDown,
    label: 'Oppose',
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    iconClass: 'text-red-600',
  },
  abstain: {
    icon: Minus,
    label: 'Abstain',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    iconClass: 'text-gray-500',
  },
};

const sizeClasses = {
  sm: {
    container: 'px-2 py-0.5 text-xs',
    icon: 'h-3 w-3',
  },
  md: {
    container: 'px-2.5 py-1 text-sm',
    icon: 'h-4 w-4',
  },
};

export function VoteIndicator({ vote, size = 'md', showLabel = true, className }: VoteIndicatorProps) {
  if (!vote) {
    return null;
  }

  const config = voteConfig[vote];
  const sizes = sizeClasses[size];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full',
        config.bgClass,
        config.textClass,
        sizes.container,
        className
      )}
    >
      <Icon className={cn(sizes.icon, config.iconClass)} />
      {showLabel && <span className="font-medium">{config.label}</span>}
    </div>
  );
}
