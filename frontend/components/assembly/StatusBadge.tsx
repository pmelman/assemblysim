'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { AssemblyStatus } from '@/lib/types';
import { STATUS_CONFIG } from '@/lib/types';

interface StatusBadgeProps {
  status: AssemblyStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <Badge
      variant={config.color as 'gray' | 'yellow' | 'blue' | 'green' | 'purple' | 'red'}
      className={cn(
        config.pulse && 'animate-pulse',
        className
      )}
    >
      {config.label}
    </Badge>
  );
}
