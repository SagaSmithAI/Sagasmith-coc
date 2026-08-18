import type { Campaign, CampaignWorkspace, Investigator } from '../types';

export const DEMO_CAMPAIGNS: Campaign[] = [
  {
    id: 'demo-beacon', name: '灯塔回归线 A', slug: 'lightless-beacon-a', system_id: 'coc7e',
    edition: '7e', locale: 'zh', status: 'demo', description: '用于 UI 验收的并行战役演示数据，不代表真实模组回测已经完成。',
    settings: { ruleset: 'classic', era: '1920s' }, state: { game_phase: 'play', chase: null, combat: null }, revision: 23,
  },
  {
    id: 'demo-flames', name: '孤火回归线 B', slug: 'alone-against-flames-b', system_id: 'coc7e',
    edition: '7e', locale: 'zh', status: 'demo', description: '第二条并行战役的只读演示档案；真实回测结果需由 MCP 运行产生。',
    settings: { ruleset: 'classic', era: '1920s', solo_play: true }, state: { game_phase: 'lobby', chase: null, combat: null }, revision: 11,
  },
];

const INVESTIGATORS: Investigator[] = [
  {
    id: 'demo-ada', campaign_id: 'demo-beacon', name: '艾达·陈', character_type: 'investigator', player_name: 'Player A',
    summary: '记者，擅长图书馆使用与侦查。', revision: 7, notes: {},
    sheet: {
      occupation: '调查记者', ruleset: 'classic', characteristics: { str: 45, con: 55, siz: 50, dex: 65, app: 60, int: 75, pow: 60, edu: 80 },
      hp: 10, max_hp: 10, san: 54, san_max: 96, san_daily_loss: 3, san_daily_limit: 10,
      luck: 48, mp: 12, max_mp: 12, mov: 8, damage_bonus: '0', build: 0, dodge: 32, cthulhu_mythos: 3,
      skills: { '图书馆使用': 70, '侦查': 65, '聆听': 55, '心理学': 50, '摄影': 60 },
      weapons: [{ name: '小型左轮', skill: '手枪', damage: '1D10', range: '15码', ammunition: 6, malfunction: 100 }],
      conditions: { major_wound: false, dying: false, unconscious: false, temporary_insanity: false, indefinite_insanity: false },
      development: { checked_skills: ['侦查'] },
    },
  },
  {
    id: 'demo-owen', campaign_id: 'demo-beacon', name: '欧文·格雷', character_type: 'investigator', player_name: 'Player B',
    summary: '前海岸警卫队员，熟悉航海与急救。', revision: 5, notes: {},
    sheet: {
      occupation: '水手', ruleset: 'classic', characteristics: { str: 70, con: 65, siz: 65, dex: 55, app: 45, int: 60, pow: 55, edu: 55 },
      hp: 13, max_hp: 13, san: 50, san_max: 99, luck: 35, mp: 11, max_mp: 11, mov: 8, damage_bonus: '1D4', build: 1, dodge: 27,
      skills: { '航海': 70, '急救': 65, '攀爬': 55, '聆听': 50, '斗殴': 60 }, weapons: [], development: { checked_skills: [] },
    },
  },
  {
    id: 'demo-solo', campaign_id: 'demo-flames', name: '露丝·卡特', character_type: 'investigator', player_name: 'Solo',
    summary: '尚未开始的单人调查员。', revision: 2, notes: {},
    sheet: {
      occupation: '古董商', ruleset: 'classic', characteristics: { str: 40, con: 50, siz: 45, dex: 60, app: 65, int: 80, pow: 65, edu: 75 },
      hp: 9, max_hp: 9, san: 65, san_max: 99, luck: 62, mp: 13, max_mp: 13, mov: 8, damage_bonus: '-1', build: -1, dodge: 30,
      skills: { '估价': 70, '历史': 65, '图书馆使用': 60, '侦查': 55 }, weapons: [], development: { checked_skills: [] },
    },
  },
];

export function demoInvestigator(campaignId: string, investigatorId: string): Investigator {
  const actor = INVESTIGATORS.find((item) => item.campaign_id === campaignId && item.id === investigatorId);
  if (!actor) throw new Error('演示调查员不存在');
  return actor;
}

export function demoWorkspace(campaignId: string): CampaignWorkspace {
  const campaign = DEMO_CAMPAIGNS.find((item) => item.id === campaignId) ?? DEMO_CAMPAIGNS[0];
  const characters = INVESTIGATORS.filter((item) => item.campaign_id === campaign.id);
  const play = campaign.id === 'demo-beacon';
  return {
    campaign, phase: play ? 'play' : 'lobby', characters,
    modules: play ? [{ id: 'demo-module-beacon', title: 'The Lightless Beacon', source_key: 'private.demo.lightless-beacon', parser_profile: 'content-package', active: true, warnings: [] }] : [],
    packs: play ? [{ id: 'demo-module-beacon', title: 'The Lightless Beacon', parser_profile: 'content-package', active: true, status: 'active' }] : [],
    finalizedDrafts: play ? [] : [{ job_id: 'demo-draft-flames', stage: 'review', title: 'Alone Against the Flames' }],
    rulePacks: [{ pack_id: 'coc7e.rules.quick-start.private', version: '1.0.0', status: 'installed' }],
    ruleLock: { lock: [{ pack_id: 'coc7e.rules.quick-start.private', version: '1.0.0' }] },
    ruleSources: [{ source_id: 'demo-rules', title: 'CoC 7e Quick-Start Rules', source_key: 'quick-start.private' }],
    conversations: play ? [{ conversation_id: 'demo-conversation', status: 'open', conversation_revision: 2, pending_activation_count: 1, participants: [{ name: '港务长' }, { name: '艾达·莫里斯' }] }] : [],
    scenes: play ? [
      { scene_id: 'demo-scene-landing', stable_key: 'landing', title: '无光海岸', module: 'The Lightless Beacon', chapter: '抵达', scene_type: 'investigation', visibility: 'group', page_start: 7, page_end: 9, tags: ['clue', 'storm'], profile_data: { clues: [{ title: '被冲上岸的残骸' }], checks: [{ skill: '侦查', difficulty: 'regular' }], sanity: [] } },
      { scene_id: 'demo-scene-lighthouse', stable_key: 'lighthouse', title: '灯塔内部', module: 'The Lightless Beacon', chapter: '调查', scene_type: 'investigation', visibility: 'restricted', page_start: 10, page_end: 16, tags: ['clue', 'danger'], profile_data: { clues: [{ title: '损坏的无线电' }, { title: '守塔人的记录' }], checks: [{ skill: '电气维修' }], sanity: [{ success_loss: '0', failure_loss: '1D4' }] } },
    ] : [],
    currentScene: play ? { scene_id: 'demo-scene-landing', stable_key: 'landing', title: '无光海岸', module: 'The Lightless Beacon', chapter: '抵达', scene_type: 'investigation', visibility: 'group', page_start: 7, page_end: 9, tags: ['clue', 'storm'], profile_data: { clues: [{ title: '被冲上岸的残骸' }], checks: [], sanity: [] }, content: '暴风雨后的海岸。此文本仅用于 UI 演示。' } : null,
    progress: play ? [{ scene_id: 'demo-scene-landing', scope_id: 'party', status: 'current', progress: 35, current_location_key: 'shore', state_version: 4, state: { discovered_clues: ['残骸'] } }] : [],
    snapshots: play ? [{ slot: 3, label: '登陆海岸', parent_slot: 2, branch_id: 'main', created_at: '2026-08-13T20:15:00+08:00' }, { slot: 2, label: '暴风雨', parent_slot: 1, branch_id: 'main', created_at: '2026-08-13T19:40:00+08:00' }] : [{ slot: 1, label: '角色创建完成', branch_id: 'main', created_at: '2026-08-13T18:00:00+08:00' }],
    branches: [{ id: 'main', name: 'main', head_snapshot_id: play ? 'demo-snapshot-3' : 'demo-snapshot-1' }],
    revisions: play ? [{ id: 'rev-23', operation: 'coc.investigation.check.open', actor: 'demo' }, { id: 'rev-22', operation: 'module.progress', actor: 'demo' }] : [],
    investigations: play ? {
      'demo-ada': { campaign_id: campaign.id, campaign_revision: campaign.revision, actor_id: 'demo-ada', pending: { check_id: 'demo-check-1', skill_name: '侦查', threshold: 65, roll: 71, outcome: { level: 'failure' }, available_actions: ['spend_luck', 'push', 'settle', 'abort'], source: '无光海岸 / 残骸' } },
      'demo-owen': { campaign_id: campaign.id, campaign_revision: campaign.revision, actor_id: 'demo-owen', pending: null },
    } : {},
    encounter: null,
    exposure: { id: 'demo-exposure', campaign_id: campaign.id, phase: play ? 'play' : 'lobby', loaded_tools: ['module_query', 'character_query'], visible_tools: ['campaign_query', 'exposure', 'game_phase', 'module_query', 'character_query'], native_dynamic_tools: true },
    warnings: [],
  };
}
