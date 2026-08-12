import { describe, expect, it, vi } from 'vitest';
import { CocGatewayClient, GatewayError, TOOL_IDS } from './api';

describe('CoC MCP gateway contract', () => {
  it('tracks the exact 43-tool native contract', () => {
    expect(TOOL_IDS).toHaveLength(43);
    expect(new Set(TOOL_IDS).size).toBe(43);
    expect(TOOL_IDS).toContain('investigation_check');
    expect(TOOL_IDS).toContain('content_pack');
    expect(TOOL_IDS).toContain('combat_query');
  });

  it('uses credentials and never adds a browser principal', async () => {
    const fetchImpl = vi.fn(async (_url: string | URL | Request, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body));
      expect(init?.credentials).toBe('include');
      expect(body).toEqual({ tool: 'campaign_query', arguments: { action: 'list' } });
      return new Response(JSON.stringify({ ok: true, result: { campaigns: [] } }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }) as unknown as typeof fetch;
    const client = new CocGatewayClient({ baseUrl: 'https://gateway.test', fetchImpl });
    await expect(client.call('campaign_query', { action: 'list' })).resolves.toEqual({ campaigns: [] });
    expect(fetchImpl).toHaveBeenCalledWith('https://gateway.test/api/coc/mcp/tool', expect.any(Object));
  });

  it('rejects browser-supplied principal_id before networking', async () => {
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const client = new CocGatewayClient({ fetchImpl });
    await expect(client.call('campaign_query', { action: 'list', principal_id: 'owner:forged' })).rejects.toMatchObject({ category: 'contract' });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('keeps demo mode read-only', async () => {
    const client = new CocGatewayClient({ mode: 'demo' });
    const result = await client.listCampaigns();
    expect(result.campaigns).toHaveLength(2);
    await expect(client.call('campaign_change', { action: 'create' })).rejects.toBeInstanceOf(GatewayError);
  });

  it('unwraps FastMCP structuredContent responses', async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({ result: { structuredContent: { phase: 'play' } } }), { status: 200 })) as unknown as typeof fetch;
    const client = new CocGatewayClient({ fetchImpl });
    await expect(client.call('game_phase', { campaign_id: 'c1' })).resolves.toEqual({ phase: 'play' });
  });
});
