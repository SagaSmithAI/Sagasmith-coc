import { useEffect, useMemo, useState } from 'react';
import { createClient, emitRuntimeStatus } from '../lib/api';
import type { Campaign } from '../types';
import { CampaignCards, RuntimeError } from './Dashboard';

export default function CampaignList() {
  const client = useMemo(() => createClient(), []);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => { client.listCampaigns().then((result) => {
    setCampaigns(result.campaigns); emitRuntimeStatus(true, { version: result.capabilities?.version, mode: client.mode });
  }).catch((reason) => { setError(reason instanceof Error ? reason.message : String(reason)); emitRuntimeStatus(false, { mode: client.mode }); }).finally(() => setLoading(false)); }, [client]);
  return <div className="page">
    <div className="page-heading"><div><div className="eyebrow">CAMPAIGN REGISTRY</div><h1>调查档案</h1><p>只显示当前认证身份可访问的 coc7e 战役。</p></div><a className="btn btn-ghost" href={client.mode === 'demo' ? '/?demo=1' : '/'}>返回现场</a></div>
    {client.mode === 'demo' && <div className="demo-notice"><strong>DEMO DATA</strong><span>这是两条并行战役的 UI 演示档案，不是回测完成证明。</span></div>}
    {loading ? <div className="empty card">正在读取档案……</div> : error ? <RuntimeError message={error} /> : <CampaignCards campaigns={campaigns} mode={client.mode} />}
  </div>;
}
