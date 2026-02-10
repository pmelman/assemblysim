'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { SourceList } from './SourceList';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import { deleteBriefing } from '@/lib/api';
import type { BriefingBookResponse } from '@/lib/types';
import { BookOpen, Calendar, Trash2, Loader2 } from 'lucide-react';

interface BriefingViewerProps {
  briefing: BriefingBookResponse | null;
  isLoading?: boolean;
  onDelete?: () => void;
}

export function BriefingViewer({ briefing, isLoading, onDelete }: BriefingViewerProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!briefing || !confirm('Are you sure you want to delete this briefing?')) {
      return;
    }
    setIsDeleting(true);
    setError(null);
    try {
      await deleteBriefing(briefing.assembly_id);
      onDelete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete briefing');
    } finally {
      setIsDeleting(false);
    }
  };
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
        {error && (
          <div className="p-2 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
            {error}
          </div>
        )}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Briefing Book
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Generated {formatDateTime(briefing.generated_at)}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </Button>
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
              {Object.entries(briefing.sections).map(([key, value]) => {
                if (value == null) return null;
                const heading = key.replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

                // String values
                if (typeof value === 'string') {
                  return (
                    <div key={key}>
                      <h4 className="text-sm font-medium mb-1">{heading}</h4>
                      <p className="text-sm text-muted-foreground line-clamp-4">
                        {value}
                      </p>
                    </div>
                  );
                }

                // Array of strings
                if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
                  return (
                    <div key={key}>
                      <h4 className="text-sm font-medium mb-1">{heading}</h4>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                        {(value as string[]).slice(0, 5).map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                        {value.length > 5 && (
                          <li className="text-xs italic">...and {value.length - 5} more</li>
                        )}
                      </ul>
                    </div>
                  );
                }

                // Array of objects - show a count
                if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
                  return (
                    <div key={key}>
                      <h4 className="text-sm font-medium mb-1">{heading}</h4>
                      <p className="text-sm text-muted-foreground">
                        {value.length} item{value.length !== 1 ? 's' : ''} &mdash; see full briefing
                      </p>
                    </div>
                  );
                }

                // Object (dict) - show keys
                if (typeof value === 'object' && !Array.isArray(value)) {
                  const entries = Object.entries(value as Record<string, unknown>);
                  return (
                    <div key={key}>
                      <h4 className="text-sm font-medium mb-1">{heading}</h4>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                        {entries.slice(0, 5).map(([k, v]) => (
                          <li key={k}>
                            <span className="font-medium">{k.replace(/_/g, ' ')}:</span>{' '}
                            {typeof v === 'string' ? (v as string).slice(0, 80) + ((v as string).length > 80 ? '...' : '') : String(v).slice(0, 80)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                }

                return null;
              })}
            </CardContent>
          </Card>
        )}

        <SourceList sources={briefing.sources} />
      </div>
    </div>
  );
}
