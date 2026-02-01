'use client';

import useSWR from 'swr';
import { listAssemblies } from '@/lib/api';
import type { AssemblyListResponse } from '@/lib/types';

interface UseAssembliesOptions {
  page?: number;
  pageSize?: number;
  status?: string;
  refreshInterval?: number;
}

interface UseAssembliesReturn {
  assemblies: AssemblyListResponse | undefined;
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => void;
}

const fetcher = ([, page, pageSize, status]: [string, number, number, string | undefined]) =>
  listAssemblies(page, pageSize, status);

export function useAssemblies(options: UseAssembliesOptions = {}): UseAssembliesReturn {
  const { page = 1, pageSize = 20, status, refreshInterval = 10000 } = options;

  const { data, error, isLoading, mutate } = useSWR(
    ['assemblies', page, pageSize, status],
    fetcher,
    {
      refreshInterval,
      revalidateOnFocus: true,
    }
  );

  return {
    assemblies: data,
    isLoading,
    error,
    mutate,
  };
}
