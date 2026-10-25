/** Local backend routing regression: synthetic queued evidence, isolated test server only. */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const output = path.join(root, 'artifacts', 'backend-routing-' + Date.now())
const key = 'synthetic_demo_key_' + (await import('node:crypto')).randomBytes(24).toString('hex')
const repo = path.resolve(root, '..')
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'development-demo-browser-'))
const chromePath = process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const children = []
const errors = []
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function launch(command, args, env = {}) {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', windowsHide: true })
  children.push(child)
  return child
}
async function ready(url, child) {
  for (let i = 0; i < 200; i++) {
    if (child.exitCode !== null) throw Error(`Test process exited: ${url}`)
    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* local startup */ }
    await delay(100)
  }
  throw Error(`Timed out starting ${url}`)
}

try {
  await fs.mkdir(output, { recursive: true })
  for (const port of [5196, 9246, 18986]) {
    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); throw Error(`Port ${port} is occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const backend = launch(path.join(repo, 'backend/.venv/Scripts/python.exe'), ['-B', '-c', "import uvicorn; from app.modules.game.development_demo import create_app; uvicorn.run(create_app(storage_root=r'" + path.join(output, 'isolated-storage') + "'), host='127.0.0.1', port=18986, access_log=False, log_level='error')"], { PYTHONPATH:path.join(repo,'backend'), GAME_ML_DEV_DEMO_ENABLED:'true', GAME_RESEARCHER_VERIFY_KEY:key, FRONTEND_URL:'http://127.0.0.1:5196' })
  await ready('http://127.0.0.1:18986/api/v1/health', backend)
  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5196', '--strictPort'], { VITE_API_BASE_URL: 'http://127.0.0.1:18986/api/v1' })
  const chrome = launch(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-allow-origins=*', '--remote-debugging-port=9246', `--user-data-dir=${profile}`, 'about:blank'])
  console.log('Starting isolated Vite and Chrome.')
  await Promise.all([ready('http://127.0.0.1:5196', vite), ready('http://127.0.0.1:9246/json', chrome)])
  console.log('Local browser ready.')
  const targets = await (await fetch('http://127.0.0.1:9246/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Browser debugger connection timed out')), 15000)
    socket.addEventListener('open', () => { clearTimeout(timer); resolve() }, { once: true })
    socket.addEventListener('error', () => { clearTimeout(timer); reject(Error('Browser debugger connection failed')) }, { once: true })
  })
  let id = 0
  const pending = new Map()
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const next = ++id
    const timer = setTimeout(() => { pending.delete(next); reject(Error(`Browser command timed out: ${method}`)) }, 20000)
    pending.set(next, { resolve, reject, timer })
    socket.send(JSON.stringify({ id: next, method, params }))
  })
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') {
      const error = message.params.exceptionDetails.text + ': ' + (message.params.exceptionDetails.exception?.description || '')
      errors.push(error)
      console.error(error)
    }
    if (message.method === 'Page.javascriptDialogOpening') void send('Page.handleJavaScriptDialog', { accept: true })
    if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId
      try {
        const body = await send('Fetch.getResponseBody', { requestId })
        const source = body.base64Encoded ? Buffer.from(body.body, 'base64').toString() : body.body
        const patched = source.replace('return {', 'return { callbacks: { postBoot: game => { window.__gameUiAudit = game; } },')
        assert.notEqual(source, patched, 'Test-only config interception failed')
        await send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/javascript' }], body: Buffer.from(patched).toString('base64') })
      } catch (error) { errors.push(String(error)); await send('Fetch.continueRequest', { requestId }) }
      return
    }
    if (!message.id) return
    const entry = pending.get(message.id)
    if (!entry) return
    pending.delete(message.id)
    clearTimeout(entry.timer)
    if (message.error) entry.reject(Error(JSON.stringify(message.error)))
    else entry.resolve(message.result)
  })
  async function evaluate(expression) {
    let result
    try { result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }) }
    catch (error) { throw Error(`${error.message}; expression=${expression}`) }
    if (result.exceptionDetails) throw Error(`${JSON.stringify(result.exceptionDetails)}; expression=${expression}`)
    return result.result.value
  }
  async function until(expression) {
    for (let i = 0; i < 200; i++) {
      if (await evaluate(`Boolean(${expression})`)) return
      await delay(100)
    }
    const diagnostics = await evaluate(`({scene:(${scene})?.sys.settings.key,objects:(${scene})?.children.list.length,active:window.__gameUiAudit?.loop.running})`)
    throw Error(`Timed out: ${expression}; diagnostics=${JSON.stringify(diagnostics)}; errors=${JSON.stringify(errors)}`)
  }
  const scene = 'window.__gameUiAudit?.scene.getScenes(true)[0]'

  const sid='00000000-0000-0000-0000-000000000099'
  const fixture={version:1,destination:'http://127.0.0.1:18986/api/v1',sessions:[{
    request:{student_id:'STU_999',concept_id:'linear_equations',learning_cycle_id:'00000000-0000-0000-0000-000000000088',assessment_phase:'pre_tutor',client_session_id:sid},
    mode:'drag_drop',created:false,writes:[{id:'synthetic-write',kind:'event',body:{game_session_id:sid,event_type:'GAME_STARTED',event_timestamp:'2026-10-22T00:00:00Z',event_payload:{}}}],
    completionRequested:false,completed:false,closed:false,error:'Failed to fetch'
  }]}
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`if(!localStorage.getItem('game.collection.pending.v1'))localStorage.setItem('game.collection.pending.v1',${JSON.stringify(JSON.stringify(fixture))})`})
  await send('Page.navigate',{url:'http://127.0.0.1:5196/'})
  await until(`[...document.querySelectorAll('.app-navigation button')].some(b=>b.textContent==='Equation Game')`)
  await evaluate(`[...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game').click()`)
  await until(`document.querySelector('.collection-gate')?.textContent.includes('accepts isolated test sessions only')`)
  assert.equal(await evaluate(`document.querySelector('.collection-gate button[type=submit]').disabled`),true)
  assert.equal(await evaluate(`[...document.querySelectorAll('.collection-gate button')].find(b=>b.textContent==='Retry / recover saved evidence').disabled`),true)
  assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1'))`),fixture)
  assert.equal(await evaluate(`document.querySelector('.phaser-game-container')`),null)
  await evaluate(`document.querySelector('.collection-gate a[href="/development-demo"]').click()`)
  await until(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Start Game')`)
  await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent==='Start Game').click()`)
  await until(`document.querySelector('canvas')`)
  assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1'))`),fixture)
  assert.equal(await evaluate(`location.pathname`),'/development-demo')
  await send('Page.navigate',{url:'http://127.0.0.1:5196/'})
  await until(`[...document.querySelectorAll('.app-navigation button')].some(b=>b.textContent==='Equation Game')`)
  await evaluate(`(()=>{const original=window.fetch.bind(window);window.fetch=(input,init)=>String(input).endsWith('/api/v1/health')?Promise.reject(new TypeError('Synthetic offline test')):original(input,init)})()`)
  await evaluate(`[...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game').click()`)
  await until(`document.querySelector('.collection-gate')?.textContent.includes('Cannot reach the normal Game backend')`)
  assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1'))`),fixture)
  assert.deepEqual(errors,[])
  await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({checks:['wrong-service identified','STU collection blocked on isolated server','queue unchanged before and after test-page navigation','correct Game page starts','offline status identified'],errors},null,2))
  console.log('PASS: backend routing, safe test-page navigation and unchanged pending evidence. '+output)
} finally {
  socket?.close()
  for(const child of children)child.kill('SIGTERM')
}
