'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SourceList } from './SourceList';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import type { BriefingBookResponse } from '@/lib/types';
import { BookOpen, Calendar } from 'lucide-react';

interface BriefingViewerProps {
  briefing: BriefingBookResponse | null;
  isLoading?: boolean;
}

export function BriefingViewer({ briefing, isLoading }: BriefingViewerProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium">No Briefing Available</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Generate a briefing book to provide background research for the deliberation.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Briefing Book
          </h2>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Generated {formatDateTime(briefing.generated_at)}</span>
          </div>
        </div>

        <Card>
          <CardContent className="pt-6">
            <ScrollArea className="h-[600px] pr-4">
              <div className="prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {briefing.content_markdown}
                </ReactMarkdown>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        {briefing.sections && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Quick Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {briefing.sections.overview && (
                <div>
                  <h4 className="text-sm font-medium mb-1">Overview</h4>
                  <p className="text-sm text-muted-foreground">
                    {briefing.sections.overview}
                  </p>
                </div>
              )}

              {briefing.sections.key_facts && briefing.sections.key_facts.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1">Key Facts</h4>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    {briefing.sections.key_facts.map((fact, i) => (
                      <li key={i}>{fact}</li>
                    ))}
                  </ul>
                </div>
              )}

              {briefing.sections.arguments_for && briefing.sections.arguments_for.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1 text-green-600">Arguments For</h4>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    {briefing.sections.arguments_for.map((arg, i) => (
                      <li key={i}>{arg}</li>
                    ))}
                  </ul>
                </div>
              )}

              {briefing.sections.arguments_against && briefing.sections.arguments_against.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1 text-red-600">Arguments Against</h4>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    {briefing.sections.arguments_against.map((arg, i) => (
                      <li key={i}>{arg}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <SourceList sources={briefing.sources} />
      </div>
    </div>
  );
}
