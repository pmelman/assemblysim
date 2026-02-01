'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { BriefingSource } from '@/lib/types';
import { ExternalLink, FileText } from 'lucide-react';

interface SourceListProps {
  sources: BriefingSource[] | null;
}

export function SourceList({ sources }: SourceListProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Sources
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {sources.map((source, index) => (
            <li key={index} className="border-b last:border-0 pb-3 last:pb-0">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group"
              >
                <div className="flex items-start gap-2">
                  <ExternalLink className="h-4 w-4 mt-0.5 text-muted-foreground group-hover:text-primary flex-shrink-0" />
                  <div>
                    <h4 className="text-sm font-medium group-hover:text-primary group-hover:underline">
                      {source.title}
                    </h4>
                    {source.snippet && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {source.snippet}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1 truncate">
                      {source.url}
                    </p>
                  </div>
                </div>
              </a>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
