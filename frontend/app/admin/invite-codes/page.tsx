'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createInviteCode, listInviteCodes } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import type { InviteCodeResponse } from '@/lib/types';

export default function InviteCodesPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const [codes, setCodes] = useState<InviteCodeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState<number | null>(null);

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || !user?.is_admin)) {
      router.push('/');
      return;
    }
    if (isAuthenticated && user?.is_admin) {
      fetchCodes();
    }
  }, [isAuthenticated, user, authLoading, router]);

  const fetchCodes = async () => {
    try {
      const result = await listInviteCodes();
      setCodes(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load invite codes');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const newCode = await createInviteCode();
      setCodes((prev) => [newCode, ...prev]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create invite code');
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async (code: string, id: number) => {
    await navigator.clipboard.writeText(code);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Invite Codes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generate codes to invite new users
          </p>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {creating ? 'Generating...' : 'Generate Code'}
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-lg border bg-card">
        {codes.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No invite codes yet. Generate one to get started.
          </div>
        ) : (
          <div className="divide-y">
            {codes.map((code) => (
              <div key={code.id} className="flex items-center justify-between p-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <code className="rounded bg-muted px-2 py-0.5 text-sm font-mono">
                      {code.code}
                    </code>
                    <button
                      onClick={() => handleCopy(code.code, code.id)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      {copied === code.id ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Created {new Date(code.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  {code.used_at ? (
                    <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium">
                      Used by {code.used_by_username}
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 px-2.5 py-0.5 text-xs font-medium">
                      Available
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
