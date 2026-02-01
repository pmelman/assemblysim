'use client';

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import type { Citation } from '@/lib/types';
import { Quote, ExternalLink } from 'lucide-react';

interface CitationPopoverProps {
  citations: Citation[] | null;
}

export function CitationPopover({ citations }: CitationPopoverProps) {
  // Placeholder for Phase 3 - only render when citations exist
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs gap-1">
          <Quote className="h-3 w-3" />
          <span>{citations.length} {citations.length === 1 ? 'citation' : 'citations'}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          <h4 className="font-medium text-sm">Citations</h4>
          <ul className="space-y-2">
            {citations.map((citation, index) => (
              <li key={index} className="text-sm">
                <p className="text-muted-foreground italic">&ldquo;{citation.text}&rdquo;</p>
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-xs text-muted-foreground">{citation.source}</span>
                  {citation.url && (
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </PopoverContent>
    </Popover>
  );
}
