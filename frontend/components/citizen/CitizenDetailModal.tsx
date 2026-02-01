'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CitizenAvatar } from './CitizenAvatar';
import { VoteIndicator } from './VoteIndicator';
import { Skeleton } from '@/components/ui/skeleton';
import { getCitizen } from '@/lib/api';
import type { CitizenResponse, CitizenDetailResponse } from '@/lib/types';

interface CitizenDetailModalProps {
  citizen: CitizenResponse | null;
  assemblyId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CitizenDetailModal({
  citizen,
  assemblyId,
  open,
  onOpenChange,
}: CitizenDetailModalProps) {
  const [detail, setDetail] = useState<CitizenDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (citizen && open) {
      setIsLoading(true);
      getCitizen(assemblyId, citizen.id)
        .then(setDetail)
        .catch(console.error)
        .finally(() => setIsLoading(false));
    } else {
      setDetail(null);
    }
  }, [citizen, assemblyId, open]);

  if (!citizen) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <CitizenAvatar name={citizen.name} size="lg" />
            <div>
              <DialogTitle className="text-xl">{citizen.name}</DialogTitle>
              <DialogDescription>Citizen #{citizen.id}</DialogDescription>
            </div>
            {citizen.final_vote && (
              <div className="ml-auto">
                <VoteIndicator vote={citizen.final_vote} />
              </div>
            )}
          </div>
        </DialogHeader>

        <Tabs defaultValue="profile" className="mt-4">
          <TabsList>
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="persona">Persona</TabsTrigger>
            {detail?.gss_data && <TabsTrigger value="gss">GSS Data</TabsTrigger>}
          </TabsList>

          <ScrollArea className="h-[400px] mt-4">
            <TabsContent value="profile" className="space-y-4 m-0">
              {citizen.background_summary && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Background</h4>
                  <p className="text-sm text-muted-foreground">
                    {citizen.background_summary}
                  </p>
                </div>
              )}

              {citizen.key_values && citizen.key_values.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Key Values</h4>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                    {citizen.key_values.map((value, i) => (
                      <li key={i}>{value}</li>
                    ))}
                  </ul>
                </div>
              )}

              {citizen.demographic_tags && citizen.demographic_tags.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Demographics</h4>
                  <div className="flex flex-wrap gap-1">
                    {citizen.demographic_tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {citizen.vote_reasoning && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Vote Reasoning</h4>
                  <p className="text-sm text-muted-foreground">
                    {citizen.vote_reasoning}
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="persona" className="m-0">
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : detail?.system_prompt ? (
                <div className="prose-sm">
                  <h4 className="text-sm font-medium mb-2">System Prompt</h4>
                  <pre className="whitespace-pre-wrap text-xs bg-muted p-3 rounded-md overflow-x-auto">
                    {detail.system_prompt}
                  </pre>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Persona details not available
                </p>
              )}
            </TabsContent>

            {detail?.gss_data && (
              <TabsContent value="gss" className="m-0">
                <div>
                  <h4 className="text-sm font-medium mb-2">GSS Survey Data</h4>
                  <div className="bg-muted p-3 rounded-md">
                    <dl className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(detail.gss_data).map(([key, value]) => (
                        <div key={key}>
                          <dt className="font-medium text-muted-foreground">{key}</dt>
                          <dd>{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </div>
              </TabsContent>
            )}
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
