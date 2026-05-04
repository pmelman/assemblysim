'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  createAssembly,
  getAppSettings,
  listCustomCitizens,
  listAssemblyProfiles,
  createAssemblyProfile,
  updateAssemblyProfile,
  deleteAssemblyProfile,
} from '@/lib/api';
import type {
  AssemblyCreateRequest,
  RoundPromptConfig,
  CustomCitizenTemplate,
  AssemblyProfile,
  AssemblyProfileConfig,
} from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, Trash2, ChevronDown, ChevronRight, User, Save } from 'lucide-react';

const DEFAULT_ROUND_PROMPTS: RoundPromptConfig[] = [
  {
    theme: 'Initial Reactions',
    prompt: 'Focus on first impressions and personal connections to the topic. Encourage citizens to share how this issue affects them personally.',
  },
  {
    theme: 'Trade-offs & Evidence',
    prompt: 'Push citizens to engage with the briefing evidence and consider trade-offs. Challenge assumptions and encourage them to respond to points raised by others.',
  },
  {
    theme: 'Synthesis & Recommendations',
    prompt: 'Guide the discussion toward actionable recommendations. Ask citizens to identify areas of agreement and propose specific policy options.',
  },
];

export function AssemblyCreateForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  const [formData, setFormData] = useState<AssemblyCreateRequest>({
    topic: '',
    num_citizens: 40,
    num_groups: 5,
    num_rounds: 3,
    sampling_strategy: 'stratified',
    max_research_calls_per_round: 2,
    max_research_tokens_per_call: 2000,
  });

  const [roundPrompts, setRoundPrompts] = useState<RoundPromptConfig[]>(DEFAULT_ROUND_PROMPTS);
  const [showRoundPrompts, setShowRoundPrompts] = useState(false);
  const [showResearchSettings, setShowResearchSettings] = useState(false);
  const [showCustomCitizens, setShowCustomCitizens] = useState(false);
  const [customCitizens, setCustomCitizens] = useState<CustomCitizenTemplate[]>([]);
  const [selectedCustomIds, setSelectedCustomIds] = useState<Set<number>>(new Set());

  const [profiles, setProfiles] = useState<AssemblyProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);

  const refreshProfiles = () =>
    listAssemblyProfiles()
      .then(setProfiles)
      .catch(() => {
        // Profiles API not available
      });

  // Fetch defaults from settings and custom citizens on mount
  useEffect(() => {
    getAppSettings()
      .then((settings) => {
        setFormData((prev) => ({
          ...prev,
          num_citizens: settings.default_num_citizens,
          num_groups: settings.default_num_groups,
          num_rounds: settings.default_num_rounds,
          sampling_strategy: settings.default_sampling_strategy as 'stratified' | 'quota' | 'random',
          max_research_calls_per_round: settings.default_max_research_calls_per_round,
          max_research_tokens_per_call: settings.default_max_research_tokens_per_call,
        }));
        if (settings.default_round_prompts && settings.default_round_prompts.length > 0) {
          setRoundPrompts(settings.default_round_prompts);
        }
        setSettingsLoaded(true);
      })
      .catch(() => {
        // Settings API not available, use hardcoded defaults
        setSettingsLoaded(true);
      });

    listCustomCitizens()
      .then(setCustomCitizens)
      .catch(() => {
        // Custom citizens API not available
      });

    refreshProfiles();
  }, []);

  const buildConfigFromForm = (): AssemblyProfileConfig => {
    const hasRoundPrompts = roundPrompts.some((rp) => rp.theme || rp.prompt);
    const customIds = Array.from(selectedCustomIds);
    return {
      num_citizens: formData.num_citizens,
      num_groups: formData.num_groups,
      num_rounds: formData.num_rounds,
      sampling_strategy: formData.sampling_strategy,
      round_prompts: hasRoundPrompts ? roundPrompts : null,
      max_research_calls_per_round: formData.max_research_calls_per_round,
      max_research_tokens_per_call: formData.max_research_tokens_per_call,
      custom_citizen_ids: customIds.length > 0 ? customIds : null,
      topic: formData.topic || undefined,
    };
  };

  const applyConfig = (config: AssemblyProfileConfig) => {
    setFormData((prev) => ({
      ...prev,
      topic: config.topic ?? prev.topic,
      num_citizens: config.num_citizens ?? prev.num_citizens,
      num_groups: config.num_groups ?? prev.num_groups,
      num_rounds: config.num_rounds ?? prev.num_rounds,
      sampling_strategy: (config.sampling_strategy ?? prev.sampling_strategy) as
        | 'stratified'
        | 'quota'
        | 'random',
      max_research_calls_per_round:
        config.max_research_calls_per_round ?? prev.max_research_calls_per_round,
      max_research_tokens_per_call:
        config.max_research_tokens_per_call ?? prev.max_research_tokens_per_call,
    }));
    if (config.round_prompts && config.round_prompts.length > 0) {
      setRoundPrompts(config.round_prompts);
    }
    if (config.custom_citizen_ids) {
      setSelectedCustomIds(new Set(config.custom_citizen_ids));
    } else {
      setSelectedCustomIds(new Set());
    }
  };

  const handleLoadProfile = (id: number) => {
    const profile = profiles.find((p) => p.id === id);
    if (!profile) return;
    setSelectedProfileId(id);
    applyConfig(profile.config);
    setProfileMessage(`Loaded "${profile.name}"`);
    setTimeout(() => setProfileMessage(null), 2500);
  };

  const handleSaveProfile = async () => {
    setIsSavingProfile(true);
    setProfileMessage(null);
    try {
      const existing = selectedProfileId
        ? profiles.find((p) => p.id === selectedProfileId)
        : null;
      const defaultName = existing?.name ?? '';
      const name = window.prompt('Profile name:', defaultName);
      if (!name || !name.trim()) {
        setIsSavingProfile(false);
        return;
      }
      const config = buildConfigFromForm();
      let saved: AssemblyProfile;
      if (existing && existing.name === name.trim()) {
        saved = await updateAssemblyProfile(existing.id, { name: name.trim(), config });
      } else {
        saved = await createAssemblyProfile({ name: name.trim(), config });
      }
      await refreshProfiles();
      setSelectedProfileId(saved.id);
      setProfileMessage(`Saved "${saved.name}"`);
      setTimeout(() => setProfileMessage(null), 2500);
    } catch (err) {
      setProfileMessage(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleDeleteProfile = async () => {
    if (!selectedProfileId) return;
    const profile = profiles.find((p) => p.id === selectedProfileId);
    if (!profile) return;
    if (!window.confirm(`Delete profile "${profile.name}"?`)) return;
    try {
      await deleteAssemblyProfile(profile.id);
      await refreshProfiles();
      setSelectedProfileId(null);
      setProfileMessage(`Deleted "${profile.name}"`);
      setTimeout(() => setProfileMessage(null), 2500);
    } catch (err) {
      setProfileMessage(err instanceof Error ? err.message : 'Failed to delete profile');
    }
  };

  // When num_rounds changes, adjust round prompts array
  const numRounds = formData.num_rounds || 3;
  useEffect(() => {
    if (!settingsLoaded) return;
    setRoundPrompts((prev) => {
      if (prev.length < numRounds) {
        // Add blank entries for new rounds
        const additions = Array.from({ length: numRounds - prev.length }, () => ({
          theme: '',
          prompt: '',
        }));
        return [...prev, ...additions];
      }
      // Don't auto-remove entries if rounds decrease (let user decide)
      return prev;
    });
  }, [numRounds, settingsLoaded]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Include round prompts if any have content
      const hasRoundPrompts = roundPrompts.some((rp) => rp.theme || rp.prompt);
      const customIds = Array.from(selectedCustomIds);
      const submitData: AssemblyCreateRequest = {
        ...formData,
        round_prompts: hasRoundPrompts ? roundPrompts.slice(0, numRounds) : null,
        custom_citizen_ids: customIds.length > 0 ? customIds : null,
      };

      const assembly = await createAssembly(submitData);
      router.push(`/assemblies/${assembly.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create assembly');
      setIsSubmitting(false);
    }
  };

  const updateRoundPrompt = (index: number, field: keyof RoundPromptConfig, value: string) => {
    const updated = [...roundPrompts];
    updated[index] = { ...updated[index], [field]: value };
    setRoundPrompts(updated);
  };

  const addRoundPrompt = () => {
    setRoundPrompts([...roundPrompts, { theme: '', prompt: '' }]);
  };

  const removeRoundPrompt = (index: number) => {
    setRoundPrompts(roundPrompts.filter((_, i) => i !== index));
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

          <div className="border rounded-lg p-3 space-y-2 bg-muted/30">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Settings Profile</Label>
              {profileMessage && (
                <span className="text-xs text-muted-foreground">{profileMessage}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Select
                value={selectedProfileId ? String(selectedProfileId) : ''}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) handleLoadProfile(parseInt(v, 10));
                  else setSelectedProfileId(null);
                }}
                className="flex-1"
              >
                <option value="">
                  {profiles.length === 0 ? 'No saved profiles' : 'Load a profile…'}
                </option>
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleSaveProfile}
                disabled={isSavingProfile}
                title={selectedProfileId ? 'Save (or save as new)' : 'Save current settings as a profile'}
              >
                {isSavingProfile ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                <span className="ml-1">Save</span>
              </Button>
              {selectedProfileId && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleDeleteProfile}
                  className="text-red-500 hover:text-red-700"
                  title="Delete selected profile"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Save the current settings (prompts, sizes, preset delegates, etc.) as a reusable profile, or load one to populate the form.
            </p>
          </div>

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
                min={2}
                max={100}
                value={formData.num_citizens}
                onChange={(e) => setFormData({ ...formData, num_citizens: parseInt(e.target.value) || 40 })}
              />
              <p className="text-xs text-muted-foreground">2-100 citizens</p>
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

          {/* Collapsible Round Prompts Section */}
          <div className="border rounded-lg">
            <button
              type="button"
              className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
              onClick={() => setShowRoundPrompts(!showRoundPrompts)}
            >
              <div>
                <span className="font-medium">Round Prompts</span>
                <span className="text-xs text-muted-foreground ml-2">
                  Customize theme and focus for each round
                </span>
              </div>
              {showRoundPrompts ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {showRoundPrompts && (
              <div className="px-4 pb-4 space-y-3">
                {roundPrompts.map((rp, index) => (
                  <div key={index} className="border rounded-lg p-3 space-y-2 bg-muted/30">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-muted-foreground">
                        Round {index + 1}
                        {index >= numRounds && (
                          <span className="text-xs text-amber-600 ml-2">(extra)</span>
                        )}
                      </span>
                      {roundPrompts.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeRoundPrompt(index)}
                          className="text-red-500 hover:text-red-700 h-7 w-7 p-0"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                    <Input
                      placeholder="Theme, e.g., Initial Reactions"
                      value={rp.theme}
                      onChange={(e) => updateRoundPrompt(index, 'theme', e.target.value)}
                    />
                    <Textarea
                      placeholder="Moderator instructions for this round..."
                      value={rp.prompt}
                      onChange={(e) => updateRoundPrompt(index, 'prompt', e.target.value)}
                      rows={2}
                    />
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addRoundPrompt}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add Round Prompt
                </Button>
              </div>
            )}
          </div>

          {/* Collapsible Custom Citizens Section */}
          <div className="border rounded-lg">
            <button
              type="button"
              className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
              onClick={() => setShowCustomCitizens(!showCustomCitizens)}
            >
              <div>
                <span className="font-medium">Custom Citizens</span>
                <span className="text-xs text-muted-foreground ml-2">
                  {selectedCustomIds.size > 0
                    ? `${selectedCustomIds.size} selected of ${formData.num_citizens} total`
                    : 'Pre-seed with custom personas'}
                </span>
              </div>
              {showCustomCitizens ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {showCustomCitizens && (
              <div className="px-4 pb-4 space-y-2">
                {customCitizens.length === 0 ? (
                  <div className="py-4 text-center">
                    <User className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground mb-2">
                      No custom citizens yet
                    </p>
                    <p className="text-xs text-muted-foreground mb-3">
                      Create custom personas or save citizens from completed assemblies
                    </p>
                    <a
                      href="/citizens/custom"
                      className="inline-flex items-center text-sm text-blue-600 hover:underline"
                    >
                      <Plus className="h-3.5 w-3.5 mr-1" />
                      Create custom citizens
                    </a>
                  </div>
                ) : (
                  <>
                    {selectedCustomIds.size >= (formData.num_citizens || 40) && (
                      <div className="p-2 text-xs text-amber-700 bg-amber-50 rounded border border-amber-200">
                        Selected custom citizens equal or exceed total citizen count. No GSS citizens will be generated.
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Selected citizens will be included in the assembly. Remaining slots
                      ({Math.max(0, (formData.num_citizens || 40) - selectedCustomIds.size)}) will be
                      filled with GSS-generated citizens.
                    </p>
                    {customCitizens.map((citizen) => (
                      <label
                        key={citizen.id}
                        className="flex items-start gap-3 p-3 rounded-lg border bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selectedCustomIds.has(citizen.id)}
                          onChange={(e) => {
                            const next = new Set(selectedCustomIds);
                            if (e.target.checked) {
                              next.add(citizen.id);
                            } else {
                              next.delete(citizen.id);
                            }
                            setSelectedCustomIds(next);
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm">{citizen.name}</span>
                            {citizen.political_leaning && (
                              <Badge variant="outline" className="text-xs">
                                {citizen.political_leaning}
                              </Badge>
                            )}
                          </div>
                          {citizen.background_summary && (
                            <p className="text-xs text-muted-foreground mt-0.5 truncate">
                              {citizen.background_summary}
                            </p>
                          )}
                        </div>
                      </label>
                    ))}
                    <a
                      href="/citizens/custom"
                      className="inline-flex items-center text-xs text-blue-600 hover:underline mt-1"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Manage custom citizens
                    </a>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Collapsible Research Settings Section */}
          <div className="border rounded-lg">
            <button
              type="button"
              className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
              onClick={() => setShowResearchSettings(!showResearchSettings)}
            >
              <div>
                <span className="font-medium">Research Settings</span>
                <span className="text-xs text-muted-foreground ml-2">
                  Follow-up research between rounds
                </span>
              </div>
              {showResearchSettings ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {showResearchSettings && (
              <div className="px-4 pb-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max_research_calls">Max Research Calls per Round</Label>
                    <Input
                      id="max_research_calls"
                      type="number"
                      min={0}
                      max={10}
                      value={formData.max_research_calls_per_round}
                      onChange={(e) =>
                        setFormData({ ...formData, max_research_calls_per_round: parseInt(e.target.value) || 0 })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Set to 0 to disable
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max_research_tokens">Max Tokens per Call</Label>
                    <Input
                      id="max_research_tokens"
                      type="number"
                      min={500}
                      max={8000}
                      step={500}
                      value={formData.max_research_tokens_per_call}
                      onChange={(e) =>
                        setFormData({ ...formData, max_research_tokens_per_call: parseInt(e.target.value) || 2000 })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      500-8000 tokens
                    </p>
                  </div>
                </div>
              </div>
            )}
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
