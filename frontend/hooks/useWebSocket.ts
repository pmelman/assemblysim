'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { AssemblyWebSocket } from '@/lib/websocket';
import type { WSMessage, WSStatusUpdate, WSNewMessage } from '@/lib/types';

interface UseWebSocketOptions {
  onMessage?: (message: WSMessage) => void;
  onStatus?: (status: WSStatusUpdate) => void;
  onNewMessage?: (message: WSNewMessage) => void;
  onError?: (error: Event | Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoConnect?: boolean;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  send: (message: Record<string, unknown>) => void;
  requestStatus: () => void;
}

export function useWebSocket(
  assemblyId: number | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const wsRef = useRef<AssemblyWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const optionsRef = useRef(options);

  // Keep options ref updated
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (assemblyId === null || wsRef.current?.isConnected) return;

    const ws = new AssemblyWebSocket(assemblyId);

    // Set up event handlers
    ws.onConnect(() => {
      setIsConnected(true);
      optionsRef.current.onConnect?.();
    });

    ws.onDisconnect(() => {
      setIsConnected(false);
      optionsRef.current.onDisconnect?.();
    });

    ws.onMessage((message) => {
      optionsRef.current.onMessage?.(message);
    });

    ws.onStatus((status) => {
      optionsRef.current.onStatus?.(status);
    });

    ws.onNewMessage((message) => {
      optionsRef.current.onNewMessage?.(message);
    });

    ws.onError((error) => {
      optionsRef.current.onError?.(error);
    });

    ws.connect();
    wsRef.current = ws;
  }, [assemblyId]);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const send = useCallback((message: Record<string, unknown>) => {
    wsRef.current?.send(message);
  }, []);

  const requestStatus = useCallback(() => {
    wsRef.current?.requestStatus();
  }, []);

  // Auto-connect when assemblyId changes
  useEffect(() => {
    if (assemblyId !== null && options.autoConnect !== false) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [assemblyId, connect, disconnect, options.autoConnect]);

  return {
    isConnected,
    connect,
    disconnect,
    send,
    requestStatus,
  };
}
