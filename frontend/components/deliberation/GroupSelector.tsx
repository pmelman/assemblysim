'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { GroupResponse } from '@/lib/types';

interface GroupSelectorProps {
  groups: GroupResponse[];
  selectedGroupId: number | null;
  onSelectGroup: (groupId: number | null) => void;
  className?: string;
}

export function GroupSelector({
  groups,
  selectedGroupId,
  onSelectGroup,
  className,
}: GroupSelectorProps) {
  // Only show if there are multiple groups
  if (groups.length <= 1) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      <Button
        variant={selectedGroupId === null ? 'default' : 'outline'}
        size="sm"
        onClick={() => onSelectGroup(null)}
      >
        All Groups
      </Button>
      {groups.map((group) => (
        <Button
          key={group.id}
          variant={selectedGroupId === group.id ? 'default' : 'outline'}
          size="sm"
          onClick={() => onSelectGroup(group.id)}
        >
          Group {group.name} ({group.citizen_count})
        </Button>
      ))}
    </div>
  );
}
