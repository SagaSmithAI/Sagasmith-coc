import { useEffect, useMemo, useState } from 'react';
import { createClient, emitRuntimeStatus } from '../lib/api';
import type { Campaign, ConnectionMode, RuntimeCapabilities } from '../types';

export default function Dashboard() {
  const client = useMemo(() => createClient(), []);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [capabilities, setCapabilities] = useState<RuntimeCapabilities | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    client.listCampaigns().then((result) => {
      setCampaigns(result.campaigns); setCapabilities(result.capabilities); setStatus('ready');
      emitRuntimeStatus(true, { version: result.capabilities?.version, mode: client.mode });
    }).catch((reason) => {
      setStatus('error'); setError(reason instanceof Error ? reason.message : String(reason));
      emitRuntimeStatus(false, { mode: client.mode });
    });
  }, [client]);

  const phases = campaigns.reduce<Record<string, number>>((counts, campaign) => {
    const phase = String(campaign.state?.game_phase || 'lobby'); counts[phase] = (counts[phase] || 0) + 1; return counts;
  }, {});

  return (
    <div className="page">
      <section className="hero-grid">
        <div className="hero-copy">
          <div className="eyebrow">KEEPER OPERATIONS / COC 7E</div>
          <h1>把调查、疯狂与连续性放在同一张桌上。</h1>
          <p>SagaSmith CoC Workbench 观察权威 MCP 会话；随机流、修订、权限与结算仍只属于运行时。</p>
          <div className="hero-actions"><a className="btn btn-primary" href="/campaigns">打开调查档案</a><a className="btn btn-ghost" href="/?demo=1">只读演示</a></div>
        </div>
        <div className="signal-card">
          <header><span>RUNTIME SIGNAL</span><i className={status === 'ready' ? 'good' : status === 'error' ? 'bad' : ''}></i></header>
          <strong>{client.mode === 'demo' ? 'DEMO / NON-AUTHORITATIVE' : status === 'ready' ? 'MCP GATEWAY READY' : status === 'error' ? 'GATEWAY OFFLINE' : 'CONNECTING'}</strong>
          <p>{client.mode === 'demo' ? '数据仅用于界面验收，所有写入均已禁用。' : error || `${capabilities?.server || 'sagasmith-coc-mcp'} ${capabilities?.version || ''}`}</p>
          {status === 'error' && client.mode === 'live' && <a href="/?demo=1">切换为明确的演示模式 →</a>}
        </div>
      </section>

      <section className="metric-strip">
        <Metric value={campaigns.length} label="可访问战役" />
        <Metric value={phases.play || 0} label="调查进行中" accent />
        <Metric value={phases.combat || 0} label="战斗现场" />
        <Metric value={capabilities?.content_pack?.schema_version ?? 2} label="PACK SCHEMA" />
      </section>

      <section className="section-block">
        <div className="section-heading"><div><span>ACTIVE DOSSIERS</span><h2>最近的调查</h2></div><a href="/campaigns">全部档案 →</a></div>
        {status === 'loading' && <div className="empty card">正在读取可访问战役……</div>}
        {status === 'error' && <RuntimeError message={error} />}
        {status === 'ready' && <CampaignCards campaigns={campaigns} mode={client.mode} />}
      </section>

      <section className="boundary-grid">
        <article><span>01</span><div><b>MCP 是状态所有者</b><p>UI 不接受浏览器提供 principal，也不在断线时伪造成功。</p></div></article>
        <article><span>02</span><div><b>Agent 是语义裁判</b><p>线索意义、受众、叙事后果与来源解释不会塞进 UI 启发式。</p></div></article>
        <article><span>03</span><div><b>Pack 是来源事实</b><p>当前 schema v2 的草稿、证据、定稿和激活状态保持可审计。</p></div></article>
      </section>
    </div>
  );
}

export function CampaignCards({ campaigns, mode }: { campaigns: Campaign[]; mode: ConnectionMode }) {
  if (!campaigns.length) return <div className="empty card">当前身份没有可访问的 CoC 战役。</div>;
  return <div className="dossier-grid">{campaigns.map((campaign) => {
    const phase = String(campaign.state?.game_phase || 'lobby');
    const params = new URLSearchParams({ id: campaign.id }); if (mode === 'demo') params.set('demo', '1');
    return <a className="dossier-card" key={campaign.id} href={`/campaigns/detail?${params}`}>
      <header><span>COC 7E / {String(campaign.settings?.era || 'ERA UNSET').toUpperCase()}</span><b className={`phase phase-${phase}`}>{phase}</b></header>
      <h3>{campaign.name}</h3><p>{campaign.description || '暂无战役摘要。'}</p>
      <footer><span>REV {campaign.revision}</span><span>{String(campaign.settings?.ruleset || 'classic').toUpperCase()}</span><i>打开 →</i></footer>
    </a>;
  })}</div>;
}

function Metric({ value, label, accent = false }: { value: unknown; label: string; accent?: boolean }) {
  return <div className={accent ? 'accent' : ''}><strong>{String(value).padStart(2, '0')}</strong><span>{label}</span></div>;
}

export function RuntimeError({ message }: { message: string }) {
  return <div className="runtime-error card"><strong>无法读取权威运行时</strong><p>{message || '请确认认证网关与 CoC MCP 会话可用。'}</p><small>浏览器应通过带凭据的 sticky-session 网关连接；不会自动回退到 mock。</small></div>;
}
