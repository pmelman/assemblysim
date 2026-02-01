import { create } from 'zustand';
import type { MessageResponse, AssemblyStatus } from '@/lib/types';

interface DeliberationState {
  // Live messages by assembly ID
  liveMessages: Record<number, MessageResponse[]>;

  // Current assembly status (for real-time updates)
  assemblyStatuses: Record<number, AssemblyStatus>;

  // Actions
  setMessages: (assemblyId: number, messages: MessageResponse[]) => void;
  addMessage: (assemblyId: number, message: MessageResponse) => void;
  clearMessages: (assemblyId: number) => void;
  setAssemblyStatus: (assemblyId: number, status: AssemblyStatus) => void;
}

export const useDeliberationStore = create<DeliberationState>((set) => ({
  liveMessages: {},
  assemblyStatuses: {},

  setMessages: (assemblyId, messages) =>
    set((state) => ({
      liveMessages: {
        ...state.liveMessages,
        [assemblyId]: messages,
      },
    })),

  addMessage: (assemblyId, message) =>
    set((state) => {
      const existingMessages = state.liveMessages[assemblyId] ?? [];

      // Avoid duplicates
      if (existingMessages.some((m) => m.id === message.id)) {
        return state;
      }

      return {
        liveMessages: {
          ...state.liveMessages,
          [assemblyId]: [...existingMessages, message],
        },
      };
    }),

  clearMessages: (assemblyId) =>
    set((state) => {
      const { [assemblyId]: _, ...rest } = state.liveMessages;
      return { liveMessages: rest };
    }),

  setAssemblyStatus: (assemblyId, status) =>
    set((state) => ({
      assemblyStatuses: {
        ...state.assemblyStatuses,
        [assemblyId]: status,
      },
    })),
}));
