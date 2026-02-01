'use client';

import { useEffect, useCallback } from 'react';
import useSWR from 'swr';
import { listMessages } from '@/lib/api';
import { useWebSocket } from './useWebSocket';
import { useDeliberationStore } from '@/store/deliberationStore';
import { isActiveStatus } from '@/lib/utils';
import type { MessageResponse, AssemblyStatus, WSNewMessage } from '@/lib/types';

interface UseMessagesOptions {
  groupId?: number;
  phase?: string;
  roundNumber?: number;
  assemblyStatus?: AssemblyStatus;
}

interface UseMessagesReturn {
  messages: MessageResponse[];
  isLoading: boolean;
  error: Error | undefined;
  isLive: boolean;
  mutate: () => void;
}

const fetcher = ([, assemblyId, options]: [string, number, UseMessagesOptions]) =>
  listMessages(assemblyId, {
    groupId: options.groupId,
    phase: options.phase,
    roundNumber: options.roundNumber,
    limit: 500,
  });

export function useMessages(
  assemblyId: number | null,
  options: UseMessagesOptions = {}
): UseMessagesReturn {
  const { groupId, phase, roundNumber, assemblyStatus } = options;
  const isActive = assemblyStatus ? isActiveStatus(assemblyStatus) : false;

  // Zustand store for live messages
  const { liveMessages, addMessage, clearMessages, setMessages } = useDeliberationStore();

  // SWR for initial/historical messages
  const { data, error, isLoading, mutate } = useSWR(
    assemblyId !== null ? ['messages', assemblyId, { groupId, phase, roundNumber }] : null,
    fetcher,
    {
      refreshInterval: isActive ? 5000 : 0, // Poll during active states as backup
      revalidateOnFocus: false,
    }
  );

  // Initialize store with fetched messages
  useEffect(() => {
    if (data && assemblyId !== null) {
      setMessages(assemblyId, data);
    }
  }, [data, assemblyId, setMessages]);

  // Handle new WebSocket messages
  const handleNewMessage = useCallback(
    (wsMessage: WSNewMessage) => {
      if (assemblyId === null) return;

      // Convert WebSocket message to MessageResponse format
      const message: MessageResponse = {
        id: wsMessage.message_id,
        assembly_id: assemblyId,
        group_id: null,
        citizen_id: wsMessage.citizen_id ?? null,
        citizen_name: wsMessage.citizen_name ?? null,
        phase: wsMessage.phase ?? 'deliberation',
        round_number: wsMessage.round_number ?? null,
        role: wsMessage.role,
        content: wsMessage.content,
        citations: null,
        fact_check_status: null,
        created_at: new Date().toISOString(),
      };

      addMessage(assemblyId, message);
    },
    [assemblyId, addMessage]
  );

  // WebSocket connection for live updates
  const { isConnected } = useWebSocket(isActive ? assemblyId : null, {
    onNewMessage: handleNewMessage,
    onConnect: () => {
      // Refresh messages when reconnecting
      mutate();
    },
  });

  // Clear messages when assembly changes
  useEffect(() => {
    return () => {
      if (assemblyId !== null) {
        clearMessages(assemblyId);
      }
    };
  }, [assemblyId, clearMessages]);

  // Get messages from store (includes live messages)
  const messages = assemblyId !== null ? (liveMessages[assemblyId] ?? data ?? []) : [];

  return {
    messages,
    isLoading,
    error,
    isLive: isConnected && isActive,
    mutate,
  };
}
