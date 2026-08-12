export type RuntimePhase = 'lobby' | 'play' | 'combat';
export type ConnectionMode = 'live' | 'demo';

export interface Campaign {
  id: string;
  name: string;
  slug?: string;
  system_id: 'coc7e' | string;
  edition?: string;
  locale?: string;
  status?: string;
  description?: string;
  settings: Record<string, unknown>;
  state: Record<string, unknown>;
  revision: number;
}

export interface Investigator {
  id: string;
  campaign_id?: string;
  name: string;
  character_type: 'investigator' | 'npc' | 'creature' | string;
  player_name?: string;
  summary?: string;
  sheet?: CocSheet;
  notes?: Record<string, unknown>;
  revision: number;
}

export interface CocSheet {
  occupation?: string;
  archetype?: string;
  ruleset?: 'classic' | 'pulp' | string;
  characteristics: Partial<Record<Characteristic, number>>;
  hp: number;
  max_hp: number;
  san: number;
  san_max: number;
  san_daily_loss?: number;
  san_daily_limit?: number;
  luck: number;
  mp: number;
  max_mp: number;
  mov: number;
  damage_bonus: string;
  build: number;
  dodge: number;
  cthulhu_mythos?: number;
  skills: Record<string, number>;
  weapons?: CocWeapon[];
  conditions?: Record<string, boolean>;
  development?: { checked_skills?: string[]; [key: string]: unknown };
  biography?: unknown[];
  sanity_loss_events?: unknown[];
  inventory?: unknown[];
  books?: unknown[];
  spells?: unknown[];
  monetary?: Record<string, unknown>;
  backstory?: Record<string, unknown>;
  [key: string]: unknown;
}

export type Characteristic = 'str' | 'con' | 'siz' | 'dex' | 'app' | 'int' | 'pow' | 'edu';

export interface CocWeapon {
  name: string;
  skill?: string;
  damage?: string;
  range?: string;
  attacks?: number;
  ammunition?: number;
  malfunction?: number;
  [key: string]: unknown;
}

export interface ModuleRecord {
  id?: string;
  module_id?: string;
  title?: string;
  source_key?: string;
  parser_profile?: string;
  active?: boolean;
  status?: string;
  warnings?: unknown[];
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SceneRecord {
  scene_id: string;
  stable_key?: string;
  title: string;
  module?: string;
  module_id?: string;
  chapter?: string;
  scene_type?: string;
  visibility?: string;
  page_start?: number;
  page_end?: number;
  profile_data?: {
    clues?: unknown[];
    checks?: unknown[];
    sanity?: unknown[];
    [key: string]: unknown;
  };
  tags?: string[];
  headings?: string[];
  content?: string;
  [key: string]: unknown;
}

export interface SceneProgress {
  scene_id: string;
  scope_id: string;
  status: string;
  progress?: number;
  percent?: number;
  current_location_key?: string;
  current_room?: string;
  state_version?: number;
  state?: Record<string, unknown>;
}

export interface SnapshotRecord {
  id?: string;
  slot: number;
  label?: string;
  parent_slot?: number;
  branch_id?: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface BranchRecord {
  id: string;
  name?: string;
  head_snapshot_id?: string;
  head_revision_id?: string;
  [key: string]: unknown;
}

export interface ExposureStatus {
  id?: string;
  campaign_id?: string;
  phase?: RuntimePhase;
  loaded_tools?: string[];
  visible_tools?: string[];
  available_tools?: string[];
  native_dynamic_tools?: boolean;
  matches?: Array<{ tool_id: string; description?: string; loaded?: boolean; roles?: string[] }>;
  [key: string]: unknown;
}

export interface InvestigationState {
  campaign_id: string;
  campaign_revision: number;
  actor_id: string;
  pending?: Record<string, unknown> | null;
  history?: Array<Record<string, unknown>>;
}

export interface EncounterView {
  campaign_id: string;
  campaign_revision: number;
  phase: RuntimePhase;
  available_actions: string[];
  combat?: Record<string, unknown>;
  chase?: Record<string, unknown>;
}

export interface RuntimeCapabilities {
  server: string;
  version: string;
  system: string;
  phases: string[];
  native_dynamic_tools_required: boolean;
  content_pack?: Record<string, unknown>;
  tool_catalog?: unknown;
  [key: string]: unknown;
}

export interface CampaignWorkspace {
  campaign: Campaign;
  phase: RuntimePhase;
  characters: Investigator[];
  modules: ModuleRecord[];
  packs: ModuleRecord[];
  finalizedDrafts: Array<Record<string, unknown>>;
  rulePacks: Array<Record<string, unknown>>;
  ruleLock: Record<string, unknown> | null;
  ruleSources: Array<Record<string, unknown>>;
  conversations: Array<Record<string, unknown>>;
  scenes: SceneRecord[];
  currentScene: SceneRecord | null;
  progress: SceneProgress[];
  snapshots: SnapshotRecord[];
  branches: BranchRecord[];
  revisions: Array<Record<string, unknown>>;
  investigations: Record<string, InvestigationState>;
  encounter: EncounterView | null;
  exposure: ExposureStatus | null;
  warnings: string[];
}

export const CHARACTERISTIC_LABELS: Record<Characteristic, string> = {
  str: '力量', con: '体质', siz: '体型', dex: '敏捷',
  app: '外貌', int: '智力', pow: '意志', edu: '教育',
};
