'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AssemblyHeader } from '@/components/assembly/AssemblyHeader';
import { AssemblyActions } from '@/components/assembly/AssemblyActions';
import { CitizenGrid } from '@/components/citizen/CitizenGrid';
import { MessageThread } from '@/components/deliberation/MessageThread';
import { GroupSelector } from '@/components/deliberation/GroupSelector';
import { BriefingViewer } from '@/components/briefing/BriefingViewer';
import { ReportViewer } from '@/components/report/ReportViewer';
import { useAssembly } from '@/hooks/useAssembly';
import { useMessages } from '@/hooks/useMessages';
import { Users, MessageSquare, BookOpen, FileText } from 'lucide-react';

export default function AssemblyDetailPage() {
  const params = useParams();
  const assemblyId = params.id ? parseInt(params.id as string, 10) : null;

  const { assembly, isLoading, error, mutate } = useAssembly(assemblyId);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);

  const {
    messages,
    isLoading: messagesLoading,
    isLive,
  } = useMessages(assemblyId, {
    groupId: selectedGroupId ?? undefined,
    assemblyStatus: assembly?.status,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-12 w-48" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !assembly) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <h2 className="text-xl font-semibold text-red-600">
          {error ? 'Error Loading Assembly' : 'Assembly Not Found'}
        </h2>
        <p className="text-muted-foreground mt-1">
          {error?.message || 'The requested assembly could not be found.'}
        </p>
        <a href="/" className="mt-4 text-primary hover:underline">
          Return to Dashboard
        </a>
      </div>
    );
  }

  // Determine default tab based on status
  const getDefaultTab = () => {
    if (['deliberating', 'voting', 'completed'].includes(assembly.status)) {
      return 'deliberation';
    }
    if (assembly.status === 'completed' && assembly.report) {
      return 'report';
    }
    return 'citizens';
  };

  return (
    <div className="space-y-6">
      <AssemblyHeader assembly={assembly} />

      <AssemblyActions
        assemblyId={assembly.id}
        status={assembly.status}
        onActionComplete={mutate}
      />

      <Tabs defaultValue={getDefaultTab()} className="space-y-4">
        <TabsList>
          <TabsTrigger value="citizens" className="gap-2">
            <Users className="h-4 w-4" />
            Citizens ({assembly.citizens.length})
          </TabsTrigger>
          <TabsTrigger value="deliberation" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Deliberation
            {isLive && (
              <span className="ml-1 h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            )}
          </TabsTrigger>
          <TabsTrigger value="briefing" className="gap-2">
            <BookOpen className="h-4 w-4" />
            Briefing
          </TabsTrigger>
          <TabsTrigger value="report" className="gap-2">
            <FileText className="h-4 w-4" />
            Report
          </TabsTrigger>
        </TabsList>

        <TabsContent value="citizens">
          {assembly.citizens.length === 0 ? (
            <Card className="p-8 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">Citizens Not Yet Generated</h3>
              <p className="text-muted-foreground mt-1">
                {assembly.status === 'generating_citizens'
                  ? 'Citizens are currently being generated from GSS data...'
                  : 'Citizens will be generated when the assembly starts.'}
              </p>
            </Card>
          ) : (
            <CitizenGrid
              citizens={assembly.citizens}
              groups={assembly.groups}
              assemblyId={assembly.id}
            />
          )}
        </TabsContent>

        <TabsContent value="deliberation">
          <Card className="p-4">
            {assembly.groups.length > 1 && (
              <GroupSelector
                groups={assembly.groups}
                selectedGroupId={selectedGroupId}
                onSelectGroup={setSelectedGroupId}
                className="mb-4"
              />
            )}
            <MessageThread
              messages={messages}
              isLoading={messagesLoading}
              isLive={isLive}
              groupId={selectedGroupId}
            />
          </Card>
        </TabsContent>

        <TabsContent value="briefing">
          <BriefingViewer briefing={assembly.briefing_book} />
        </TabsContent>

        <TabsContent value="report">
          <ReportViewer report={assembly.report} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
