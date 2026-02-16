'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { RecommendationCard } from './RecommendationCard';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import type { ReportResponse } from '@/lib/types';
import { FileText, Calendar } from 'lucide-react';

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

  // Build a combined list of all proposals with scores for display
  const allProposals = report.proposal_scores || [];

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

      {/* Key Themes (as a subsection within a card) */}
      {report.key_themes && report.key_themes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Key Themes</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              {report.key_themes.map((theme, index) => (
                <li key={index}>{theme}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Proposal Scores — all proposals, passed and failed */}
      {allProposals.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Proposals &amp; Scores</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {allProposals.map((proposal, index) => (
              <RecommendationCard
                key={index}
                recommendation={{
                  title: proposal.title,
                  description: proposal.description,
                  avg_score: proposal.avg_score,
                  support_level: proposal.passed
                    ? (proposal.avg_score >= 4.0 ? 'strong' : 'moderate')
                    : 'weak',
                }}
                index={index}
                passed={proposal.passed}
                avgScore={proposal.avg_score}
              />
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
