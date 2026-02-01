'use client';

import { StatusBadge } from './StatusBadge';
import { formatDateTime, pluralize } from '@/lib/utils';
import type { AssemblyDetailResponse } from '@/lib/types';
import { Users, MessageSquare, Calendar, Clock } from 'lucide-react';

interface AssemblyHeaderProps {
  assembly: AssemblyDetailResponse;
}

export function AssemblyHeader({ assembly }: AssemblyHeaderProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">{assembly.topic}</h1>
          <p className="text-sm text-muted-foreground">
            Assembly #{assembly.id}
          </p>
        </div>
        <StatusBadge status={assembly.status} className="text-sm" />
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-1">
          <Users className="h-4 w-4" />
          <span>
            {assembly.citizens.length} / {assembly.num_citizens} {pluralize('citizen', assembly.num_citizens)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <MessageSquare className="h-4 w-4" />
          <span>
            {assembly.num_groups} {pluralize('group', assembly.num_groups)}, {assembly.num_rounds} {pluralize('round', assembly.num_rounds)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="h-4 w-4" />
          <span>Created {formatDateTime(assembly.created_at)}</span>
        </div>
        {assembly.completed_at && (
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>Completed {formatDateTime(assembly.completed_at)}</span>
          </div>
        )}
      </div>

      {assembly.error_message && (
        <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
          <strong>Error:</strong> {assembly.error_message}
        </div>
      )}
    </div>
  );
}
