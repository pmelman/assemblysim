'use client';

import { useEffect, useState } from 'react';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { listAvailableModels } from '@/lib/api';
import type { ModelOption } from '@/lib/types';

const CUSTOM_OPTION = '__custom__';
const INHERIT_OPTION = '__inherit__';

interface ModelSelectorProps {
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  /** When true, adds an "(inherit default)" option that maps to null. */
  allowInherit?: boolean;
  /** Label shown on the inherit option. */
  inheritLabel?: string;
  id?: string;
  disabled?: boolean;
}

export function ModelSelector({
  value,
  onChange,
  allowInherit = false,
  inheritLabel = 'Inherit default',
  id,
  disabled,
}: ModelSelectorProps) {
  const [options, setOptions] = useState<ModelOption[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listAvailableModels()
      .then((res) => {
        if (cancelled) return;
        setOptions(res.models);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const knownIds = new Set(options.map((m) => m.id));
  const isInherit = allowInherit && (value === null || value === undefined || value === '');
  const isCustom = !isInherit && !!value && loaded && !knownIds.has(value);

  const selectValue = isInherit
    ? INHERIT_OPTION
    : isCustom
      ? CUSTOM_OPTION
      : value || (allowInherit ? INHERIT_OPTION : '');

  const handleSelectChange = (next: string) => {
    if (next === INHERIT_OPTION) {
      onChange(null);
    } else if (next === CUSTOM_OPTION) {
      onChange('');
    } else {
      onChange(next);
    }
  };

  return (
    <div className="space-y-2">
      <Select
        id={id}
        value={selectValue}
        onChange={(e) => handleSelectChange(e.target.value)}
        disabled={disabled}
      >
        {allowInherit && <option value={INHERIT_OPTION}>{inheritLabel}</option>}
        {options.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label} ({m.id})
          </option>
        ))}
        <option value={CUSTOM_OPTION}>Custom OpenRouter model ID…</option>
      </Select>
      {isCustom && (
        <Input
          placeholder="provider/model-name (e.g. mistralai/mistral-large)"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      )}
    </div>
  );
}
