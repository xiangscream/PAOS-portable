'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {fork} = require('node:child_process');
const {once} = require('node:events');
const {createServer} = require('./server/index.cjs');
const TARGET = 'fixture-native-session';
const OTHER = 'fixture-second-native-session';
const {workbuddy_send} = require('./send.cjs');

test('HTTP sends to the exact native id once; rejects unauthorized callers and other targets', async () => {
  const calls = [];
  const server = createServer({conversations: {sendPrompt: async (...args) => {
    calls.push(args); return {disposition: 'queued', item: {id: 'fixture-queue'}};
  }}}, 'fixture-token', [TARGET, OTHER]);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const endpoint = `http://127.0.0.1:${server.address().port}/send`;
  const post = (token, target) => fetch(endpoint, {method: 'POST', headers: {
    Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'
  }, body: JSON.stringify({session_id: target, message: 'fixture-message'})});
  try {
    assert.equal((await post('wrong', TARGET)).status, 401);
    assert.equal((await post('fixture-token', 'other-session')).status, 400);
    assert.equal(calls.length, 0);
    const probe = await fetch(endpoint.replace('/send', '/probe'), {headers: {Authorization: 'Bearer fixture-token'}});
    assert.deepEqual((await probe.json()).targets, [TARGET, OTHER]);
    assert.equal(calls.length, 0);
    const response = await post('fixture-token', TARGET);
    const result = await response.json();
    assert.equal(response.status, 200);
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0].slice(0, 2), [TARGET, [{type: 'text', text: 'fixture-message'}]]);
    assert.equal(calls[0][2].clientRequestId, result.clientRequestId);
    assert.equal(calls[0][2]._expectQueueReceipt, true);
    assert.equal(Object.hasOwn(calls[0][2], 'modelId'), false);
    assert.equal(result.bridge_result.disposition, 'queued');
    assert.equal(result.completed, false);
    const second = await fetch(endpoint, {method: 'POST', headers: {Authorization: 'Bearer fixture-token'},
      body: JSON.stringify({session_id: OTHER, message: 'second-target', clientRequestId: 'durable-attempt'})});
    assert.equal((await second.json()).clientRequestId, 'durable-attempt');
    assert.equal(calls[1][0], OTHER);
    assert.equal(calls.length, 2);
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('SDK permission refusal and ApiError remain failures; neither is retried', async () => {
  for (const mode of ['throw', 'api-error']) {
    let calls = 0;
    const server = createServer({conversations: {sendPrompt: async () => {
      calls++;
      if (mode === 'throw') throw Object.assign(new Error('Denied by host'), {code: 'PERMISSION_DENIED'});
      return {errorCode: 'AUTHENTICATION_REQUIRED', message: 'Authentication required'};
    }}}, 'fixture-token', [TARGET, OTHER]);
    server.listen(0, '127.0.0.1'); await once(server, 'listening');
    try {
      const response = await fetch(`http://127.0.0.1:${server.address().port}/send`, {
        method: 'POST', headers: {Authorization: 'Bearer fixture-token'},
        body: JSON.stringify({session_id: TARGET, message: 'fixture-message'})
      });
      const result = await response.json();
      assert.equal(response.status, 502);
      assert.equal(calls, 1);
      assert.equal(result.retry, false);
      assert.equal(result.delivery, 'not_confirmed');
      assert.equal(result.code, mode === 'throw' ? 'PERMISSION_DENIED' : 'AUTHENTICATION_REQUIRED');
    } finally { await new Promise(resolve => server.close(resolve)); }
  }
});

test('explicit model passes unchanged with durable request id and queued receipt; invalid models never call SDK', async () => {
  const calls = [];
  const server = createServer({conversations: {sendPrompt: async (...args) => {
    calls.push(args);
    return {disposition: 'queued', item: {id: 'fixture-queue', sendOptions: args[2]}};
  }}}, 'fixture-token', [TARGET]);
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const post = modelId => fetch(`http://127.0.0.1:${server.address().port}/send`, {
    method: 'POST', headers: {Authorization: 'Bearer fixture-token'},
    body: JSON.stringify({session_id: TARGET, message: 'fixture', clientRequestId: 'night-attempt', modelId})
  });
  try {
    for (const invalid of ['', '  ', null, 4]) assert.equal((await post(invalid)).status, 400);
    assert.equal(calls.length, 0);
    const response = await post('fixture-native-model');
    const result = await response.json();
    assert.equal(response.status, 200);
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0][2], {clientRequestId: 'night-attempt', _expectQueueReceipt: true, modelId: 'fixture-native-model'});
    assert.equal(result.bridge_result.disposition, 'queued');
    assert.equal(result.bridge_result.item.sendOptions.modelId, 'fixture-native-model');
    assert.equal(result.clientRequestId, 'night-attempt');
    assert.equal(result.completed, false);
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('installed fork-preload supplies activate(wb) and generates the expected wire call (isolated mock host)', async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'paos-send-fixture-'));
  await fs.mkdir(path.join(directory, 'server'));
  await fs.copyFile(path.join(__dirname, 'server/index.cjs'), path.join(directory, 'server/index.cjs'));
  await fs.writeFile(path.join(directory, 'targets.json'), JSON.stringify({targets: [TARGET, OTHER]}));
  const child = fork(process.env.WORKBUDDY_FORK_PRELOAD || 'D:/work/WorkBuddy/resources/app.asar.unpacked/main/preload/fork-preload.cjs',
    [path.join(directory, 'server/index.cjs')], {
      env: {...process.env, WB_EXTENSION_ID: 'paos-session-send-fixture'}, stdio: ['ignore', 'ignore', 'pipe', 'ipc']
    });
  const calls = [];
  child.on('message', message => {
    if (message.type === 'invoke:request') {
      calls.push(message);
      child.send({type: 'invoke:response', requestId: message.requestId, result: null});
    }
  });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Fixture activation timeout')), 5000);
      child.on('message', message => {
        if (message.type === 'wb-extension-ready') {clearTimeout(timer); resolve();}
      });
      child.once('exit', code => {clearTimeout(timer); reject(new Error(`Fixture exited ${code}`));});
    });
    const result = await workbuddy_send(TARGET, 'fixture-message', path.join(directory, '.runtime.json'));
    assert.equal(calls.length, 1);
    assert.equal(calls[0].channel, 'wb:conversations:sendPrompt');
    assert.deepEqual(calls[0].args.slice(1, 3), [TARGET, [{type: 'text', text: 'fixture-message'}]]);
    assert.equal(result.completed, false);
    assert.equal(result.bridge_result, null);
    assert.equal(Object.hasOwn(calls[0].args[3], 'modelId'), false);
    await workbuddy_send(TARGET, 'explicit-model-fixture', path.join(directory, '.runtime.json'), 'fixture-native-model');
    assert.equal(calls.length, 2);
    assert.equal(calls[1].channel, 'wb:conversations:sendPrompt');
    assert.equal(calls[1].args[3].modelId, 'fixture-native-model');
  } finally {
    const exited = once(child, 'exit');
    child.kill('SIGTERM'); await exited;
    assert.ok(path.resolve(directory).startsWith(path.resolve(os.tmpdir()) + path.sep));
    assert.ok(path.basename(directory).startsWith('paos-send-fixture-'));
    await fs.rm(directory, {recursive: true});
  }
});

