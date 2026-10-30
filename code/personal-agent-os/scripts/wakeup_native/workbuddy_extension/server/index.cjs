'use strict';
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const {randomBytes, randomUUID} = require('node:crypto');

async function workbuddy_send(wb, session_id, message, targets, requestId, modelId) {
  if (!targets.includes(session_id)) throw new Error('Target session is outside this installation grant');
  if (typeof message !== 'string' || !message.trim()) throw new Error('message must be nonempty text');
  const clientRequestId = requestId || randomUUID();
  const options = {clientRequestId, _expectQueueReceipt: true};
  if (modelId !== undefined) options.modelId = modelId;
  const result = await wb.conversations.sendPrompt(session_id, [{type: 'text', text: message}], options);
  if (result?.errorCode) throw Object.assign(new Error(result.message), {code: result.errorCode});
  return {session_id, clientRequestId, bridge_result: result ?? null, completed: false};
}

function createServer(wb, token, targets) {
  return http.createServer(async (req, res) => {
    const reply = (status, value) => {
      res.writeHead(status, {'Content-Type': 'application/json; charset=utf-8'});
      res.end(JSON.stringify(value));
    };
    if (req.headers.authorization !== `Bearer ${token}`) {
      req.resume();
      return reply(401, {error: 'Local sender authorization required'});
    }
    if (req.method === 'GET' && req.url === '/probe') {
      return reply(200, {targets, native_state: 'unknown'});
    }
    if (req.method !== 'POST' || req.url !== '/send') {
      req.resume();
      return reply(404, {error: 'Use POST /send'});
    }
    let input;
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      if (!input || typeof input !== 'object') throw new Error('JSON object required');
      if (!targets.includes(input.session_id) || typeof input.message !== 'string' || !input.message.trim()
          || (input.clientRequestId !== undefined && (typeof input.clientRequestId !== 'string' || !input.clientRequestId.trim()))
          || (input.modelId !== undefined && (typeof input.modelId !== 'string' || !input.modelId.trim()))) {
        throw new Error('Expected authorized session_id, nonempty message and optional nonempty clientRequestId/modelId');
      }
    } catch (error) {
      return reply(400, {error: error.message});
    }
    try {
      reply(200, await workbuddy_send(wb, input.session_id, input.message, targets, input.clientRequestId, input.modelId));
    } catch (error) {
      reply(502, {error: error.message, code: error.code, delivery: 'not_confirmed', retry: false});
    }
  });
}

async function activate(wb) {
  const {targets} = JSON.parse(await fs.readFile(path.join(__dirname, '..', 'targets.json'), 'utf8'));
  if (!Array.isArray(targets) || !targets.length || targets.some(id => typeof id !== 'string' || !id.trim())) {
    throw new Error('targets.json must contain explicitly authorized native session IDs');
  }
  const token = randomBytes(32).toString('hex');
  const server = createServer(wb, token, targets);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const runtimeFile = path.join(__dirname, '..', '.runtime.json');
  try {
    await fs.writeFile(runtimeFile, JSON.stringify({
      endpoint: `http://127.0.0.1:${server.address().port}`, token, pid: process.pid, targets
    }), {mode: 0o600});
  } catch (error) {
    await new Promise(resolve => server.close(resolve));
    throw error;
  }
  console.log('PAOS Session Send listening on loopback');
  return {dispose: async () => {
    await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    await fs.unlink(runtimeFile);
  }};
}

module.exports = {activate, createServer, workbuddy_send};
