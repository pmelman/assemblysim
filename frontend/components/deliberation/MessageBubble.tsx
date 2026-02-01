'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitizenAvatar } from '@/components/citizen/CitizenAvatar';
import { FactCheckBadge } from './FactCheckBadge';
import { CitationPopover } from './CitationPopover';
import { cn, formatTime } from '@/lib/utils';
import type { MessageResponse } from '@/lib/types';

interface MessageBubbleProps {
  message: MessageResponse;
  showTimestamp?: boolean;
}

const roleStyles = {
  moderator: {
    container: 'bg-blue-50 border-l-4 border-blue-400',
    label: 'Moderator',
    labelClass: 'text-blue-600',
  },
  citizen: {
    container: 'bg-white border border-gray-200',
    label: null,
    labelClass: '',
  },
  recorder: {
    container: 'bg-amber-50 border-l-4 border-amber-400',
    label: 'Recorder',
    labelClass: 'text-amber-600',
  },
  system: {
    container: 'bg-gray-50 text-gray-500 italic',
    label: 'System',
    labelClass: 'text-gray-500',
  },
};

export function MessageBubble({ message, showTimestamp = true }: MessageBubbleProps) {
  const style = roleStyles[message.role] || roleStyles.citizen;
  const isCitizen = message.role === 'citizen';

  return (
    <div className={cn('rounded-lg p-4', style.container)}>
      <div className="flex items-start gap-3">
        {isCitizen && message.citizen_name && (
          <CitizenAvatar name={message.citizen_name} size="sm" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-2 mb-1">
            {isCitizen && message.citizen_name ? (
              <span className="font-medium text-sm">{message.citizen_name}</span>
            ) : style.label ? (
              <span className={cn('font-medium text-sm', style.labelClass)}>
                {style.label}
              </span>
            ) : null}

            {message.fact_check_status && (
              <FactCheckBadge status={message.fact_check_status} />
            )}

            {showTimestamp && (
              <span className="text-xs text-muted-foreground ml-auto">
                {formatTime(message.created_at)}
              </span>
            )}
          </div>

          <div className="prose-sm text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>

          {message.citations && message.citations.length > 0 && (
            <div className="mt-2">
              <CitationPopover citations={message.citations} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
