'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Recommendation } from '@/lib/types';
import { CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
}

const supportLevelConfig = {
  strong: {
    icon: CheckCircle,
    variant: 'green' as const,
    label: 'Strong Support',
  },
  moderate: {
    icon: AlertCircle,
    variant: 'yellow' as const,
    label: 'Moderate Support',
  },
  weak: {
    icon: HelpCircle,
    variant: 'gray' as const,
    label: 'Weak Support',
  },
};

export function RecommendationCard({ recommendation, index }: RecommendationCardProps) {
  const config = supportLevelConfig[recommendation.support_level];
  const Icon = config.icon;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="flex items-center justify-center h-6 w-6 rounded-full bg-muted text-sm font-medium">
              {index + 1}
            </span>
            {recommendation.title}
          </CardTitle>
          <Badge variant={config.variant} className="gap-1 flex-shrink-0">
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{recommendation.description}</p>
      </CardContent>
    </Card>
  );
}
