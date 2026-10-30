'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');

async function workbuddy_send(session_id, message, runtimeFile = path.join(__dirname, '.runtime.json'), modelId) {
  const runtime = JSON.parse(await fs.readFile(runtimeFile, 'utf8'));
  const response = await fetch(`${runtime.endpoint}/send`, {
    method: 'POST', headers: {'Authorization': `Bearer ${runtime.token}`, 'Content-Type': 'application/json'},
    body: JSON.stringify({session_id, message, ...(modelId === undefined ? {} : {modelId})}),
    redirect: 'error', signal: AbortSignal.timeout(30000)
  });
  const result = await response.json();
  if (!response.ok) throw Object.assign(new Error(result.error), {status: response.status, result});
  return result;
}

module.exports = {workbuddy_send};
if (require.main === module) {
  const [session_id, messageFile, modelId] = process.argv.slice(2);
  (async () => {
    if (!session_id || !messageFile) throw new Error('Usage: node send.cjs <session_id> <message-file> [modelId]');
    const message = await fs.readFile(messageFile, 'utf8');
    const result = await workbuddy_send(session_id, message, path.join(__dirname, '.runtime.json'), modelId);
    console.log(JSON.stringify(result));
  })().catch(error => {console.error(error.message); process.exitCode = 1;});
}
