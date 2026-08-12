import { useEffect, useMemo, useState } from 'react';
import { createClient, emitRuntimeStatus } from '../lib/api';
import { CHARACTERISTIC_LABELS, type Characteristic, type Investigator } from '../types';
import { RuntimeError } from './Dashboard';

const ORDER: Characteristic[] = ['str', 'con', 'siz', 'dex', 'app', 'int', 'pow', 'edu'];

export default function InvestigatorSheet() {
  const client = useMemo(() => createClient(), []); const [actor, setActor] = useState<Investigator | null>(null); const [error, setError] = useState(''); const [raw, setRaw] = useState(false);
  const id = typeof window === 'undefined' ? '' : new URLSearchParams(window.location.search).get('id') || '';
  const campaignId = typeof window === 'undefined' ? '' : new URLSearchParams(window.location.search).get('campaign') || '';
  useEffect(() => { if (!campaignId) { setError('角色读取需要 campaign 查询参数，以便 MCP 做 campaign 与 actor scope 授权。'); return; } client.getInvestigator(campaignId, id).then((value) => { setActor(value); emitRuntimeStatus(true, { mode: client.mode }); }).catch((reason) => { setError(reason instanceof Error ? reason.message : String(reason)); emitRuntimeStatus(false, { mode: client.mode }); }); }, [campaignId, client, id]);
  if (error) return <div className="page"><RuntimeError message={error} /></div>;
  if (!actor) return <div className="page"><div className="empty card">正在读取 actor-scoped 角色卡……</div></div>;
  if (!actor.sheet) return <div className="page"><div className="page-heading"><div><div className="eyebrow">REDACTED ACTOR</div><h1>{actor.name}</h1></div></div><div className="empty card">当前身份只能看到公开角色摘要，私有 sheet 已由 MCP 隐去。</div></div>;
  const sheet = actor.sheet; const conditions = Object.entries(sheet.conditions || {}).filter(([, active]) => active); const skills = Object.entries(sheet.skills || {}).sort((a, b) => b[1] - a[1]);
  const backQuery = new URLSearchParams({ id: campaignId }); if (client.mode === 'demo') backQuery.set('demo', '1');
  return <div className="page investigator-page"><div className="page-heading"><div><div className="eyebrow">INVESTIGATOR DOSSIER / REV {actor.revision}</div><h1>{actor.name}</h1><p>{sheet.occupation || actor.summary || '调查员'}</p></div><a className="btn btn-ghost" href={`/campaigns/detail?${backQuery}`}>返回战役</a></div>
    {client.mode === 'demo' && <div className="demo-notice"><strong>DEMO SHEET</strong><span>字段结构与当前 `validate_investigator_sheet` 一致，但数值不是回测记录。</span></div>}
    <section className="identity-strip"><Datum label="RULESET" value={sheet.ruleset || 'classic'} /><Datum label="OCCUPATION" value={sheet.occupation || '—'} /><Datum label="MOV" value={sheet.mov} /><Datum label="BUILD / DB" value={`${sheet.build} / ${sheet.damage_bonus}`} /><Datum label="DODGE" value={sheet.dodge} /></section>
    <section className="characteristics">{ORDER.map((key) => { const value = sheet.characteristics?.[key]; return <article key={key}><span>{CHARACTERISTIC_LABELS[key]}</span><small>{key.toUpperCase()}</small><strong>{value ?? '—'}</strong><footer><b>½ {value == null ? '—' : Math.floor(value / 2)}</b><b>⅕ {value == null ? '—' : Math.floor(value / 5)}</b></footer></article>; })}</section>
    <section className="vital-grid"><Vital label="HP" value={sheet.hp} max={sheet.max_hp} tone="blood" /><Vital label="SAN" value={sheet.san} max={sheet.san_max} tone="mind" /><Vital label="LUCK" value={sheet.luck} max={100} tone="luck" /><Vital label="MP" value={sheet.mp} max={sheet.max_mp} tone="magic" /></section>
    <div className="grid-2"><section className="card"><div className="card-header"><strong>SKILLS</strong><span>{skills.length}</span></div><div className="skill-list">{skills.map(([name, value]) => <div key={name}><span>{name}</span><i><b style={{ width: `${Math.min(100, value)}%` }} /></i><strong>{value}</strong></div>)}</div></section>
      <div className="stack"><section className="card"><div className="card-header"><strong>CONDITIONS</strong><span>{conditions.length || 'CLEAR'}</span></div>{conditions.length ? <div className="action-chips danger">{conditions.map(([name]) => <span key={name}>{name}</span>)}</div> : <p className="empty compact">没有活动状态。</p>}</section><section className="card"><div className="card-header"><strong>DEVELOPMENT</strong><span>LOBBY SETTLEMENT</span></div><div className="action-chips">{(sheet.development?.checked_skills || []).map((name) => <span key={name}>{name}</span>)}</div>{!(sheet.development?.checked_skills || []).length && <p className="empty compact">没有待结算成长标记。</p>}</section><section className="card"><div className="card-header"><strong>WEAPONS</strong><span>{sheet.weapons?.length || 0}</span></div>{sheet.weapons?.map((weapon) => <div className="weapon-row" key={weapon.name}><b>{weapon.name}</b><span>{weapon.skill || '—'} · {weapon.damage || '—'} · {weapon.range || '近战'}</span></div>)}</section></div>
    </div><section className="card raw-sheet"><button onClick={() => setRaw(!raw)}><span>完整 sheet JSON</span><b>{raw ? '收起' : '展开'}</b></button>{raw && <pre>{JSON.stringify(sheet, null, 2)}</pre>}</section>
  </div>;
}

function Datum({ label, value }: { label: string; value: unknown }) { return <div><span>{label}</span><strong>{String(value)}</strong></div>; }
function Vital({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) { const pct = Math.max(0, Math.min(100, max ? value / max * 100 : 0)); return <article className={`vital ${tone}`}><header><span>{label}</span><strong>{value}<small> / {max}</small></strong></header><i><b style={{ width: `${pct}%` }} /></i></article>; }
