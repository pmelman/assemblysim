'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { VoteChart } from './VoteChart';
import { RecommendationCard } from './RecommendationCard';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import type { ReportResponse } from '@/lib/types';
import { FileText, Calendar, Tag, Users } from 'lucide-react';

interface ReportViewerProps {
  report: ReportResponse | null;
  isLoading?: boolean;
}

export function ReportViewer({ report, isLoading }: ReportViewerProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium">No Report Available</h3>
        <p className="text-sm text-muted-foreground mt-1">
          The report will be generated after the deliberation and voting phases are complete.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Final Report
        </h2>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          <span>Generated {formatDateTime(report.generated_at)}</span>
        </div>
      </div>

      {/* Vote Results */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Vote Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          <VoteChart voteTally={report.vote_tally} />
        </CardContent>
      </Card>

      {/* Executive Summary */}
      {report.executive_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {report.executive_summary}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Themes */}
      {report.key_themes && report.key_themes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Tag className="h-5 w-5" />
              Key Themes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {report.key_themes.map((theme, index) => (
                <Badge key={index} variant="secondary" className="text-sm">
                  {theme}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Recommendations</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {report.recommendations.map((rec, index) => (
              <RecommendationCard key={index} recommendation={rec} index={index} />
            ))}
          </div>
        </div>
      )}

      {/* Minority Report */}
      {report.minority_report && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Minority Report</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[200px]">
              <div className="prose-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {report.minority_report}
                </ReactMarkdown>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
