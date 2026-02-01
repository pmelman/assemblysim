'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { createAssembly } from '@/lib/api';
import type { AssemblyCreateRequest } from '@/lib/types';
import { Loader2 } from 'lucide-react';

export function AssemblyCreateForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<AssemblyCreateRequest>({
    topic: '',
    num_citizens: 40,
    num_groups: 5,
    num_rounds: 3,
    sampling_strategy: 'stratified',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const assembly = await createAssembly(formData);
      router.push(`/assemblies/${assembly.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create assembly');
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="max-w-2xl mx-auto">
      <form onSubmit={handleSubmit}>
        <CardHeader>
          <CardTitle>Create New Assembly</CardTitle>
          <CardDescription>
            Configure a new citizens&apos; assembly for deliberation on a policy topic
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="topic">Policy Topic</Label>
            <Textarea
              id="topic"
              placeholder="e.g., Should the United States implement a Universal Basic Income?"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              required
              minLength={5}
              maxLength={500}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Enter a clear policy question for citizens to deliberate on (5-500 characters)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="num_citizens">Number of Citizens</Label>
              <Input
                id="num_citizens"
                type="number"
                min={8}
                max={100}
                value={formData.num_citizens}
                onChange={(e) => setFormData({ ...formData, num_citizens: parseInt(e.target.value) || 40 })}
              />
              <p className="text-xs text-muted-foreground">8-100 citizens</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="num_groups">Number of Groups</Label>
              <Input
                id="num_groups"
                type="number"
                min={1}
                max={10}
                value={formData.num_groups}
                onChange={(e) => setFormData({ ...formData, num_groups: parseInt(e.target.value) || 5 })}
              />
              <p className="text-xs text-muted-foreground">1-10 groups</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="num_rounds">Deliberation Rounds</Label>
              <Input
                id="num_rounds"
                type="number"
                min={1}
                max={10}
                value={formData.num_rounds}
                onChange={(e) => setFormData({ ...formData, num_rounds: parseInt(e.target.value) || 3 })}
              />
              <p className="text-xs text-muted-foreground">1-10 rounds</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sampling_strategy">Sampling Strategy</Label>
              <Select
                id="sampling_strategy"
                value={formData.sampling_strategy}
                onChange={(e) => setFormData({ ...formData, sampling_strategy: e.target.value as 'stratified' | 'quota' | 'random' })}
              >
                <option value="stratified">Stratified</option>
                <option value="quota">Quota</option>
                <option value="random">Random</option>
              </Select>
              <p className="text-xs text-muted-foreground">
                How citizens are selected from GSS data
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push('/')}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || formData.topic.length < 5}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Assembly'
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
