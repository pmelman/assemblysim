'use client';

import useSWR from 'swr';
import { getAppSettings } from '@/lib/api';
import type { AppSettings } from '@/lib/types';

const fetcher = () => getAppSettings();

export function useSettings() {
  const { data, error, isLoading, mutate } = useSWR<AppSettings>(
    'app-settings',
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );

  return {
    settings: data,
    isLoading,
    error,
    mutate,
  };
}
