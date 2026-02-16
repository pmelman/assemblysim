'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  listCustomCitizens,
  createCustomCitizen,
  updateCustomCitizen,
  deleteCustomCitizen,
} from '@/lib/api';
import type { CustomCitizenTemplate, CustomCitizenCreateRequest } from '@/lib/types';
import { Loader2, Plus, Pencil, Trash2, User } from 'lucide-react';

const POLITICAL_LEANINGS = [
  'Extremely Liberal',
  'Liberal',
  'Slightly Liberal',
  'Moderate',
  'Slightly Conservative',
  'Conservative',
  'Extremely Conservative',
];

interface CitizenFormData {
  name: string;
  mode: 'traits' | 'full';
  background_summary: string;
  key_values_text: string; // comma-separated for easy editing
  demographic_tags_text: string; // comma-separated
  political_leaning: string;
  system_prompt: string;
}

const EMPTY_FORM: CitizenFormData = {
  name: '',
  mode: 'traits',
  background_summary: '',
  key_values_text: '',
  demographic_tags_text: '',
  political_leaning: '',
  system_prompt: '',
};

function formDataToRequest(form: CitizenFormData): CustomCitizenCreateRequest {
  const keyValues = form.key_values_text
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
  const tags = form.demographic_tags_text
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);

  return {
    name: form.name,
    mode: form.mode,
    background_summary: form.background_summary || null,
    key_values: keyValues.length > 0 ? keyValues : null,
    demographic_tags: tags.length > 0 ? tags : null,
    political_leaning: form.political_leaning || null,
    system_prompt: form.mode === 'full' ? form.system_prompt : null,
  };
}

function templateToFormData(t: CustomCitizenTemplate): CitizenFormData {
  return {
    name: t.name,
    mode: t.mode as 'traits' | 'full',
    background_summary: t.background_summary || '',
    key_values_text: (t.key_values || []).join(', '),
    demographic_tags_text: (t.demographic_tags || []).join(', '),
    political_leaning: t.political_leaning || '',
    system_prompt: t.system_prompt || '',
  };
}

export default function CustomCitizensPage() {
  const [citizens, setCitizens] = useState<CustomCitizenTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<CitizenFormData>(EMPTY_FORM);
  const [isSaving, setIsSaving] = useState(false);

  // Delete confirmation
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Expanded system prompt view
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadCitizens = async () => {
    try {
      const data = await listCustomCitizens();
      setCitizens(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load custom citizens');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCitizens();
  }, []);

  const openCreateDialog = () => {
    setEditingId(null);
    setFormData(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEditDialog = (citizen: CustomCitizenTemplate) => {
    setEditingId(citizen.id);
    setFormData(templateToFormData(citizen));
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);

    try {
      const request = formDataToRequest(formData);

      if (editingId) {
        await updateCustomCitizen(editingId, request);
      } else {
        await createCustomCitizen(request);
      }

      setDialogOpen(false);
      await loadCitizens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save custom citizen');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setIsDeleting(true);

    try {
      await deleteCustomCitizen(deleteId);
      setDeleteId(null);
      await loadCitizens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete custom citizen');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-8 flex justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Custom Citizens</h1>
          <p className="text-muted-foreground">
            Create reusable citizen personas to include in assemblies
          </p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="h-4 w-4 mr-2" />
          Create Custom Citizen
        </Button>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      )}

      {citizens.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No custom citizens yet</h3>
            <p className="text-muted-foreground mb-4">
              Create custom citizen personas to pre-seed your assemblies with specific viewpoints.
            </p>
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Custom Citizen
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {citizens.map((citizen) => (
            <Card key={citizen.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg">{citizen.name}</h3>
                      <Badge variant={citizen.mode === 'traits' ? 'blue' : 'purple'}>
                        {citizen.mode}
                      </Badge>
                      {citizen.political_leaning && (
                        <Badge variant="outline">{citizen.political_leaning}</Badge>
                      )}
                    </div>
                    {citizen.background_summary && (
                      <p className="text-sm text-muted-foreground">
                        {citizen.background_summary}
                      </p>
                    )}
                    {citizen.key_values && citizen.key_values.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {citizen.key_values.map((value, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {value}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {citizen.demographic_tags && citizen.demographic_tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {citizen.demographic_tags.map((tag, i) => (
                          <Badge key={i} variant="gray" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {citizen.system_prompt && (
                      <div>
                        <button
                          type="button"
                          className="text-xs text-blue-600 hover:underline"
                          onClick={() =>
                            setExpandedId(expandedId === citizen.id ? null : citizen.id)
                          }
                        >
                          {expandedId === citizen.id ? 'Hide' : 'Show'} system prompt
                        </button>
                        {expandedId === citizen.id && (
                          <pre className="mt-2 p-3 bg-muted rounded-md text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                            {citizen.system_prompt}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1 ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(citizen)}
                      className="h-8 w-8 p-0"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteId(citizen.id)}
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingId ? 'Edit Custom Citizen' : 'Create Custom Citizen'}
            </DialogTitle>
            <DialogDescription>
              {editingId
                ? 'Update this custom citizen template.'
                : 'Define a custom citizen to include in future assemblies.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="citizen-name">Name</Label>
              <Input
                id="citizen-name"
                placeholder="e.g., Maria Rodriguez"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <Tabs
              value={formData.mode}
              onValueChange={(v) => setFormData({ ...formData, mode: v as 'traits' | 'full' })}
            >
              <TabsList className="w-full">
                <TabsTrigger value="traits" className="flex-1">
                  Traits (Auto-generate)
                </TabsTrigger>
                <TabsTrigger value="full" className="flex-1">
                  Full Persona
                </TabsTrigger>
              </TabsList>

              <TabsContent value="traits" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="background">Background Summary</Label>
                  <Textarea
                    id="background"
                    placeholder="Brief description of the citizen's background, e.g., 'A 45-year-old small business owner from rural Texas who grew up in a farming community...'"
                    value={formData.background_summary}
                    onChange={(e) =>
                      setFormData({ ...formData, background_summary: e.target.value })
                    }
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="political-leaning">Political Leaning</Label>
                  <Select
                    id="political-leaning"
                    value={formData.political_leaning}
                    onChange={(e) =>
                      setFormData({ ...formData, political_leaning: e.target.value })
                    }
                  >
                    <option value="">Select...</option>
                    {POLITICAL_LEANINGS.map((leaning) => (
                      <option key={leaning} value={leaning}>
                        {leaning}
                      </option>
                    ))}
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="key-values">Core Values (comma-separated)</Label>
                  <Input
                    id="key-values"
                    placeholder="e.g., family, faith, self-reliance, community"
                    value={formData.key_values_text}
                    onChange={(e) =>
                      setFormData({ ...formData, key_values_text: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="demo-tags">Demographic Tags (comma-separated)</Label>
                  <Input
                    id="demo-tags"
                    placeholder="e.g., rural, middle-class, veteran, parent"
                    value={formData.demographic_tags_text}
                    onChange={(e) =>
                      setFormData({ ...formData, demographic_tags_text: e.target.value })
                    }
                  />
                </div>

                <p className="text-xs text-muted-foreground">
                  The LLM will generate a full persona system prompt from these traits.
                </p>
              </TabsContent>

              <TabsContent value="full" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="system-prompt">System Prompt</Label>
                  <Textarea
                    id="system-prompt"
                    placeholder="You are [name], a [description]..."
                    value={formData.system_prompt}
                    onChange={(e) =>
                      setFormData({ ...formData, system_prompt: e.target.value })
                    }
                    rows={10}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Write the full persona description that will be used as the citizen&apos;s system
                    prompt during deliberation.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="background-full">
                    Background Summary (optional, for display)
                  </Label>
                  <Textarea
                    id="background-full"
                    placeholder="Brief summary shown in the UI..."
                    value={formData.background_summary}
                    onChange={(e) =>
                      setFormData({ ...formData, background_summary: e.target.value })
                    }
                    rows={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="key-values-full">Core Values (comma-separated, optional)</Label>
                  <Input
                    id="key-values-full"
                    placeholder="e.g., justice, equality, pragmatism"
                    value={formData.key_values_text}
                    onChange={(e) =>
                      setFormData({ ...formData, key_values_text: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="political-leaning-full">Political Leaning (optional)</Label>
                  <Select
                    id="political-leaning-full"
                    value={formData.political_leaning}
                    onChange={(e) =>
                      setFormData({ ...formData, political_leaning: e.target.value })
                    }
                  >
                    <option value="">Select...</option>
                    {POLITICAL_LEANINGS.map((leaning) => (
                      <option key={leaning} value={leaning}>
                        {leaning}
                      </option>
                    ))}
                  </Select>
                </div>
              </TabsContent>
            </Tabs>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={isSaving}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || !formData.name || (formData.mode === 'full' && !formData.system_prompt)}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {formData.mode === 'traits' ? 'Generating...' : 'Saving...'}
                </>
              ) : editingId ? (
                'Update'
              ) : (
                'Create'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Custom Citizen</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this custom citizen template? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
