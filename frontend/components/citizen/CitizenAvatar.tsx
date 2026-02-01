'use client';

import { cn, getInitials, stringToColor } from '@/lib/utils';

interface CitizenAvatarProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
};

export function CitizenAvatar({ name, size = 'md', className }: CitizenAvatarProps) {
  const initials = getInitials(name);
  const colorClass = stringToColor(name);

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full text-white font-medium',
        colorClass,
        sizeClasses[size],
        className
      )}
    >
      {initials}
    </div>
  );
}
