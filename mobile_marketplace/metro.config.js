const { getDefaultConfig } = require('expo/metro-config');
const dns = require('dns');
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

/** Em redes só IPv6 instável ou dual-stack estranho, conectar ao upstream HTTPS pode falhar (502 no proxy). */
if (typeof dns.setDefaultResultOrder === 'function') {
  dns.setDefaultResultOrder('ipv4first');
}

/** Carrega `.env` na raiz do app para o processo do Metro (o proxy lê `process.env`). */
function loadProjectDotEnv() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, 'utf8');
  for (const line of text.split(/\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = val;
  }
}

loadProjectDotEnv();

const config = getDefaultConfig(__dirname);

/**
 * Proxy simples para Web dev: evita CORS no navegador.
 * Requisições para `/__ibix_api/*` são encaminhadas para o host configurado em
 * `EXPO_PUBLIC_API_BASE_URL` (ou padrão `https://www.ibix.com.br/api/v1`).
 *
 * Exemplo: GET http://localhost:8082/__ibix_api/api/v1/loja/anuncios
 * → https://www.ibix.com.br/api/v1/loja/anuncios
 */
function getProxyTarget() {
  const raw = process.env.EXPO_PUBLIC_API_BASE_URL || 'https://www.ibix.com.br/api/v1';
  try {
    const u = new URL(raw);
    return { origin: `${u.protocol}//${u.host}`, basePath: u.pathname.replace(/\/+$/, '') };
  } catch {
    return { origin: 'https://www.ibix.com.br', basePath: '/api/v1' };
  }
}

/**
 * Cabeçalhos do browser não devem ir crus ao upstream: o stack do Expo inclui `compression()`
 * no Connect; se o upstream devolver gzip e isso for re-piped, a resposta pode corromper ou
 * fechar sem corpo (Chrome: net::ERR_EMPTY_RESPONSE).
 */
function buildUpstreamHeaders(req, targetHost) {
  const headers = {};
  for (const [key, value] of Object.entries(req.headers || {})) {
    const lk = key.toLowerCase();
    if (
      lk === 'host' ||
      lk === 'origin' ||
      lk === 'referer' ||
      lk === 'connection' ||
      lk === 'keep-alive' ||
      lk === 'proxy-connection' ||
      lk === 'te' ||
      lk === 'trailer' ||
      lk === 'transfer-encoding' ||
      lk === 'upgrade' ||
      lk === 'accept-encoding' ||
      lk === 'content-length'
    ) {
      continue;
    }
    headers[key] = value;
  }
  headers.Host = targetHost;
  headers['Accept-Encoding'] = 'identity';
  return headers;
}

function filterResponseHeadersForClient(src) {
  const out = {};
  if (!src || typeof src !== 'object') return out;
  const drop = new Set([
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
  ]);
  for (const key of Object.keys(src)) {
    if (drop.has(key.toLowerCase())) continue;
    const v = src[key];
    if (v !== undefined) out[key] = v;
  }
  return out;
}

function pipeProxy(req, res) {
  if (req.method === 'OPTIONS') {
    const allowOrigin = req.headers.origin || '*';
    res.writeHead(204, {
      'Access-Control-Allow-Origin': allowOrigin,
      'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
      'Access-Control-Allow-Headers':
        req.headers['access-control-request-headers'] ||
        'Authorization,Content-Type,X-Client,X-Client-Version',
      'Access-Control-Max-Age': '7200',
      Vary: 'Origin',
    });
    res.end();
    return;
  }

  const { origin, basePath } = getProxyTarget();
  const targetUrl = new URL(origin);

  const prefix = '/__ibix_api';
  const path = req.url.startsWith(prefix) ? req.url.slice(prefix.length) : req.url;
  // Se o path já vier com `/api/v1/...` (ex.: /__ibix_api/api/v1/loja/anuncios),
  // não duplicar basePath (evita /api/v1/api/v1/...).
  const normalizedBase = basePath || '';
  const upstreamPath = (path.startsWith(normalizedBase + '/') || path === normalizedBase)
    ? path
    : `${normalizedBase}${path}`.replace(/\/{2,}/g, '/');

  const isHttps = targetUrl.protocol === 'https:';
  const client = isHttps ? https : http;

  const headers = buildUpstreamHeaders(req, targetUrl.host);

  const upstreamReq = client.request(
    {
      protocol: targetUrl.protocol,
      hostname: targetUrl.hostname,
      port: targetUrl.port || (isHttps ? 443 : 80),
      method: req.method,
      path: upstreamPath,
      headers,
      timeout: 120000,
    },
    (upstreamRes) => {
      const outHeaders = filterResponseHeadersForClient(upstreamRes.headers);
      if (!res.headersSent) {
        res.writeHead(upstreamRes.statusCode || 502, outHeaders);
      }
      upstreamRes.pipe(res);
    },
  );

  upstreamReq.on('timeout', () => {
    upstreamReq.destroy(new Error('upstream timeout'));
  });

  upstreamReq.on('error', (err) => {
    const code = err && typeof err === 'object' && 'code' in err ? err.code : '';
    if (process.env.NODE_ENV !== 'production') {
      console.error(
        '[__ibix_api proxy] falha ao falar com o upstream:',
        `${origin}${upstreamPath}`,
        '| EXPO_PUBLIC_API_BASE_URL=',
        process.env.EXPO_PUBLIC_API_BASE_URL || '(padrão https://www.ibix.com.br/api/v1)',
        '|',
        err.message,
        code ? `(${code})` : '',
        '| Na máquina onde corre o Expo: curl -sI "' +
          origin +
          (upstreamPath.startsWith('/') ? '' : '/') +
          upstreamPath.split('?')[0] +
          '" — se falhar, o proxy também dará 502.',
        '| Se .env apontar para 127.0.0.1:8000 sem uvicorn a ouvir nessa porta → ECONNREFUSED.',
      );
    }
    if (!res.headersSent) {
      res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
      res.end(
        JSON.stringify({
          detail: 'Proxy error — Metro não alcançou EXPO_PUBLIC_API_BASE_URL. Veja o terminal do Expo.',
          code: code || undefined,
          error: String(err && err.message ? err.message : err),
        }),
      );
    }
  });

  if (req.method === 'GET' || req.method === 'HEAD') upstreamReq.end();
  else req.pipe(upstreamReq);
}

config.server = config.server || {};
config.server.enhanceMiddleware = (middleware) => {
  return (req, res, next) => {
    if (req.url && req.url.startsWith('/__ibix_api/')) {
      return pipeProxy(req, res);
    }
    return middleware(req, res, next);
  };
};

module.exports = config;
