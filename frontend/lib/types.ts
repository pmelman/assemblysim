/**
 * TypeScript interfaces for Silicon Citizens' Assembly
 * Derived from backend Pydantic schemas
 */

// =============================================================================
// ENUMS
// =============================================================================

export type AssemblyStatus =
  | 'pending'
  | 'generating_citizens'
  | 'citizens_ready'
  | 'generating_briefing'
  | 'ready'
  | 'deliberating'
  | 'voting'
  | 'completed'
  | 'failed';

export type MessageRole = 'moderator' | 'citizen' | 'recorder' | 'system';

export type VoteValue = 'support' | 'oppose' | 'abstain';

export type FactCheckStatus = 'verified' | 'disputed' | 'unchecked';

// =============================================================================
// AUTH TYPES
// =============================================================================

export interface User {
  id: number;
  email: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
  invite_code: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface InviteCodeResponse {
  id: number;
  code: string;
  created_at: string;
  used_at: string | null;
  used_by_username: string | null;
}

// =============================================================================
// REQUEST TYPES
// =============================================================================

export interface RoundPromptConfig {
  theme: string;
  prompt: string;
}

export interface AssemblyCreateRequest {
  topic: string;
  num_citizens?: number;
  num_groups?: number;
  num_rounds?: number;
  sampling_strategy?: 'stratified' | 'quota' | 'random';
  round_prompts?: RoundPromptConfig[] | null;
  max_research_calls_per_round?: number;
  max_research_tokens_per_call?: number;
  custom_citizen_ids?: number[] | null;
}

export interface BriefingGenerateRequest {
  depth?: 'quick' | 'standard' | 'detailed';
}

// =============================================================================
// RESPONSE TYPES
// =============================================================================

export interface CitizenResponse {
  id: number;
  name: string;
  background_summary: string | null;
  key_values: string[] | null;
  demographic_tags: string[] | null;
  group_id: number | null;
  final_vote: VoteValue | null;
  vote_reasoning: string | null;
  created_at: string;
}

export interface CitizenDetailResponse extends CitizenResponse {
  system_prompt: string;
  gss_data: Record<string, unknown> | null;
}

export interface BriefingBookResponse {
  id: number;
  assembly_id: number;
  topic_query: string;
  content_markdown: string;
  sections: BriefingSections | null;
  sources: BriefingSource[] | null;
  generated_at: string;
}

// Briefing sections can have any structure depending on the Perplexity prompt config
export type BriefingSections = Record<string, unknown>;

export interface BriefingSource {
  title: string;
  url: string;
  snippet?: string;
}

export interface MessageResponse {
  id: number;
  assembly_id: number;
  group_id: number | null;
  citizen_id: number | null;
  citizen_name: string | null;
  phase: string;
  round_number: number | null;
  role: MessageRole;
  content: string;
  citations: Citation[] | null;
  fact_check_status: FactCheckStatus | null;
  created_at: string;
}

export interface Citation {
  text: string;
  source: string;
  url?: string;
}

export interface GroupResponse {
  id: number;
  name: string;
  round_summaries: string[] | null;
  consensus_summary: string | null;
  disagreements_summary: string | null;
  citizen_count: number;
  created_at: string;
}

export interface ProposalScore {
  title: string;
  description: string;
  avg_score: number;
  num_votes?: number;
  passed: boolean;
}

export interface ReportResponse {
  id: number;
  assembly_id: number;
  executive_summary: string | null;
  recommendations: Recommendation[] | null;
  vote_tally: Record<string, number> | null;
  proposal_scores: ProposalScore[] | null;
  minority_report: string | null;
  key_themes: string[] | null;
  generated_at: string;
}

export interface Recommendation {
  title: string;
  description: string;
  avg_score?: number;
  support_level?: 'strong' | 'moderate' | 'weak';
}

export interface VoteTally {
  support: number;
  oppose: number;
  abstain: number;
  total: number;
}

export interface RoundResearchResponse {
  id: number;
  assembly_id: number;
  round_number: number;
  queries: string[];
  results: Array<{ query: string; content: string; sources: Array<{ title: string; url: string }> }>;
  summary_markdown: string;
  created_at: string;
}

export interface AssemblyResponse {
  id: number;
  topic: string;
  status: AssemblyStatus;
  num_citizens: number;
  num_groups: number;
  num_rounds: number;
  sampling_strategy: string;
  round_prompts: RoundPromptConfig[] | null;
  max_research_calls_per_round: number;
  max_research_tokens_per_call: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AssemblyDetailResponse extends AssemblyResponse {
  citizens: CitizenResponse[];
  groups: GroupResponse[];
  briefing_book: BriefingBookResponse | null;
  report: ReportResponse | null;
  round_research: RoundResearchResponse[];
}

export interface AssemblyListResponse {
  assemblies: AssemblyResponse[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// WEBSOCKET TYPES
// =============================================================================

export interface WSMessage {
  type: WSMessageType;
  assembly_id: number;
  data?: Record<string, unknown>;
  message?: string;
  timestamp: string;
}

export type WSMessageType =
  | 'connected'
  | 'status_update'
  | 'new_message'
  | 'vote_update'
  | 'error'
  | 'pong'
  | 'subscribed'
  | 'status'
  | 'research_complete';

export interface AppSettings {
  id: number;
  default_num_citizens: number;
  default_num_groups: number;
  default_num_rounds: number;
  default_sampling_strategy: string;
  default_round_prompts: RoundPromptConfig[] | null;
  default_max_research_calls_per_round: number;
  default_max_research_tokens_per_call: number;
  updated_at: string | null;
}

export interface AppSettingsUpdateRequest {
  default_num_citizens?: number;
  default_num_groups?: number;
  default_num_rounds?: number;
  default_sampling_strategy?: string;
  default_round_prompts?: RoundPromptConfig[] | null;
  default_max_research_calls_per_round?: number;
  default_max_research_tokens_per_call?: number;
}

export interface WSStatusUpdate {
  status: AssemblyStatus;
  progress?: number;
  total?: number;
  message?: string;
}

export interface WSNewMessage {
  message_id: number;
  role: MessageRole;
  content: string;
  citizen_id?: number;
  citizen_name?: string;
  round_number?: number;
  phase?: string;
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  status_code: number;
}

// =============================================================================
// CUSTOM CITIZEN TYPES
// =============================================================================

export interface CustomCitizenTemplate {
  id: number;
  name: string;
  mode: 'traits' | 'full';
  background_summary: string | null;
  key_values: string[] | null;
  demographic_tags: string[] | null;
  political_leaning: string | null;
  system_prompt: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomCitizenCreateRequest {
  name: string;
  mode: 'traits' | 'full';
  background_summary?: string | null;
  key_values?: string[] | null;
  demographic_tags?: string[] | null;
  political_leaning?: string | null;
  system_prompt?: string | null;
}

export interface CustomCitizenUpdateRequest {
  name?: string;
  mode?: 'traits' | 'full';
  background_summary?: string | null;
  key_values?: string[] | null;
  demographic_tags?: string[] | null;
  political_leaning?: string | null;
  system_prompt?: string | null;
}

// Helper type for status badge styling
export interface StatusConfig {
  label: string;
  color: string;
  pulse: boolean;
}

export const STATUS_CONFIG: Record<AssemblyStatus, StatusConfig> = {
  pending: { label: 'Pending', color: 'gray', pulse: false },
  generating_citizens: { label: 'Generating Citizens', color: 'yellow', pulse: true },
  citizens_ready: { label: 'Citizens Ready', color: 'blue', pulse: false },
  generating_briefing: { label: 'Generating Briefing', color: 'yellow', pulse: true },
  ready: { label: 'Ready', color: 'green', pulse: false },
  deliberating: { label: 'Deliberating', color: 'blue', pulse: true },
  voting: { label: 'Voting', color: 'purple', pulse: true },
  completed: { label: 'Completed', color: 'green', pulse: false },
  failed: { label: 'Failed', color: 'red', pulse: false },
};
