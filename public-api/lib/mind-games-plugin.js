/**
 * Mind Games S² plugin — progress, achievements, strength profiles.
 * File-backed store under data/mind-games/
 */
const fs = require('fs');
const path = require('path');
const express = require('express');

const DATA_DIR = path.join(__dirname, '..', 'data', 'mind-games');

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function storePath(name) {
  return path.join(DATA_DIR, `${name}.json`);
}

function readStore(name, fallback = {}) {
  ensureDataDir();
  const file = storePath(name);
  if (!fs.existsSync(file)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeStore(name, data) {
  ensureDataDir();
  fs.writeFileSync(storePath(name), JSON.stringify(data, null, 2), 'utf8');
}

function bearerOk(req) {
  const expected = (process.env.MIND_GAMES_PLUGIN_TOKEN || '').trim();
  if (!expected) return true;
  const auth = req.get('Authorization') || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  return token === expected;
}

function unauthorized(res) {
  return res.status(401).json({ ok: false, error: 'Unauthorized' });
}

async function forwardStrengthToIngest(playerId, strengthData) {
  const ingestUrl = (process.env.VITALSYNC_INGEST_API_URL || '').replace(/\/$/, '');
  if (!ingestUrl) return { forwarded: false };

  const ingestKey = process.env.VITALSYNC_INGEST_API_KEY || '';
  const headers = { 'Content-Type': 'application/json' };
  if (ingestKey) headers['X-Ingest-Key'] = ingestKey;

  try {
    const res = await fetch(`${ingestUrl}/v1/events`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        events: [
          {
            source: 'mind_games',
            ts: Date.now(),
            partition_key: playerId,
            payload: {
              type: 'strength_profile_sync',
              player_id: playerId,
              ...strengthData,
            },
            labels: {
              bucket: 'evidence',
              appId: 'mind_games',
              program: 'mind_games',
            },
          },
        ],
      }),
    });
    return { forwarded: res.ok, status: res.status };
  } catch (e) {
    return { forwarded: false, error: e.message };
  }
}

function mountMindGamesPlugin(app) {
  const router = express.Router();

  router.post('/register', (req, res) => {
    if (!bearerOk(req)) return unauthorized(res);
    const plugins = readStore('plugins', {});
    const pluginId = req.body?.plugin_id || 'mind-games';
    plugins[pluginId] = {
      ...req.body,
      registered_at: new Date().toISOString(),
    };
    writeStore('plugins', plugins);
    return res.json({ ok: true, plugin_id: pluginId });
  });

  router.post('/progress', (req, res) => {
    if (!bearerOk(req)) return unauthorized(res);
    const { player_id: playerId, game_type: gameType, progress_data: progressData } =
      req.body || {};
    if (!playerId) {
      return res.status(400).json({ ok: false, error: 'player_id required' });
    }

    const progress = readStore('progress', {});
    if (!progress[playerId]) progress[playerId] = [];
    progress[playerId].push({
      game_type: gameType,
      progress_data: progressData,
      timestamp: req.body?.timestamp || new Date().toISOString(),
    });
    writeStore('progress', progress);

    return res.json({ ok: true, player_id: playerId });
  });

  router.post('/achievements', (req, res) => {
    if (!bearerOk(req)) return unauthorized(res);
    const {
      player_id: playerId,
      achievement_id: achievementId,
      achievement_name: achievementName,
      achievement_data: achievementData,
    } = req.body || {};
    if (!playerId || !achievementId) {
      return res.status(400).json({ ok: false, error: 'player_id and achievement_id required' });
    }

    const achievements = readStore('achievements', {});
    if (!achievements[playerId]) achievements[playerId] = [];
    achievements[playerId].push({
      achievement_id: achievementId,
      achievement_name: achievementName,
      achievement_data: achievementData,
      timestamp: req.body?.timestamp || new Date().toISOString(),
    });
    writeStore('achievements', achievements);

    return res.json({ ok: true, player_id: playerId, achievement_id: achievementId });
  });

  router.post('/strengths', async (req, res) => {
    if (!bearerOk(req)) return unauthorized(res);
    const { player_id: playerId, strength_data: strengthData } = req.body || {};
    if (!playerId || !strengthData) {
      return res.status(400).json({ ok: false, error: 'player_id and strength_data required' });
    }

    const strengths = readStore('strengths', {});
    strengths[playerId] = {
      ...strengthData,
      received_at: new Date().toISOString(),
    };
    writeStore('strengths', strengths);

    const ingest = await forwardStrengthToIngest(playerId, strengthData);

    return res.json({
      ok: true,
      player_id: playerId,
      top_strengths: strengthData.top_strengths || [],
      vitalsync_ingest: ingest,
    });
  });

  router.get('/player/:playerId', (req, res) => {
    if (!bearerOk(req)) return unauthorized(res);
    const playerId = req.params.playerId;
    const progress = readStore('progress', {});
    const achievements = readStore('achievements', {});
    const strengths = readStore('strengths', {});

    return res.json({
      ok: true,
      player_id: playerId,
      progress: progress[playerId] || [],
      achievements: achievements[playerId] || [],
      strength_profile: strengths[playerId] || null,
    });
  });

  router.get('/health', (_req, res) => {
    return res.json({
      ok: true,
      plugin: 'mind-games',
      strength_profile_sync: true,
      data_dir: DATA_DIR,
    });
  });

  app.use('/api/plugins/mind-games', router);
  app.use('/api/auth/validate', (req, res) => {
    if (req.method === 'GET' && bearerOk(req)) {
      return res.json({ ok: true });
    }
    if (req.method === 'GET') return unauthorized(res);
    return res.status(405).end();
  });

  ensureDataDir();
}

module.exports = { mountMindGamesPlugin };
