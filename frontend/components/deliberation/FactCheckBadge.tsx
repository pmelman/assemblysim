'use client';

import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { FactCheckStatus } from '@/lib/types';
import { CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';

interface FactCheckBadgeProps {
  status: FactCheckStatus | null;
}

const statusConfig = {
  verified: {
    icon: CheckCircle,
    label: 'Verified',
    variant: 'green' as const,
    description: 'This claim has been fact-checked and verified',
  },
  disputed: {
    icon: AlertCircle,
    label: 'Disputed',
    variant: 'red' as const,
    description: 'This claim has been disputed or found to be inaccurate',
  },
  unchecked: {
    icon: HelpCircle,
    label: 'Unchecked',
    variant: 'gray' as const,
    description: 'This claim has not been fact-checked',
  },
};

export function FactCheckBadge({ status }: FactCheckBadgeProps) {
  // Placeholder for Phase 3 - only render when fact-checking is enabled
  if (!status) {
    return null;
  }

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant={config.variant} className="gap-1 cursor-help">
            <Icon className="h-3 w-3" />
            <span>{config.label}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
