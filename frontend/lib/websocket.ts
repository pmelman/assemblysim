/**
 * WebSocket Client for Silicon Citizens' Assembly
 * Handles real-time updates for assembly status and deliberation messages
 */

import type { WSMessage, WSStatusUpdate, WSNewMessage } from './types';

type MessageHandler = (message: WSMessage) => void;
type StatusHandler = (status: WSStatusUpdate) => void;
type NewMessageHandler = (message: WSNewMessage) => void;
type ErrorHandler = (error: Event | Error) => void;
type ConnectionHandler = () => void;

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export class AssemblyWebSocket {
  private ws: WebSocket | null = null;
  private assemblyId: number;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private isClosing = false;

  // Event handlers
  private onMessageHandlers: Set<MessageHandler> = new Set();
  private onStatusHandlers: Set<StatusHandler> = new Set();
  private onNewMessageHandlers: Set<NewMessageHandler> = new Set();
  private onErrorHandlers: Set<ErrorHandler> = new Set();
  private onConnectHandlers: Set<ConnectionHandler> = new Set();
  private onDisconnectHandlers: Set<ConnectionHandler> = new Set();

  constructor(assemblyId: number) {
    this.assemblyId = assemblyId;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isClosing = false;
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      console.warn('WebSocket: No auth token available, skipping connection');
      return;
    }
    const url = `${WS_BASE_URL}/ws/assemblies/${this.assemblyId}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.startPingInterval();
        this.onConnectHandlers.forEach((handler) => handler());
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (event) => {
        this.onErrorHandlers.forEach((handler) => handler(event));
      };

      this.ws.onclose = () => {
        this.stopPingInterval();
        this.onDisconnectHandlers.forEach((handler) => handler());

        if (!this.isClosing && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      if (error instanceof Error) {
        this.onErrorHandlers.forEach((handler) => handler(error));
      }
    }
  }

  disconnect(): void {
    this.isClosing = true;
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private handleMessage(message: WSMessage): void {
    // Notify all generic message handlers
    this.onMessageHandlers.forEach((handler) => handler(message));

    // Handle specific message types
    switch (message.type) {
      case 'status_update':
        if (message.data) {
          this.onStatusHandlers.forEach((handler) =>
            handler(message.data as unknown as WSStatusUpdate)
          );
        }
        break;

      case 'new_message':
        if (message.data) {
          this.onNewMessageHandlers.forEach((handler) =>
            handler(message.data as unknown as WSNewMessage)
          );
        }
        break;

      case 'error':
        this.onErrorHandlers.forEach((handler) =>
          handler(new Error(message.message || 'WebSocket error'))
        );
        break;

      case 'pong':
        // Ping response received, connection is alive
        break;

      case 'connected':
      case 'subscribed':
      case 'status':
        // These are handled by generic handlers
        break;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(
      `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );
    setTimeout(() => this.connect(), delay);
  }

  private startPingInterval(): void {
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  // Send a message to the server
  send(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  // Request current status
  requestStatus(): void {
    this.send({ type: 'get_status' });
  }

  // Event subscription methods
  onMessage(handler: MessageHandler): () => void {
    this.onMessageHandlers.add(handler);
    return () => this.onMessageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.onStatusHandlers.add(handler);
    return () => this.onStatusHandlers.delete(handler);
  }

  onNewMessage(handler: NewMessageHandler): () => void {
    this.onNewMessageHandlers.add(handler);
    return () => this.onNewMessageHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.onErrorHandlers.add(handler);
    return () => this.onErrorHandlers.delete(handler);
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.onConnectHandlers.add(handler);
    return () => this.onConnectHandlers.delete(handler);
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.onDisconnectHandlers.add(handler);
    return () => this.onDisconnectHandlers.delete(handler);
  }

  // Connection state
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Factory function for creating WebSocket connections
export function createAssemblyWebSocket(assemblyId: number): AssemblyWebSocket {
  return new AssemblyWebSocket(assemblyId);
}
