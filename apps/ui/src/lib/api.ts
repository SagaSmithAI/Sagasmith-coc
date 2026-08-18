import type {
  Campaign,
  CampaignWorkspace,
  ConnectionMode,
  EncounterView,
  ExposureStatus,
  Investigator,
  RuntimeCapabilities,
  RuntimePhase,
} from '../types';
import { DEMO_CAMPAIGNS, demoInvestigator, demoWorkspace } from './demo';

export type CocToolId = string;

export interface GatewaySession {
  id?: string;
  campaign_id?: string;
  phase?: RuntimePhase;
  tools_revision?: number;
}

export class GatewayError extends Error {
  status: number;
  category: 'offline' | 'unauthorized' | 'forbidden' | 'conflict' | 'contract' | 'server';

  constructor(status: number, message: string) {
    super(message);
    this.name = 'GatewayError';
    this.status = status;
    this.category = status === 0 ? 'offline'
      : status === 401 ? 'unauthorized'
        : status === 403 ? 'forbidden'
          : status === 409 ? 'conflict'
            : status >= 500 ? 'server' : 'contract';
  }
}

export interface ClientConfig {
  baseUrl?: string;
  mode?: ConnectionMode;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

function publicMode(): ConnectionMode {
  if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('demo') === '1') return 'demo';
  return import.meta.env.PUBLIC_COC_UI_MODE === 'demo' ? 'demo' : 'live';
}

function extractResult<T>(body: unknown): T {
  if (!body || typeof body !== 'object') return body as T;
  const value = body as Record<string, unknown>;
  if (value.ok === false) throw new GatewayError(400, String(value.error || 'MCP gateway rejected the call'));
  let result: unknown = value.result ?? value.data ?? value;
  if (result && typeof result === 'object') {
    const structured = (result as Record<string, unknown>).structuredContent;
    if (structured !== undefined) result = structured;
  }
  return result as T;
}

export class CocGatewayClient {
  readonly baseUrl: string;
  readonly mode: ConnectionMode;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = (config.baseUrl ?? import.meta.env.PUBLIC_COC_GATEWAY_BASE ?? 'http://127.0.0.1:8768').replace(/\/$/, '');
    this.mode = config.mode ?? publicMode();
    this.fetchImpl = config.fetchImpl ?? fetch;
    this.timeoutMs = config.timeoutMs ?? 12_000;
  }

  async call<T>(tool: CocToolId, args: Record<string, unknown> = {}): Promise<T> {
    if ('principal_id' in args) throw new GatewayError(400, '浏览器不得提交 principal_id；身份必须由认证网关注入。');
    if (this.mode === 'demo') throw new GatewayError(400, '演示模式为只读，不会伪造 MCP 写入。');
    const controller = new AbortController();
    const timer = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(`${this.baseUrl}/api/coc/mcp/tool`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ tool, arguments: args }),
        signal: controller.signal,
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = String((body as Record<string, unknown>).error || `${response.status} ${response.statusText}`);
        throw new GatewayError(response.status, message);
      }
      return extractResult<T>(body);
    } catch (error) {
      if (error instanceof GatewayError) throw error;
      throw new GatewayError(0, error instanceof Error ? error.message : String(error));
    } finally {
      globalThis.clearTimeout(timer);
    }
  }

  async listCampaigns(): Promise<{ campaigns: Campaign[]; capabilities: RuntimeCapabilities | null }> {
    if (this.mode === 'demo') return { campaigns: DEMO_CAMPAIGNS, capabilities: null };
    const [campaignResult, capabilities] = await Promise.all([
      this.call<{ campaigns: Campaign[] }>('campaign_query', { action: 'list' }),
      this.call<RuntimeCapabilities>('server_capabilities'),
    ]);
    return { campaigns: campaignResult.campaigns, capabilities };
  }

  private async bindExposure(campaignId: string): Promise<ExposureStatus> {
    try {
      await this.call<ExposureStatus>('exposure', { action: 'open', campaign_id: campaignId });
    } catch (error) {
      if (!(error instanceof GatewayError) || !error.message.includes('already bound')) throw error;
    }
    const search = await this.call<ExposureStatus>('exposure', { action: 'search', campaign_id: campaignId, query: '' });
    const wanted = new Set([
      'branch_query', 'character_query', 'content_pack', 'investigation_query', 'module_query',
      'npc_conversation', 'rule_query', 'snapshot_query', 'state_revision', 'chase_query',
      'combat_query',
    ]);
    const unloaded = (search.matches ?? []).filter((item) => wanted.has(item.tool_id) && !item.loaded).map((item) => item.tool_id);
    if (unloaded.length) {
      return this.call<ExposureStatus>('exposure', { action: 'set', campaign_id: campaignId, add_tool_ids: unloaded });
    }
    return search;
  }

  async loadWorkspace(campaignId: string): Promise<CampaignWorkspace> {
    if (this.mode === 'demo') return demoWorkspace(campaignId);
    const exposure = await this.bindExposure(campaignId);
    const warnings: string[] = [];
    const guarded = async <T>(label: string, task: Promise<T>, fallback: T): Promise<T> => {
      try { return await task; }
      catch (error) { warnings.push(`${label}: ${error instanceof Error ? error.message : String(error)}`); return fallback; }
    };
    const [campaign, phaseResult, charactersResult, modulesResult, scenesResult, currentResult, progressResult] = await Promise.all([
      this.call<Campaign>('campaign_query', { action: 'get', campaign_id: campaignId }),
      this.call<{ phase: RuntimePhase }>('game_phase', { campaign_id: campaignId }),
      this.call<{ characters: Investigator[] }>('character_query', { action: 'list', campaign_id: campaignId }),
      this.call<{ modules: CampaignWorkspace['modules'] }>('module_query', { action: 'list', campaign_id: campaignId }),
      this.call<{ scenes: CampaignWorkspace['scenes'] }>('module_query', { action: 'index', campaign_id: campaignId }),
      this.call<{ scene: CampaignWorkspace['currentScene'] }>('module_query', { action: 'current', campaign_id: campaignId, data: { scope_id: 'party' } }),
      this.call<{ progress: CampaignWorkspace['progress'] }>('module_query', { action: 'progress', campaign_id: campaignId, data: { scope_id: 'party' } }),
    ]);
    const phase = phaseResult.phase;
    const [packResult, ruleLockResult, ruleSourcesResult, snapshotResult, branchResult, revisionResult] = await Promise.all([
      guarded('Content Pack', this.call<{ packs: CampaignWorkspace['packs']; finalized_drafts: CampaignWorkspace['finalizedDrafts']; rule_packs?: CampaignWorkspace['rulePacks'] }>('content_pack', { action: 'list', campaign_id: campaignId }), { packs: [], finalized_drafts: [], rule_packs: [] }),
      guarded('Effective rules', this.call<CampaignWorkspace['ruleLock']>('rule_query', { action: 'effective', campaign_id: campaignId }), null),
      guarded('Rule sources', this.call<{ sources: CampaignWorkspace['ruleSources'] }>('rule_query', { action: 'sources', campaign_id: campaignId }), { sources: [] }),
      guarded('Snapshots', this.call<{ snapshots: CampaignWorkspace['snapshots'] }>('snapshot_query', { action: 'list', campaign_id: campaignId }), { snapshots: [] }),
      guarded('Branches', this.call<{ branches: CampaignWorkspace['branches'] }>('branch_query', { action: 'list', campaign_id: campaignId }), { branches: [] }),
      guarded('Revision history', this.call<{ revisions: CampaignWorkspace['revisions'] }>('state_revision', { action: 'history', campaign_id: campaignId, data: { limit: 30 } }), { revisions: [] }),
    ]);
    const investigations: CampaignWorkspace['investigations'] = {};
    if (phase === 'play') {
      await Promise.all(charactersResult.characters.filter((actor) => actor.character_type === 'investigator').map(async (actor) => {
        const value = await guarded(`Investigation / ${actor.name}`, this.call<any>('investigation_query', { campaign_id: campaignId, actor_id: actor.id, view: 'pending' }), null);
        if (value) investigations[actor.id] = value;
      }));
    }
    let encounter: EncounterView | null = null;
    if (phase === 'combat') encounter = await guarded('Combat', this.call<EncounterView>('combat_query', { campaign_id: campaignId }), null);
    else if (Boolean(campaign.state?.chase && (campaign.state.chase as Record<string, unknown>).active)) encounter = await guarded('Chase', this.call<EncounterView>('chase_query', { campaign_id: campaignId }), null);
    const conversations = phase === 'play'
      ? (await guarded('NPC conversations', this.call<{ conversations: CampaignWorkspace['conversations'] }>('npc_conversation', { action: 'list', campaign_id: campaignId, data: {} }), { conversations: [] })).conversations
      : [];
    return {
      campaign, phase, characters: charactersResult.characters, modules: modulesResult.modules,
      packs: packResult.packs, finalizedDrafts: packResult.finalized_drafts,
      rulePacks: packResult.rule_packs ?? [], ruleLock: ruleLockResult,
      ruleSources: ruleSourcesResult.sources, conversations,
      scenes: scenesResult.scenes, currentScene: currentResult.scene, progress: progressResult.progress,
      snapshots: snapshotResult.snapshots, branches: branchResult.branches, revisions: revisionResult.revisions,
      investigations, encounter, exposure, warnings,
    };
  }

  async getInvestigator(campaignId: string, investigatorId: string): Promise<Investigator> {
    if (this.mode === 'demo') return demoInvestigator(campaignId, investigatorId);
    await this.bindExposure(campaignId);
    return this.call<Investigator>('character_query', { action: 'get', campaign_id: campaignId, character_id: investigatorId });
  }
}

export function createClient(config?: ClientConfig): CocGatewayClient { return new CocGatewayClient(config); }

export function emitRuntimeStatus(connected: boolean, detail: { version?: string; mode?: ConnectionMode } = {}) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('sagasmith:runtime', { detail: { connected, ...detail } }));
}
