#!/usr/bin/env node
/**
 * Smoke test for Mind Games plugin routes on public-api.
 * Usage: node scripts/smoke-mind-games-plugin.js [baseUrl]
 */
const base = (process.argv[2] || 'http://127.0.0.1:3010').replace(/\/$/, '');

async function main() {
  const playerId = `smoke-${Date.now()}`;
  const strengthData = {
    player_id: playerId,
    neurodivergent_types: ['adhd'],
    strength_scores: { hyperfocus: 0.55, creative_thinking: 0.42 },
    top_strengths: [{ id: 'hyperfocus', label: 'Hyperfocus', score: 0.55 }],
    recommended_games: ['focusTraining'],
    synced_at: new Date().toISOString(),
  };

  const health = await fetch(`${base}/api/plugins/mind-games/health`);
  console.log('health', health.status, await health.json());

  const strengths = await fetch(`${base}/api/plugins/mind-games/strengths`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_id: playerId, strength_data: strengthData }),
  });
  console.log('strengths', strengths.status, await strengths.json());

  const profile = await fetch(`${base}/api/plugins/mind-games/player/${playerId}`);
  console.log('profile', profile.status, await profile.json());
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
