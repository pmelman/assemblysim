'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useSettings } from '@/hooks/useSettings';
import { updateAppSettings } from '@/lib/api';
import type { RoundPromptConfig } from '@/lib/types';
import { Loader2, Save, Plus, Trash2 } from 'lucide-react';

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

export default function SettingsPage() {
  const { settings, isLoading, mutate } = useSettings();
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [numCitizens, setNumCitizens] = useState(40);
  const [numGroups, setNumGroups] = useState(5);
  const [numRounds, setNumRounds] = useState(3);
  const [samplingStrategy, setSamplingStrategy] = useState('stratified');
  const [roundPrompts, setRoundPrompts] = useState<RoundPromptConfig[]>(DEFAULT_ROUND_PROMPTS);
  const [maxResearchCalls, setMaxResearchCalls] = useState(2);
  const [maxResearchTokens, setMaxResearchTokens] = useState(2000);

  useEffect(() => {
    if (settings) {
      setNumCitizens(settings.default_num_citizens);
      setNumGroups(settings.default_num_groups);
      setNumRounds(settings.default_num_rounds);
      setSamplingStrategy(settings.default_sampling_strategy);
      setRoundPrompts(settings.default_round_prompts || DEFAULT_ROUND_PROMPTS);
      setMaxResearchCalls(settings.default_max_research_calls_per_round);
      setMaxResearchTokens(settings.default_max_research_tokens_per_call);
    }
  }, [settings]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaved(false);

    try {
      await updateAppSettings({
        default_num_citizens: numCitizens,
        default_num_groups: numGroups,
        default_num_rounds: numRounds,
        default_sampling_strategy: samplingStrategy,
        default_round_prompts: roundPrompts,
        default_max_research_calls_per_round: maxResearchCalls,
        default_max_research_tokens_per_call: maxResearchTokens,
      });
      mutate();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
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

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-8 flex justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure default values for new assemblies
        </p>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      )}

      {saved && (
        <div className="p-3 text-sm text-green-600 bg-green-50 rounded-md border border-green-200">
          Settings saved successfully
        </div>
      )}

      {/* Assembly Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Assembly Defaults</CardTitle>
          <CardDescription>
            Default parameters for new assemblies
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="default_num_citizens">Number of Citizens</Label>
              <Input
                id="default_num_citizens"
                type="number"
                min={8}
                max={100}
                value={numCitizens}
                onChange={(e) => setNumCitizens(parseInt(e.target.value) || 40)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default_num_groups">Number of Groups</Label>
              <Input
                id="default_num_groups"
                type="number"
                min={1}
                max={10}
                value={numGroups}
                onChange={(e) => setNumGroups(parseInt(e.target.value) || 5)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default_num_rounds">Deliberation Rounds</Label>
              <Input
                id="default_num_rounds"
                type="number"
                min={1}
                max={10}
                value={numRounds}
                onChange={(e) => setNumRounds(parseInt(e.target.value) || 3)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default_sampling_strategy">Sampling Strategy</Label>
              <Select
                id="default_sampling_strategy"
                value={samplingStrategy}
                onChange={(e) => setSamplingStrategy(e.target.value)}
              >
                <option value="stratified">Stratified</option>
                <option value="quota">Quota</option>
                <option value="random">Random</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Round Prompt Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Default Round Prompts</CardTitle>
          <CardDescription>
            Default theme and moderator instructions for each round
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {roundPrompts.map((rp, index) => (
            <div key={index} className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">
                  Round {index + 1}
                </span>
                {roundPrompts.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeRoundPrompt(index)}
                    className="text-red-500 hover:text-red-700 h-8 w-8 p-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`theme-${index}`}>Theme</Label>
                <Input
                  id={`theme-${index}`}
                  placeholder="e.g., Initial Reactions"
                  value={rp.theme}
                  onChange={(e) => updateRoundPrompt(index, 'theme', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`prompt-${index}`}>Moderator Instructions</Label>
                <Textarea
                  id={`prompt-${index}`}
                  placeholder="Instructions for the moderator to guide this round..."
                  value={rp.prompt}
                  onChange={(e) => updateRoundPrompt(index, 'prompt', e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addRoundPrompt}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Round Prompt
          </Button>
        </CardContent>
      </Card>

      {/* Research Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Research Defaults</CardTitle>
          <CardDescription>
            Configure follow-up research between deliberation rounds
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_research_calls">Max Research Calls per Round</Label>
              <Input
                id="max_research_calls"
                type="number"
                min={0}
                max={10}
                value={maxResearchCalls}
                onChange={(e) => setMaxResearchCalls(parseInt(e.target.value) || 0)}
              />
              <p className="text-xs text-muted-foreground">
                Set to 0 to disable follow-up research
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
                value={maxResearchTokens}
                onChange={(e) => setMaxResearchTokens(parseInt(e.target.value) || 2000)}
              />
              <p className="text-xs text-muted-foreground">
                500-8000 tokens
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              Save Settings
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
