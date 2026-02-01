'use client';

import useSWR from 'swr';
import { getAssembly } from '@/lib/api';
import { isActiveStatus } from '@/lib/utils';
import type { AssemblyDetailResponse } from '@/lib/types';

interface UseAssemblyOptions {
  refreshInterval?: number;
}

interface UseAssemblyReturn {
  assembly: AssemblyDetailResponse | undefined;
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => void;
}

const fetcher = (id: number) => getAssembly(id);

export function useAssembly(
  assemblyId: number | null,
  options: UseAssemblyOptions = {}
): UseAssemblyReturn {
  const { data, error, isLoading, mutate } = useSWR(
    assemblyId !== null ? ['assembly', assemblyId] : null,
    () => fetcher(assemblyId!),
    {
      // Adaptive refresh: faster when active, slower otherwise
      refreshInterval: (data) => {
        if (options.refreshInterval !== undefined) {
          return options.refreshInterval;
        }
        if (data && isActiveStatus(data.status)) {
          return 3000; // 3 seconds when active
        }
        return 30000; // 30 seconds when idle
      },
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  return {
    assembly: data,
    isLoading,
    error,
    mutate,
  };
}
