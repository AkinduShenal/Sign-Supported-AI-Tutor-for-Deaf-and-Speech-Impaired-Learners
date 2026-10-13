/** Actual researcher-button download against an empty, isolated SQLite DB.
 * Run from frontend/: node tests/gameCsvDownload.e2e.mjs
 * No production URL, real observations or successful HTTP mocks are used.
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backend = path.resolve(frontend, '../backend')
const output = path.join(frontend, 'artifacts', 'csv-download-' + Date.now())
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-csv-download-'))
const api = 'http://127.0.0.1:8142/api/v1'
const key = 'synthetic-browser-export-key-only'
const children = [], errors = []
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))

function launch(command, args, cwd, env = {}) {
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
  child.on('error', error => errors.push(String(error)))
  child.stdout.on('data', () => {})
  child.stderr.on('data', data => { if (process.env.GAME_DOWNLOAD_VERBOSE) process.stderr.write(data) })
  children.push(child)
  return child
}

async function ready(url, child) {
  for (let n = 0; n < 200; n++) {
    if (child.exitCode !== null) throw Error('Local test process exited: ' + url)
    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* startup */ }
    await delay(100)
  }
  throw Error('Local startup timed out: ' + url)
}

try {
  await fs.mkdir(output, { recursive: true })
  for (const port of [8142, 5199, 9249]) {
    let occupied = false
    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); occupied = true } catch { /* unused */ }
    assert.equal(occupied, false, `Port ${port} already occupied`)
  }
  const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python'
  const code = `
import uvicorn
from app.main import app
from app.db.base import Base
from app.db.session import engine
from app.modules.game.models import GameSession, GameplayEvent, GameTaskAttempt, GameResult
assert engine.url.get_backend_name() == 'sqlite'
Base.metadata.create_all(engine, tables=[GameSession.__table__, GameplayEvent.__table__, GameTaskAttempt.__table__, GameResult.__table__])
uvicorn.run(app, host='127.0.0.1', port=8142, access_log=False)
`
  const server = launch(path.join(backend, python), ['-c', code], backend, {
    DATABASE_URL: 'sqlite+pysqlite:///' + path.join(output, 'synthetic-empty.sqlite').replaceAll('\\', '/'),
    GAME_COLLECTION_EXPORT_KEY: key,
  })
  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5199', '--strictPort'], frontend, { VITE_API_BASE_URL: api })
  const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*', '--remote-debugging-port=9249', `--user-data-dir=${profile}`, 'about:blank'], frontend)
  await Promise.all([ready(api + '/health', server), ready('http://127.0.0.1:5199', vite), ready('http://127.0.0.1:9249/json', chrome)])
  const targets = await (await fetch('http://127.0.0.1:9249/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const next = ++id
    const timeout = setTimeout(() => { pending.delete(next); reject(Error('CDP timeout: ' + method)) }, 15000)
    pending.set(next, { resolve, reject, timeout })
    socket.send(JSON.stringify({ id: next, method, params }))
  })
  socket.addEventListener('close', () => { for (const p of pending.values()) { clearTimeout(p.timeout); p.reject(Error('Browser closed')) }; pending.clear() })
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text)
    const p = pending.get(message.id)
    if (!p) return
    pending.delete(message.id); clearTimeout(p.timeout)
    if (message.error) p.reject(Error(JSON.stringify(message.error)))
    else p.resolve(message.result)
  })
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  async function until(expression) {
    for (let n = 0; n < 200; n++) { if (await evaluate(expression)) return; await delay(100) }
    throw Error('Timed out: ' + expression + '; ' + await evaluate('document.body.innerText'))
  }
  await send('Runtime.enable'); await send('Page.enable')
  await send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: output })
  await send('Page.navigate', { url: 'http://127.0.0.1:5199' })
  await until(`!!document.querySelector('.collection-export summary')`)
  await evaluate(`document.querySelector('.collection-export summary').click()`)
  await until(`!!document.querySelector('#game-export-key') && !document.querySelector('#game-export-key').disabled`)
  const submit = `document.querySelector('.collection-export button')`
  assert.equal(await evaluate(`${submit}.disabled`), true)
  async function enter(value) {
    await evaluate(`(() => { const e=document.querySelector('#game-export-key'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)}); e.dispatchEvent(new Event('input',{bubbles:true})); })()`)
    await delay(80)
  }
  await enter('incorrect-test-key')
  await evaluate(`${submit}.click()`)
  await until(`document.querySelector('.collection-export [role=alert]')?.textContent.includes('incorrect')`)
  assert.equal((await fs.readdir(output)).filter(name => name.endsWith('.zip')).length, 0)
  await enter(key)
  await evaluate(`${submit}.click()`)
  await until(`document.querySelector('.collection-export [role=status]')?.textContent.includes('Download started')`)
  let downloads = []
  for (let n = 0; n < 100; n++) {
    downloads = (await fs.readdir(output)).filter(name => name.endsWith('.zip'))
    if (downloads.length) break
    await delay(100)
  }
  assert.equal(downloads.length, 1)
  const archive = await fs.readFile(path.join(output, downloads[0]))
  assert.equal(archive.subarray(0, 2).toString(), 'PK')
  assert.equal(await evaluate(`JSON.stringify(localStorage).includes(${JSON.stringify(key)})`), false)
  assert.deepEqual(errors, [])
  const screenshot = await send('Page.captureScreenshot')
  await fs.writeFile(path.join(output, 'download-button.png'), Buffer.from(screenshot.data, 'base64'))
  await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify({ status: 'PASS', kind: 'synthetic_engineering_only', download: downloads[0], bytes: archive.length, checks: ['empty key disabled', 'wrong key rejected', 'real HTTP button download', 'ZIP saved by browser', 'key not persisted', 'no runtime exceptions'] }, null, 2))
  console.log('PASS actual CSV download button: ' + output)
} finally {
  socket?.close()
  for (const child of children) child.kill('SIGTERM')
}
