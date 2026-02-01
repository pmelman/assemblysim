'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { AssemblyCard } from '@/components/assembly/AssemblyCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useAssemblies } from '@/hooks/useAssemblies';
import { Plus, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const { assemblies, isLoading, error, mutate } = useAssemblies();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Assemblies</h1>
          <p className="text-muted-foreground mt-1">
            Manage and view citizens&apos; assembly deliberations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => mutate()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Link href="/assemblies/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Assembly
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 text-red-600 bg-red-50 rounded-md border border-red-200">
          <p className="font-medium">Failed to load assemblies</p>
          <p className="text-sm mt-1">{error.message}</p>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      ) : assemblies?.assemblies.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <Plus className="h-8 w-8 text-muted-foreground" />
          </div>
          <h2 className="text-xl font-semibold">No assemblies yet</h2>
          <p className="text-muted-foreground mt-1 max-w-md">
            Create your first citizens&apos; assembly to start deliberating on policy topics
            with AI-generated personas based on GSS data.
          </p>
          <Link href="/assemblies/new" className="mt-4">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Assembly
            </Button>
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {assemblies?.assemblies.map((assembly) => (
              <AssemblyCard key={assembly.id} assembly={assembly} />
            ))}
          </div>

          {assemblies && assemblies.total > assemblies.page_size && (
            <div className="flex justify-center">
              <p className="text-sm text-muted-foreground">
                Showing {assemblies.assemblies.length} of {assemblies.total} assemblies
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
