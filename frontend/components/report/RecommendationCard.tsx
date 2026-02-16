'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Recommendation } from '@/lib/types';
import { CheckCircle, XCircle } from 'lucide-react';

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
  passed?: boolean;
  avgScore?: number;
}

export function RecommendationCard({ recommendation, index, passed, avgScore }: RecommendationCardProps) {
  const hasPassed = passed ?? true;
  const score = avgScore ?? recommendation.avg_score;

  return (
    <Card className={hasPassed ? '' : 'opacity-70'}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="flex items-center justify-center h-6 w-6 rounded-full bg-muted text-sm font-medium">
              {index + 1}
            </span>
            {recommendation.title}
          </CardTitle>
          <div className="flex flex-col items-end gap-1 flex-shrink-0">
            {score != null && (
              <Badge variant="outline" className="font-mono text-xs">
                {score.toFixed(1)} / 5
              </Badge>
            )}
            <Badge
              variant={hasPassed ? 'green' : 'red'}
              className="gap-1"
            >
              {hasPassed ? (
                <>
                  <CheckCircle className="h-3 w-3" />
                  Passed
                </>
              ) : (
                <>
                  <XCircle className="h-3 w-3" />
                  Did Not Pass
                </>
              )}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{recommendation.description}</p>
      </CardContent>
    </Card>
  );
}
