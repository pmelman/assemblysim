'use client';

import { useEffect, useRef, useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { RoundDivider } from './RoundDivider';
import { LiveIndicator } from './LiveIndicator';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { MessageResponse, RoundPromptConfig } from '@/lib/types';
import { Search } from 'lucide-react';

interface MessageThreadProps {
  messages: MessageResponse[];
  isLoading?: boolean;
  isLive?: boolean;
  groupId?: number | null;
  autoScroll?: boolean;
  className?: string;
  roundPrompts?: RoundPromptConfig[] | null;
}

export function MessageThread({
  messages,
  isLoading,
  isLive,
  groupId,
  autoScroll = true,
  className,
  roundPrompts,
}: MessageThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [userHasScrolled, setUserHasScrolled] = useState(false);

  // Filter messages by group if specified
  const filteredMessages = groupId !== null && groupId !== undefined
    ? messages.filter((m) => m.group_id === groupId || m.group_id === null)
    : messages;

  // Get theme for a round number from roundPrompts
  const getTheme = (round: number): string | undefined => {
    if (!roundPrompts || round <= 0) return undefined;
    const idx = round - 1;
    if (idx < roundPrompts.length) return roundPrompts[idx].theme;
    return undefined;
  };

  // Group messages by round for dividers
  const messagesWithDividers: (MessageResponse | { type: 'divider'; round: number; phase: string; theme?: string })[] = [];
  let lastRound: number | null = null;
  let lastPhase: string | null = null;

  filteredMessages.forEach((message) => {
    const currentRound = message.round_number ?? 0;
    const currentPhase = message.phase;

    // Add divider for phase or round changes
    if (currentPhase !== lastPhase || (currentRound !== lastRound && currentRound > 0)) {
      messagesWithDividers.push({
        type: 'divider',
        round: currentRound,
        phase: currentPhase,
        theme: getTheme(currentRound),
      });
      lastRound = currentRound;
      lastPhase = currentPhase;
    }

    messagesWithDividers.push(message);
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && !userHasScrolled && scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages.length, autoScroll, userHasScrolled]);

  // Track user scroll to disable auto-scroll
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
    if (!scrollContainer) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setUserHasScrolled(!isAtBottom);
  };

  if (isLoading && filteredMessages.length === 0) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-20 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (filteredMessages.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-12 text-muted-foreground', className)}>
        <p>No messages yet</p>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)} ref={scrollRef}>
      {isLive && (
        <div className="absolute top-2 right-2 z-10">
          <LiveIndicator isLive={isLive} />
        </div>
      )}

      <ScrollArea className="h-[500px] pr-4" onScrollCapture={handleScroll}>
        <div className="space-y-4 pb-4">
          {messagesWithDividers.map((item, index) => {
            if ('type' in item && item.type === 'divider') {
              return (
                <RoundDivider
                  key={`divider-${item.round}-${item.phase}`}
                  round={item.round}
                  phase={item.phase}
                  theme={item.theme}
                />
              );
            }
            const message = item as MessageResponse;

            // Render research messages with distinct visual treatment
            if (message.role === 'system' && message.phase === 'research') {
              return (
                <div
                  key={message.id}
                  className="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-800 p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Search className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
                      Follow-up Research
                    </span>
                  </div>
                  <div className="text-sm text-blue-900 dark:text-blue-100 prose prose-sm max-w-none prose-blue">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: message.content
                          .replace(/^## (.+)$/gm, '<h4 class="text-blue-800 dark:text-blue-300 font-semibold mt-3 mb-1">$1</h4>')
                          .replace(/^### (.+)$/gm, '<h5 class="text-blue-700 dark:text-blue-400 font-medium mt-2 mb-1">$1</h5>')
                          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-blue-600 underline" target="_blank" rel="noopener noreferrer">$1</a>')
                          .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
                          .replace(/\n/g, '<br/>')
                      }}
                    />
                  </div>
                </div>
              );
            }

            return <MessageBubble key={message.id} message={message} />;
          })}

          {isLive && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="animate-pulse h-2 w-2 rounded-full bg-gray-400" />
              <span>Waiting for more messages...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {userHasScrolled && isLive && (
        <button
          onClick={() => {
            setUserHasScrolled(false);
            const scrollContainer = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
              scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
          }}
          className="absolute bottom-4 right-4 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs shadow-lg hover:bg-primary/90"
        >
          Scroll to latest
        </button>
      )}
    </div>
  );
}
