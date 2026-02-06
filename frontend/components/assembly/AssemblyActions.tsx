'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { generateCitizens, generateBriefing, startDeliberation, deleteAssembly } from '@/lib/api';
import type { AssemblyStatus } from '@/lib/types';
import { isActiveStatus } from '@/lib/utils';
import { Play, BookOpen, Trash2, Loader2, Users } from 'lucide-react';

interface AssemblyActionsProps {
  assemblyId: number;
  status: AssemblyStatus;
  hasCitizens: boolean;
  hasBriefing: boolean;
  onActionComplete?: () => void;
}

export function AssemblyActions({ assemblyId, status, hasCitizens, hasBriefing, onActionComplete }: AssemblyActionsProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Determine valid actions based on status AND actual data
  const isProcessing = isActiveStatus(status);
  const canGenerateCitizens = !hasCitizens && !isProcessing;
  const canGenerateBriefing = !isProcessing || status === 'generating_citizens';
  const canStartDeliberation = hasCitizens && !isProcessing && status !== 'completed';
  const canDelete = !isProcessing;

  const handleGenerateCitizens = async () => {
    setIsLoading('citizens');
    setError(null);
    try {
      await generateCitizens(assemblyId);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate citizens');
    } finally {
      setIsLoading(null);
    }
  };

  const handleGenerateBriefing = async () => {
    setIsLoading('briefing');
    setError(null);
    try {
      await generateBriefing(assemblyId, { depth: 'standard' });
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate briefing');
    } finally {
      setIsLoading(null);
    }
  };

  const handleStartDeliberation = async () => {
    setIsLoading('deliberation');
    setError(null);
    try {
      await startDeliberation(assemblyId);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start deliberation');
    } finally {
      setIsLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this assembly? This action cannot be undone.')) {
      return;
    }
    setIsLoading('delete');
    setError(null);
    try {
      await deleteAssembly(assemblyId);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete assembly');
      setIsLoading(null);
    }
  };

  const hasAnyAction = canGenerateCitizens || canGenerateBriefing || canStartDeliberation || canDelete;

  if (!hasAnyAction && !error) {
    return null;
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="p-2 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {canGenerateCitizens && (
          <Button
            onClick={handleGenerateCitizens}
            disabled={isLoading !== null}
            variant="default"
          >
            {isLoading === 'citizens' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Users className="h-4 w-4 mr-2" />
            )}
            Generate Citizens
          </Button>
        )}

        {canGenerateBriefing && (
          <Button
            onClick={handleGenerateBriefing}
            disabled={isLoading !== null}
            variant="outline"
          >
            {isLoading === 'briefing' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <BookOpen className="h-4 w-4 mr-2" />
            )}
            {hasBriefing ? 'Regenerate Briefing' : 'Generate Briefing'}
          </Button>
        )}

        {canStartDeliberation && (
          <Button
            onClick={handleStartDeliberation}
            disabled={isLoading !== null}
          >
            {isLoading === 'deliberation' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Start Deliberation
          </Button>
        )}

        {canDelete && (
          <Button
            onClick={handleDelete}
            disabled={isLoading !== null}
            variant="destructive"
          >
            {isLoading === 'delete' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 mr-2" />
            )}
            Delete
          </Button>
        )}
      </div>
    </div>
  );
}
