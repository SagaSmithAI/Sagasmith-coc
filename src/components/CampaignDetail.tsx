import { useEffect, useMemo, useState } from 'react';
import { createClient, emitRuntimeStatus, TOOL_IDS, type CocToolId } from '../lib/api';
import type { CampaignWorkspace, Investigator } from '../types';
import { RuntimeError } from './Dashboard';

type Tab = 'overview' | 'investigation' | 'content' | 'rules' | 'dialogue' | 'encounter' | 'continuity' | 'console';

function campaignIdFromLocation() { return new URLSearchParams(window.location.search).get('id') || ''; }
function asRecord(value: unknown): Record<string, unknown> { return value && typeof value === 'object' ? value as Record<string, unknown> : {}; }
function arrayLength(value: unknown): number { return Array.isArray(value) ? value.length : 0; }

export default function CampaignDetail() {
  const client = useMemo(() => createClient(), []);
  const [workspace, setWorkspace] = useState<CampaignWorkspace | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const campaignId = typeof window === 'undefined' ? '' : campaignIdFromLocation();
  const load = () => {
    setLoading(true); setError('');
    client.loadWorkspace(campaignId).then((value) => { setWorkspace(value); emitRuntimeStatus(true, { mode: client.mode }); })
      .catch((reason) => { setError(reason instanceof Error ? reason.message : String(reason)); emitRuntimeStatus(false, { mode: client.mode }); })
      .finally(() => setLoading(false));
  };
  useEffect(load, [campaignId, client]);

  if (loading) return <div className="page"><div className="empty card">正在建立 campaign-scoped MCP exposure……</div></div>;
  if (error || !workspace) return <div className="page"><RuntimeError message={error} /></div>;
  const { campaign, phase } = workspace;
  const selectTab = (next: Tab) => { setTab(next); const query = new URLSearchParams(location.search); query.set('tab', next); history.replaceState({}, '', `${location.pathname}?${query}`); };

  return <div className="page">
    <div className="page-heading campaign-heading">
      <div><div className="eyebrow">CASE FILE / {campaign.slug || campaign.id}</div><h1>{campaign.name}</h1><p>{campaign.description || '暂无调查摘要。'}</p></div>
      <div className="heading-actions"><button className="btn btn-ghost" onClick={load}>刷新修订</button><a className="btn btn-ghost" href={client.mode === 'demo' ? '/campaigns?demo=1' : '/campaigns'}>全部档案</a></div>
    </div>
    {client.mode === 'demo' && <div className="demo-notice"><strong>READ-ONLY DEMO</strong><span>所有操作按钮与 MCP 控制台均不会写入；这不是权威战役状态。</span></div>}
    <section className="campaign-banner">
      <Datum label="PHASE" value={phase.toUpperCase()} accent />
      <Datum label="CAMPAIGN REVISION" value={campaign.revision} />
      <Datum label="RULESET" value={String(campaign.settings?.ruleset || 'classic').toUpperCase()} />
      <Datum label="PACKS / SCENES" value={`${workspace.packs.length + workspace.rulePacks.length} / ${workspace.scenes.length}`} />
      <Datum label="EXPOSURE" value={workspace.exposure?.native_dynamic_tools === false ? 'NON-NATIVE' : 'NATIVE'} />
    </section>
    {workspace.warnings.length > 0 && <details className="warning-strip"><summary>{workspace.warnings.length} 个受权限或 phase 限制的读取未完成</summary>{workspace.warnings.map((item) => <p key={item}>{item}</p>)}</details>}
    <nav className="tabs" aria-label="Campaign workspaces">{([
      ['overview', '桌面概览'], ['investigation', '调查结算'], ['content', '模组包'], ['rules', '规则包'], ['dialogue', 'NPC 对话'], ['encounter', '追逐与战斗'], ['continuity', '连续性'], ['console', 'MCP 控制台'],
    ] as Array<[Tab, string]>).map(([id, label]) => <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => selectTab(id)}>{label}</button>)}</nav>
    <div className="tab-panel">
      {tab === 'overview' && <Overview data={workspace} demo={client.mode === 'demo'} />}
      {tab === 'investigation' && <Investigation data={workspace} />}
      {tab === 'content' && <Content data={workspace} />}
      {tab === 'rules' && <Rules data={workspace} />}
      {tab === 'dialogue' && <Dialogue data={workspace} />}
      {tab === 'encounter' && <Encounter data={workspace} />}
      {tab === 'continuity' && <Continuity data={workspace} />}
      {tab === 'console' && <ToolConsole client={client} campaignId={campaign.id} disabled={client.mode === 'demo'} onMutated={load} />}
    </div>
  </div>;
}

function Datum({ label, value, accent = false }: { label: string; value: unknown; accent?: boolean }) { return <div><span>{label}</span><strong className={accent ? 'accent-text' : ''}>{String(value)}</strong></div>; }

function Overview({ data, demo }: { data: CampaignWorkspace; demo: boolean }) {
  const scene = data.currentScene;
  const progress = data.progress.find((item) => item.scene_id === scene?.scene_id);
  const percent = Number(progress?.progress ?? progress?.percent ?? 0);
  return <div className="grid-2">
    <section className="card"><div className="card-header"><strong>VISIBLE ACTORS</strong><span>{data.characters.length}</span></div><ActorList actors={data.characters} campaignId={data.campaign.id} demo={demo} /></section>
    <section className="card current-scene"><div className="card-header"><strong>CURRENT SCENE</strong><span>{scene?.visibility || 'UNSET'}</span></div>
      {scene ? <><small>{scene.chapter || scene.module || 'SCENE'}</small><h3>{scene.title}</h3><p>{scene.content || '场景正文由当前身份与可见性决定。'}</p><div className="progress-bar"><i style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} /></div><footer><span>{progress?.current_location_key || progress?.current_room || 'LOCATION UNSET'}</span><b>{percent}%</b></footer></> : <div className="empty">尚未设置当前场景。</div>}
    </section>
    <section className="card"><div className="card-header"><strong>INVESTIGATION SIGNALS</strong><span>AGENT-DECIDED MEANING</span></div><div className="signal-grid">
      <Datum label="PENDING CHECKS" value={Object.values(data.investigations).filter((item) => item.pending).length} />
      <Datum label="SCENE CLUES" value={arrayLength(scene?.clues)} />
      <Datum label="SAN ENCOUNTERS" value={arrayLength(scene?.sanity)} />
      <Datum label="HANDOUT / TAGS" value={arrayLength(scene?.tags)} />
    </div></section>
    <section className="card"><div className="card-header"><strong>RUNTIME BOUNDARIES</strong><span>AUTHORITATIVE</span></div><ul className="boundary-list"><li><b>随机与结算</b><span>MCP 原子提交并返回 receipt</span></li><li><b>来源解释与受众</b><span>Agent 显式决定</span></li><li><b>NPC 私有意图</b><span>隔离 worker；只发布派生输出</span></li><li><b>版本与恢复</b><span>revision + branch + snapshot 守卫</span></li></ul></section>
  </div>;
}

function ActorList({ actors, campaignId, demo }: { actors: Investigator[]; campaignId: string; demo: boolean }) {
  if (!actors.length) return <div className="empty">当前身份看不到任何角色。</div>;
  return <div className="actor-list">{actors.map((actor) => {
    const sheet = actor.sheet; const query = new URLSearchParams({ campaign: campaignId }); if (demo) query.set('demo', '1');
    query.set('id', actor.id);
    return <a key={actor.id} href={`/characters/detail?${query}`}><div className="actor-monogram">{actor.name.slice(0, 1)}</div><div><b>{actor.name}</b><span>{actor.character_type.toUpperCase()} · {sheet?.occupation || 'PRIVATE SHEET'} · REV {actor.revision}</span></div>{sheet && <div className="actor-vitals"><span>HP {sheet.hp}/{sheet.max_hp}</span><span>SAN {sheet.san}</span><span>LUCK {sheet.luck}</span></div>}</a>;
  })}</div>;
}

function Investigation({ data }: { data: CampaignWorkspace }) {
  const pending = Object.entries(data.investigations).filter(([, value]) => value.pending);
  return <div className="investigation-layout"><section className="card"><div className="card-header"><strong>PENDING HUMAN CHOICES</strong><span>{pending.length}</span></div>
    {data.phase !== 'play' && <div className="empty">调查检定只在 Play phase 开放。Lobby 用于内容与角色准备；Combat 使用战斗工具。</div>}
    {data.phase === 'play' && !pending.length && <div className="empty">没有待处理检定。新检定由 `investigation_check(open)` 建立。</div>}
    {pending.map(([actorId, state]) => { const actor = data.characters.find((item) => item.id === actorId); const check = asRecord(state.pending); const outcome = asRecord(check.outcome); const actions = Array.isArray(check.available_actions) ? check.available_actions : [];
      return <article className="pending-check" key={actorId}><header><div><span>{actor?.name || actorId}</span><h3>{String(check.skill_name || check.skill || '未命名检定')}</h3></div><strong>{String(outcome.level || check.result || 'PENDING').toUpperCase()}</strong></header><div className="check-numbers"><Datum label="TARGET" value={check.threshold ?? '—'} /><Datum label="ROLL" value={asRecord(check.roll).total ?? check.roll ?? '—'} /><Datum label="REVISION" value={state.campaign_revision} /></div><p>{String(check.source || '来源必须随检定显式记录。')}</p><footer>{actions.map((action) => <span key={String(action)}>{String(action)}</span>)}</footer></article>;
    })}
  </section><aside className="card procedure-card"><div className="card-header"><strong>SETTLEMENT PROCEDURE</strong><span>NO HEURISTICS</span></div><ol><li><b>Open</b><span>记录来源、技能、难度和意图。</span></li><li><b>Choose</b><span>玩家决定花幸运、孤注一掷或接受结果。</span></li><li><b>Settle</b><span>MCP 原子写入随机流、角色与战役修订。</span></li><li><b>Commit continuity</b><span>Agent 决定线索、受众、知识与叙事后果。</span></li></ol><p className="hint">所有可写操作可在“MCP 控制台”以当前原生 schema 提交；演示模式禁用。</p></aside></div>;
}

function Content({ data }: { data: CampaignWorkspace }) {
  return <div className="grid-2"><section className="card span-2"><div className="card-header"><strong>MODULE PACK PIPELINE</strong><span>SCHEMA V2 / COC7E PROFILE</span></div><div className="pipeline"><div className="done"><b>01</b><span>机械首轮导入</span></div><div className={data.finalizedDrafts.length ? 'active' : ''}><b>02</b><span>Agent 证据审计</span></div><div className={data.packs.length ? 'done' : ''}><b>03</b><span>显式定稿</span></div><div className={data.packs.some((item) => item.active) ? 'done' : ''}><b>04</b><span>导入与激活</span></div></div></section>
    <section className="card"><div className="card-header"><strong>FINALIZED PACKS</strong><span>{data.packs.length}</span></div>{data.packs.map((pack, index) => <div className="pack-row" key={String(pack.id || pack.module_id || index)}><div><b>{pack.title || pack.id || pack.module_id}</b><span>{pack.parser_profile || 'content-package'} · {pack.active ? 'ACTIVE' : pack.status || 'INSTALLED'}</span></div><i className={pack.active ? 'active' : ''}></i></div>)}{!data.packs.length && <div className="empty">尚无已导入的 CoC Module Pack。</div>}</section>
    <section className="card"><div className="card-header"><strong>DRAFT / REVIEW JOBS</strong><span>{data.finalizedDrafts.length}</span></div>{data.finalizedDrafts.map((job, index) => <div className="json-row" key={index}><b>{String(job.title || job.package_id || job.job_id || `Draft ${index + 1}`)}</b><code>{String(job.stage || job.status || 'finalized')}</code></div>)}{!data.finalizedDrafts.length && <div className="empty">没有待导入的已定稿草稿。</div>}</section>
    <section className="card span-2"><div className="card-header"><strong>SCENE INDEX</strong><span>{data.scenes.length}</span></div><div className="scene-table">{data.scenes.map((scene) => <article key={scene.scene_id}><header><span>{scene.chapter || scene.module || 'SCENE'}</span><b>{scene.visibility || 'dm'}</b></header><h4>{scene.title}</h4><footer><span>{scene.scene_type || 'investigation'}</span><span>{arrayLength(scene.clues)} clues</span><span>{arrayLength(scene.checks)} checks</span><span>{arrayLength(scene.sanity)} SAN</span>{scene.page_start && <span>p.{scene.page_start}{scene.page_end ? `–${scene.page_end}` : ''}</span>}</footer></article>)}</div></section>
  </div>;
}

function Rules({ data }: { data: CampaignWorkspace }) {
  const lock = Array.isArray(data.ruleLock?.lock) ? data.ruleLock.lock as Array<Record<string, unknown>> : [];
  return <div className="grid-2">
    <section className="card span-2"><div className="card-header"><strong>CORE RULES PACK PIPELINE</strong><span>PRIVATE SOURCE / SCHEMA V2</span></div><div className="pipeline"><div className={data.ruleSources.length ? 'done' : 'active'}><b>01</b><span>规则源归一化</span></div><div className={data.ruleSources.length ? 'done' : ''}><b>02</b><span>证据检索审计</span></div><div className={data.rulePacks.length ? 'done' : ''}><b>03</b><span>定稿与导入</span></div><div className={lock.length ? 'done' : ''}><b>04</b><span>分支规则锁激活</span></div></div></section>
    <section className="card"><div className="card-header"><strong>RULE PACKS</strong><span>{data.rulePacks.length}</span></div>{data.rulePacks.map((pack, index) => <div className="pack-row" key={String(pack.pack_id || index)}><div><b>{String(pack.title || pack.pack_id || 'Rules Pack')}</b><span>{String(pack.version || '—')} · {String(pack.status || 'installed').toUpperCase()}</span></div><i className={lock.some((item) => item.pack_id === pack.pack_id) ? 'active' : ''}></i></div>)}{!data.rulePacks.length && <div className="empty">尚未导入 CoC core_rules Pack。</div>}</section>
    <section className="card"><div className="card-header"><strong>EFFECTIVE RULE LOCK</strong><span>{lock.length}</span></div>{lock.map((item, index) => <div className="json-row" key={String(item.pack_id || index)}><b>{String(item.pack_id || 'pack')}</b><code>{String(item.version || '—')}</code></div>)}{!lock.length && <div className="empty">当前分支没有已激活的规则包。</div>}<p className="hint">使用 `rule_query(search → expand)` 读取来源证据；模糊规则仍由 Keeper 解释。</p></section>
    <section className="card span-2"><div className="card-header"><strong>INDEXED RULE SOURCES</strong><span>{data.ruleSources.length}</span></div><div className="scene-table">{data.ruleSources.map((source, index) => <article key={String(source.source_id || source.id || index)}><header><span>{String(source.source_key || 'SOURCE')}</span><b>COC7E</b></header><h4>{String(source.title || source.name || 'Reviewed rule source')}</h4><footer><span>{String(source.checksum || 'managed checksum')}</span></footer></article>)}</div></section>
  </div>;
}

function Dialogue({ data }: { data: CampaignWorkspace }) {
  return <div className="grid-2">
    <section className="card"><div className="card-header"><strong>ACTIVE NPC CONVERSATIONS</strong><span>{data.conversations.length}</span></div>{data.phase !== 'play' && <div className="empty">隔离 NPC 对话只在 Play phase 开放。</div>}{data.conversations.map((conversation, index) => { const participants = Array.isArray(conversation.participants) ? conversation.participants as Array<Record<string, unknown>> : []; return <article className="conversation-row" key={String(conversation.conversation_id || index)}><header><b>{String(conversation.status || 'open').toUpperCase()}</b><code>REV {String(conversation.conversation_revision ?? '—')}</code></header><p>{participants.map((item) => String(item.name || item.actor_id)).join(' · ') || String(conversation.conversation_id)}</p><footer><span>{String(conversation.pending_activation_count ?? 0)} pending activations</span><span>{String(conversation.publication_count ?? 0)} publications</span></footer></article>; })}{data.phase === 'play' && !data.conversations.length && <div className="empty">没有活动对话；新对话必须列出全部参与者并至少包含一个 NPC。</div>}</section>
    <section className="card procedure-card"><div className="card-header"><strong>ISOLATED DIALOGUE CONTRACT</strong><span>NO PRIVATE LEAKAGE</span></div><ol><li><b>Ingest</b><span>Agent 显式提交感知、理解与可回应者。</span></li><li><b>Claim locally</b><span>host-local worker 领取单个 NPC 私有 capsule。</span></li><li><b>Publish</b><span>Director 只接收服务器派生的可发布输出。</span></li><li><b>Settle</b><span>解决机制请求后，close 提交公开记录与选定变化。</span></li></ol><p className="hint">活动对话会阻止 phase、Chase 与 Combat 转换；不继续时必须 close 或 abort。</p></section>
    <section className="card span-2"><div className="card-header"><strong>BOUNDED EVALUATION</strong><span>SIGNED / TOOL-FREE / NO STATE WRITE</span></div><div className="mode-cards"><article><b>ACTOR / FACTION</b><p>生成短期签名上下文；不能代替真人调查员选择。</p></article><article><b>AUDIENCE / SOURCE / RULING</b><p>验证严格 proposal；只有显式后续 MCP 调用才能修改权威状态。</p></article></div></section>
  </div>;
}

function Encounter({ data }: { data: CampaignWorkspace }) {
  const encounter = data.encounter; const state = asRecord(encounter?.combat || encounter?.chase);
  return <div className="grid-2"><section className="card"><div className="card-header"><strong>AUTHORITATIVE ENCOUNTER</strong><span>{encounter ? data.phase.toUpperCase() : 'INACTIVE'}</span></div>{encounter ? <><div className="encounter-title"><span>ROUND</span><strong>{String(state.round ?? state.turn ?? '—')}</strong></div><div className="signal-grid"><Datum label="CURRENT ACTOR" value={state.current_actor_id || '—'} /><Datum label="POSITIONING" value={state.positioning_mode || 'agent'} /><Datum label="REVISION" value={encounter.campaign_revision} /><Datum label="PARTICIPANTS" value={arrayLength(state.participants || state.combatants)} /></div><div className="action-chips">{encounter.available_actions.map((item) => <span key={item}>{item}</span>)}</div></> : <div className="empty">当前没有权威追逐或战斗。追逐留在 Play；Combat 只能由 `combat_start` 进入并由 `combat_end` 返回 Play。</div>}</section>
    <section className="card"><div className="card-header"><strong>SPATIAL CONTRACT</strong><span>EXPLICIT MODE</span></div><div className="mode-cards"><article><b>GRID</b><p>坐标、移动与几何由引擎权威结算。</p></article><article><b>AGENT</b><p>无合成坐标；距离、视线与遮挡由 Agent 基于证据裁定。</p></article><article><b>VEHICLE</b><p>载具绑定来源卡的 source id、名称、Build 与 MOV；碰撞后果仍由来源流程结算。</p></article></div><p className="hint">UI 只呈现 MCP 返回的 legal actions，不猜测谁能移动、反应或攻击。</p></section></div>;
}

function Continuity({ data }: { data: CampaignWorkspace }) {
  return <div className="grid-2"><section className="card"><div className="card-header"><strong>BRANCHES</strong><span>{data.branches.length}</span></div>{data.branches.map((branch) => <div className="branch-row" key={branch.id}><i></i><div><b>{branch.name || branch.id}</b><span>{branch.id} · {branch.head_snapshot_id || branch.head_revision_id || 'EMPTY HEAD'}</span></div></div>)}{!data.branches.length && <div className="empty">当前身份无法读取分支。</div>}</section>
    <section className="card"><div className="card-header"><strong>SNAPSHOT LINEAGE</strong><span>{data.snapshots.length}</span></div><div className="timeline">{data.snapshots.map((snapshot, index) => <div className="timeline-row" key={snapshot.slot}><i className={index === 0 ? 'active' : ''}></i><div><small>SLOT {snapshot.slot}{snapshot.parent_slot ? ` ← ${snapshot.parent_slot}` : ' · ROOT'}</small><b>{snapshot.label || 'Untitled snapshot'}</b><span>{snapshot.created_at ? new Date(snapshot.created_at).toLocaleString('zh-CN') : '时间未知'}</span></div></div>)}</div></section>
    <section className="card span-2"><div className="card-header"><strong>REVISION RECEIPTS</strong><span>{data.revisions.length}</span></div><div className="revision-list">{data.revisions.map((revision, index) => <div key={String(revision.id || index)}><code>{String(revision.id || `#${index + 1}`)}</code><b>{String(revision.operation || revision.kind || 'unknown operation')}</b><span>{String(revision.actor || revision.principal_id || '—')}</span></div>)}</div>{!data.revisions.length && <div className="empty">没有可见修订记录。</div>}</section></div>;
}

function ToolConsole({ client, campaignId, disabled, onMutated }: { client: ReturnType<typeof createClient>; campaignId: string; disabled: boolean; onMutated: () => void }) {
  const [tool, setTool] = useState<CocToolId>('server_capabilities');
  const [args, setArgs] = useState('{}'); const [result, setResult] = useState(''); const [busy, setBusy] = useState(false);
  const invoke = async () => { setBusy(true); setResult(''); try { const parsed = JSON.parse(args) as Record<string, unknown>; const value = await client.call(tool, parsed); setResult(JSON.stringify(value, null, 2)); } catch (error) { setResult(`ERROR\n${error instanceof Error ? error.message : String(error)}`); } finally { setBusy(false); } };
  const choose = (value: CocToolId) => { setTool(value); const needsCampaign = !['server_capabilities', 'storage_status'].includes(value); setArgs(JSON.stringify(needsCampaign ? { campaign_id: campaignId } : {}, null, 2)); setResult(''); };
  return <div className="console-layout"><section className="card console-form"><div className="card-header"><strong>NATIVE MCP TOOL</strong><span>51-TOOL CONTRACT</span></div><label>工具<select value={tool} onChange={(event) => choose(event.target.value as CocToolId)}>{TOOL_IDS.map((id) => <option key={id}>{id}</option>)}</select></label><label>Arguments（网关自动注入 principal）<textarea value={args} onChange={(event) => setArgs(event.target.value)} spellCheck={false} /></label><div className="console-actions"><button className="btn btn-primary" disabled={disabled || busy} onClick={invoke}>{busy ? '调用中…' : '调用权威 MCP'}</button><button className="btn btn-ghost" disabled={disabled} onClick={onMutated}>调用后刷新工作台</button></div>{disabled && <p className="hint">演示模式不会发送任何工具调用。移除 `?demo=1` 并连接认证网关后才能使用。</p>}</section><section className="card console-output"><div className="card-header"><strong>STRUCTURED RESULT</strong><span>NO SYNTHETIC SUCCESS</span></div><pre>{result || '等待 MCP 返回结构化结果。\n\n写操作必须自行提供 expected_revision、expected_character_revision、expected_branch_id 和 idempotency_key 等当前 schema 要求的守卫。'}</pre></section></div>;
}
