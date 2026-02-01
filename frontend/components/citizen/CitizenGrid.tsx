'use client';

import { useState } from 'react';
import { CitizenCard } from './CitizenCard';
import { CitizenDetailModal } from './CitizenDetailModal';
import type { CitizenResponse, GroupResponse } from '@/lib/types';

interface CitizenGridProps {
  citizens: CitizenResponse[];
  groups?: GroupResponse[];
  assemblyId: number;
}

export function CitizenGrid({ citizens, groups, assemblyId }: CitizenGridProps) {
  const [selectedCitizen, setSelectedCitizen] = useState<CitizenResponse | null>(null);

  // Group citizens by group_id if groups exist
  const citizensByGroup = groups && groups.length > 0
    ? groups.map((group) => ({
        group,
        citizens: citizens.filter((c) => c.group_id === group.id),
      }))
    : [{ group: null, citizens }];

  return (
    <>
      <div className="space-y-6">
        {citizensByGroup.map(({ group, citizens: groupCitizens }) => (
          <div key={group?.id ?? 'all'} className="space-y-3">
            {group && (
              <h3 className="text-sm font-medium text-muted-foreground">
                Group {group.name} ({groupCitizens.length} citizens)
              </h3>
            )}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {groupCitizens.map((citizen) => (
                <CitizenCard
                  key={citizen.id}
                  citizen={citizen}
                  onClick={() => setSelectedCitizen(citizen)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <CitizenDetailModal
        citizen={selectedCitizen}
        assemblyId={assemblyId}
        open={selectedCitizen !== null}
        onOpenChange={(open) => !open && setSelectedCitizen(null)}
      />
    </>
  );
}
