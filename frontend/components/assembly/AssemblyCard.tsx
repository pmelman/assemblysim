'use client';

import Link from 'next/link';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from './StatusBadge';
import { formatDate, truncate, pluralize } from '@/lib/utils';
import type { AssemblyResponse } from '@/lib/types';
import { Users, Calendar, MessageSquare } from 'lucide-react';

interface AssemblyCardProps {
  assembly: AssemblyResponse;
}

export function AssemblyCard({ assembly }: AssemblyCardProps) {
  return (
    <Link href={`/assemblies/${assembly.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-lg leading-tight">
              {truncate(assembly.topic, 80)}
            </CardTitle>
            <StatusBadge status={assembly.status} />
          </div>
        </CardHeader>
        <CardContent className="pb-2">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>{assembly.num_citizens} {pluralize('citizen', assembly.num_citizens)}</span>
            </div>
            <div className="flex items-center gap-1">
              <MessageSquare className="h-4 w-4" />
              <span>{assembly.num_rounds} {pluralize('round', assembly.num_rounds)}</span>
            </div>
          </div>
        </CardContent>
        <CardFooter className="pt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>Created {formatDate(assembly.created_at)}</span>
          </div>
        </CardFooter>
      </Card>
    </Link>
  );
}
