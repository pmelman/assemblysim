/**
 * API Client for Silicon Citizens' Assembly
 */

import type {
  AssemblyCreateRequest,
  AssemblyResponse,
  AssemblyDetailResponse,
  AssemblyListResponse,
  BriefingGenerateRequest,
  BriefingBookResponse,
  CitizenResponse,
  CitizenDetailResponse,
  MessageResponse,
  ReportResponse,
  GroupResponse,
  RoundResearchResponse,
  AppSettings,
  AppSettingsUpdateRequest,
  ErrorResponse,
  CustomCitizenTemplate,
  CustomCitizenCreateRequest,
  CustomCitizenUpdateRequest,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ErrorResponse | null = null;
    try {
      errorData = await response.json();
    } catch {
      // Response body is not JSON
    }
    throw new ApiError(
      errorData?.error || `HTTP error ${response.status}`,
      response.status,
      errorData?.detail
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// =============================================================================
// ASSEMBLY ENDPOINTS
// =============================================================================

export async function createAssembly(
  request: AssemblyCreateRequest
): Promise<AssemblyResponse> {
  const response = await fetch(`${API_BASE_URL}/assemblies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<AssemblyResponse>(response);
}

export async function listAssemblies(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<AssemblyListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) {
    params.append('status', status);
  }
  const response = await fetch(`${API_BASE_URL}/assemblies?${params}`);
  return handleResponse<AssemblyListResponse>(response);
}

export async function getAssembly(id: number): Promise<AssemblyDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/assemblies/${id}`);
  return handleResponse<AssemblyDetailResponse>(response);
}

export async function deleteAssembly(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/assemblies/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<void>(response);
}

// =============================================================================
// CITIZEN ENDPOINTS
// =============================================================================

export async function generateCitizens(
  assemblyId: number
): Promise<{ message: string; assembly_id: number; num_citizens: number; num_groups: number }> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/citizens`,
    { method: 'POST' }
  );
  return handleResponse<{ message: string; assembly_id: number; num_citizens: number; num_groups: number }>(response);
}

export async function listCitizens(
  assemblyId: number,
  groupId?: number
): Promise<CitizenResponse[]> {
  const params = new URLSearchParams();
  if (groupId !== undefined) {
    params.append('group_id', String(groupId));
  }
  const query = params.toString() ? `?${params}` : '';
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/citizens${query}`
  );
  return handleResponse<CitizenResponse[]>(response);
}

export async function getCitizen(
  assemblyId: number,
  citizenId: number
): Promise<CitizenDetailResponse> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/citizens/${citizenId}`
  );
  return handleResponse<CitizenDetailResponse>(response);
}

// =============================================================================
// BRIEFING ENDPOINTS
// =============================================================================

export async function generateBriefing(
  assemblyId: number,
  request: BriefingGenerateRequest = {}
): Promise<BriefingBookResponse> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/briefing`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    }
  );
  return handleResponse<BriefingBookResponse>(response);
}

export async function getBriefing(
  assemblyId: number
): Promise<BriefingBookResponse> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/briefing`
  );
  return handleResponse<BriefingBookResponse>(response);
}

export async function deleteBriefing(assemblyId: number): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/briefing`,
    { method: 'DELETE' }
  );
  return handleResponse<void>(response);
}

// =============================================================================
// DELIBERATION ENDPOINTS
// =============================================================================

export async function startDeliberation(
  assemblyId: number
): Promise<{ message: string; assembly_id: number; status: string; citizens: number }> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/start`,
    { method: 'POST' }
  );
  return handleResponse<{ message: string; assembly_id: number; status: string; citizens: number }>(response);
}

export async function listMessages(
  assemblyId: number,
  options: {
    groupId?: number;
    phase?: string;
    roundNumber?: number;
    limit?: number;
    offset?: number;
  } = {}
): Promise<MessageResponse[]> {
  const params = new URLSearchParams();
  if (options.groupId !== undefined) {
    params.append('group_id', String(options.groupId));
  }
  if (options.phase) {
    params.append('phase', options.phase);
  }
  if (options.roundNumber !== undefined) {
    params.append('round_number', String(options.roundNumber));
  }
  if (options.limit !== undefined) {
    params.append('limit', String(options.limit));
  }
  if (options.offset !== undefined) {
    params.append('offset', String(options.offset));
  }
  const query = params.toString() ? `?${params}` : '';
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/messages${query}`
  );
  return handleResponse<MessageResponse[]>(response);
}

// =============================================================================
// GROUP ENDPOINTS
// =============================================================================

export async function listGroups(assemblyId: number): Promise<GroupResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/groups`
  );
  return handleResponse<GroupResponse[]>(response);
}

// =============================================================================
// REPORT ENDPOINTS
// =============================================================================

export async function getReport(assemblyId: number): Promise<ReportResponse> {
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/report`
  );
  return handleResponse<ReportResponse>(response);
}

// =============================================================================
// SETTINGS ENDPOINTS
// =============================================================================

export async function getAppSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/settings`);
  return handleResponse<AppSettings>(response);
}

export async function updateAppSettings(
  request: AppSettingsUpdateRequest
): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<AppSettings>(response);
}

// =============================================================================
// RESEARCH ENDPOINTS
// =============================================================================

export async function listResearch(
  assemblyId: number,
  roundNumber?: number
): Promise<RoundResearchResponse[]> {
  const params = new URLSearchParams();
  if (roundNumber !== undefined) {
    params.append('round_number', String(roundNumber));
  }
  const query = params.toString() ? `?${params}` : '';
  const response = await fetch(
    `${API_BASE_URL}/assemblies/${assemblyId}/research${query}`
  );
  return handleResponse<RoundResearchResponse[]>(response);
}

// =============================================================================
// CUSTOM CITIZEN ENDPOINTS
// =============================================================================

export async function createCustomCitizen(
  request: CustomCitizenCreateRequest
): Promise<CustomCitizenTemplate> {
  const response = await fetch(`${API_BASE_URL}/custom-citizens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<CustomCitizenTemplate>(response);
}

export async function listCustomCitizens(): Promise<CustomCitizenTemplate[]> {
  const response = await fetch(`${API_BASE_URL}/custom-citizens`);
  return handleResponse<CustomCitizenTemplate[]>(response);
}

export async function getCustomCitizen(id: number): Promise<CustomCitizenTemplate> {
  const response = await fetch(`${API_BASE_URL}/custom-citizens/${id}`);
  return handleResponse<CustomCitizenTemplate>(response);
}

export async function updateCustomCitizen(
  id: number,
  request: CustomCitizenUpdateRequest
): Promise<CustomCitizenTemplate> {
  const response = await fetch(`${API_BASE_URL}/custom-citizens/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<CustomCitizenTemplate>(response);
}

export async function deleteCustomCitizen(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/custom-citizens/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<void>(response);
}

// =============================================================================
// EXPORTS
// =============================================================================

export { ApiError };
