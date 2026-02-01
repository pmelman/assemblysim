'use client';

import { Card, CardContent } from '@/components/ui/card';
import { CitizenAvatar } from './CitizenAvatar';
import { VoteIndicator } from './VoteIndicator';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { CitizenResponse } from '@/lib/types';

interface CitizenCardProps {
  citizen: CitizenResponse;
  onClick?: () => void;
  selected?: boolean;
  compact?: boolean;
}

export function CitizenCard({ citizen, onClick, selected, compact }: CitizenCardProps) {
  return (
    <Card
      className={cn(
        'transition-all',
        onClick && 'cursor-pointer hover:shadow-md',
        selected && 'ring-2 ring-primary',
        compact && 'shadow-none border-0 bg-transparent'
      )}
      onClick={onClick}
    >
      <CardContent className={cn('flex items-start gap-3', compact ? 'p-2' : 'p-4')}>
        <CitizenAvatar name={citizen.name} size={compact ? 'sm' : 'md'} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className={cn('font-medium truncate', compact && 'text-sm')}>
              {citizen.name}
            </h4>
            {citizen.final_vote && (
              <VoteIndicator vote={citizen.final_vote} size="sm" showLabel={!compact} />
            )}
          </div>

          {!compact && citizen.background_summary && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {citizen.background_summary}
            </p>
          )}

          {!compact && citizen.demographic_tags && citizen.demographic_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {citizen.demographic_tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {citizen.demographic_tags.length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{citizen.demographic_tags.length - 3}
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
