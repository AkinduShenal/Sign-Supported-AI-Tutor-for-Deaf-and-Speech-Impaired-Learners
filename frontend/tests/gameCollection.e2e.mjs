/** Synthetic engineering verification only. Requires an explicitly configured
 * isolated loopback API + PostgreSQL. Uses real HTTP; no successful API mocks.
 * GAME_COLLECTION_API=http://127.0.0.1:8137/api/v1 node tests/gameCollection.e2e.mjs
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const api = process.env.GAME_COLLECTION_API
assert.ok(api && new URL(api).hostname === '127.0.0.1', 'An explicit isolated loopback API is required')
const output = path.join(root, 'artifacts', 'game-collection-' + Date.now())
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-collection-browser-'))
const children = [], errors = [], captures = [], sessions = [], actions = [], network = []
let socket, send
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const scene = 'window.__gameCollectionAudit?.scene.getScenes(true)[0]'
function launch(command, args, env = {}) {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
  child.on('error', e => errors.push(String(e)))
  child.stderr.on('data', data => { if (process.env.GAME_COLLECTION_VERBOSE) process.stderr.write(data) })
  children.push(child)
  return child
}
async function ready(url, child) {
  for (let n = 0; n < 200; n++) {
    if (child.exitCode !== null) throw Error(`Process exited while starting ${url}`)
    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* startup */ }
    await delay(100)
  }
  throw Error(`Startup timeout: ${url}`)
}
const source = `(() => {
  window.__collectionRequests = [];
  const original = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = String(typeof input === 'string' ? input : input.url);
    if (!url.startsWith(${JSON.stringify(api)})) return original(input, init);
    const body = init.body ? JSON.parse(init.body) : null;
    const entry = {url,body};
    if (body) window.__collectionRequests.push(entry);
    if (window.__failCollectionWrites && body) {entry.error='Synthetic network interruption';throw Error(entry.error);}
    const result = await original(input, init).catch(e=>{entry.error=String(e);throw e;});
    entry.response_status = result.status;
    if (window.__loseCollectionResponse && body?.event_type === 'ANSWER_CORRECT') {
      window.__loseCollectionResponse = false;
      throw Error('Synthetic response loss after actual server persistence');
    }
    return result;
  };
})()`
async function connect() {
  const targets = await (await fetch('http://127.0.0.1:9247/json')).json()
  const page = targets.find(target => target.type === 'page')
  socket = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  socket.addEventListener('close', () => {
    for (const entry of pending.values()) { clearTimeout(entry.timeout); entry.reject(Error('Browser connection closed')) }
    pending.clear()
  })
  send = (method, params = {}) => new Promise((resolve, reject) => {
    if (socket.readyState !== WebSocket.OPEN) { reject(Error('Browser connection is not open')); return }
    const next = ++id
    const timeout = setTimeout(() => { pending.delete(next); reject(Error(`CDP timeout: ${method}`)) }, 20000)
    pending.set(next, { resolve, reject, timeout })
    socket.send(JSON.stringify({ id: next, method, params }))
  })
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data)
    if (process.env.GAME_COLLECTION_VERBOSE) console.log('CDP', message.id || message.method)
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text)
    if (message.method?.startsWith('Network.')) network.push({method:message.method,params:message.params})
    if (message.method === 'Page.javascriptDialogOpening') void send('Page.handleJavaScriptDialog', { accept: true })
    if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId
      try {
        const response = await send('Fetch.getResponseBody', { requestId })
        const body = response.base64Encoded ? Buffer.from(response.body, 'base64').toString() : response.body
        const patched = body.replace('return {', 'return { callbacks: { postBoot: game => { window.__gameCollectionAudit = game; } },')
        assert.notEqual(body, patched, 'Test-only Phaser interception failed')
        await send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/javascript' }], body: Buffer.from(patched).toString('base64') })
      } catch (e) { errors.push(String(e)); await send('Fetch.continueRequest', { requestId }) }
      return
    }
    const entry = pending.get(message.id)
    if (!entry) return
    clearTimeout(entry.timeout); pending.delete(message.id)
    if (message.error) entry.reject(Error(JSON.stringify(message.error)))
    else entry.resolve(message.result)
  })
  console.log('Connected to browser target', page.id)
  await send('Browser.getVersion')
  await send('Runtime.enable'); await send('Page.enable')
  await send('Network.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', { source })
  await send('Fetch.enable', { patterns: [{ urlPattern: '*/src/game/phaser/GameConfig.ts*', requestStage: 'Response' }] })
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false })
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] })
  return page.id
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
  return result.result.value
}
async function until(expression, timeout = 25000) {
  const start = Date.now()
  let progress = start
  while (Date.now() - start < timeout) {
    if (await evaluate(`Boolean(${expression})`)) return
    if (timeout > 25000 && Date.now() - progress > 15000) {
      progress = Date.now()
      console.log('Waiting for acknowledged database writes:', await evaluate(`document.querySelector('.collection-gate')?.innerText`))
      const retry = button('Retry / recover saved evidence')
      if (await evaluate(`document.querySelector('.collection-gate')?.textContent.includes('Failed') && (${retry}) && !(${retry}).disabled`)) await evaluate(`(${retry}).click()`)
    }
    await delay(100)
  }
  const diagnostics = await evaluate(`({text:document.body.innerText,scene:(${scene})?.sys.settings.key,level:(${scene})?.session?.levelIndex,index:(${scene})?.currentIndex,step:(${scene})?.currentStepIndex,lastRequests:window.__collectionRequests?.slice(-4)})`)
  throw Error(`Timed out: ${expression}; ${JSON.stringify(diagnostics)}`)
}
const button = text => `[...document.querySelectorAll('.collection-gate button')].find(b=>b.textContent===${JSON.stringify(text)})`
async function choose(code) {
  await until(`document.querySelector('#collection-student') && !document.querySelector('#collection-student').disabled`)
  await evaluate(`(() => {const e=document.querySelector('#collection-student');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(code)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
  await delay(50)
  await evaluate(`${button('Set student')}.click()`)
}
async function end() {
  await until(`!document.querySelector('.collection-gate').textContent.includes('queued writes') || document.querySelector('.collection-gate').textContent.includes('Saved')`)
  await evaluate(`document.querySelector('.collection-gate input[type=checkbox]').click()`)
  await until(`!${button('End collection / switch learner')}.disabled`)
  await evaluate(`${button('End collection / switch learner')}.click()`)
  await until(`document.querySelector('#collection-student')`)
}
async function tap(expression) {
  await until(`${scene}?.cameras && (${expression})?.input?.enabled`)
  await evaluate(`(() => {const s=${scene},o=${expression},m=o.getWorldTransformMatrix(),p=s.cameras.main.matrixCombined.transformPoint(m.tx,m.ty),c=s.game.canvas,r=c.getBoundingClientRect();const y=r.top+p.y*r.height/c.height;window.scrollBy(0,y<80?y-80:Math.max(0,y-innerHeight+90));})()`)
  await delay(70)
  const point = await evaluate(`(() => {const s=${scene},o=${expression},m=o.getWorldTransformMatrix(),p=s.cameras.main.matrixCombined.transformPoint(m.tx,m.ty),c=s.game.canvas,r=c.getBoundingClientRect();s.game.scale.updateBounds();return {x:r.left+p.x*r.width/c.width,y:r.top+p.y*r.height/c.height};})()`)
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...point })
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point })
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point })
  await delay(80)
}
const find = label => `${scene}.children.list.find(o=>o.type==='Container'&&o.list?.some(t=>t.text===${JSON.stringify(label)}||t.text?.startsWith(${JSON.stringify(label + '\n')})))`
async function start(mode) {
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  await tap(find(mode === 'drag_drop' ? 'Drag & Drop' : 'Hangman'))
  await until(`${scene}?.session?.levels.length===6 && (${mode === 'drag_drop' ? `${scene}.operationButtons?.length>0` : `${scene}.keyButtons?.length===12`})`)
  const row = await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>!s.closed)`)
  sessions.push({ id: row.request.client_session_id, student: row.request.student_id, mode })
  return row.request.client_session_id
}
async function answer(mode, correct) {
  const action = await evaluate(`(() => {const s=${scene},v=${mode === 'drag_drop' ? 's.currentLevel' : 's.currentVariant'};return {session:JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(r=>!r.closed).request.client_session_id,task:v.variantId,step:${mode === 'drag_drop' ? 's.currentStepIndex' : '0'},correct:${correct},response:${mode === 'drag_drop' ? `s.operationButtons.find(b=>${correct ? '' : '!'}b.getData('choice').isCorrect).getData('choice').label` : correct ? 'v.finalAnswer' : "'999'"}}})()`)
  actions.push(action)
  if (mode === 'drag_drop') await tap(`${scene}.operationButtons.find(b=>${correct ? '' : '!'}b.getData('choice').isCorrect)`)
  else {
    await until(`!${scene}.locked`)
    for (const digit of action.response) await tap(find(digit))
    await tap(`${scene}.submitButton`)
  }
}
async function complete(mode, id) {
  for (let count = 0; count < 45; count++) {
    if (await evaluate(`${scene}.showSummary`)) break
    if (await evaluate(`${scene}.nextButton?.input?.enabled`)) { await tap(`${scene}.nextButton`); continue }
    if (await evaluate(mode === 'drag_drop' ? `${scene}.hasAnsweredStepCorrectly` : `${scene}.locked`)) { await delay(250); continue }
    const previous = await evaluate(mode === 'drag_drop' ? `({level:${scene}.session.levelIndex,step:${scene}.currentStepIndex})` : `({level:${scene}.currentIndex})`)
    await answer(mode, true)
    await until(`${scene}.showSummary || ${scene}.nextButton?.input?.enabled || ${mode === 'drag_drop' ? `${scene}.currentStepIndex!==${previous.step} || ${scene}.session.levelIndex!==${previous.level}` : `${scene}.currentIndex!==${previous.level}`} || ${scene}.session.stars.length===6 || JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>s.request.client_session_id===${JSON.stringify(id)}).completed`)
    if (await evaluate(`${scene}.session.stars.length===6`)) break
  }
  await until(`JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>s.request.client_session_id===${JSON.stringify(id)}).completed`, 300000)
  await until(`${scene}.showSummary`)
  console.log(`Completed ${mode} ${id}`)
}
async function capture() { captures.push(...await evaluate('window.__collectionRequests || []')) }

try {
  await fs.mkdir(output, { recursive: true })
  for (const port of [5197, 9247]) {
    let occupied = false
    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); occupied = true } catch { /* unused */ }
    assert.equal(occupied, false, `Port ${port} already occupied`)
  }
  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5197', '--strictPort'], { VITE_API_BASE_URL: api })
  const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-allow-origins=*', '--remote-debugging-port=9247', `--user-data-dir=${profile}`, 'about:blank'])
  await Promise.all([ready('http://127.0.0.1:5197', vite), ready('http://127.0.0.1:9247/json', chrome)])
  let page = await connect()
  await send('Page.navigate', { url: 'http://127.0.0.1:5197' })
  await choose('bad-code')
  await until(`document.querySelector('[role=alert]')?.textContent.includes('STU_')`)
  assert.equal(await evaluate('!!document.querySelector("canvas")'), false)
  for (const mode of ['drag_drop', 'hangman']) {
    await choose('STU_001')
    await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
    const full = await start(mode)
    await answer(mode, false)
    await tap(`${scene}.hintButton`)
    await evaluate('window.__loseCollectionResponse=true')
    await complete(mode, full)
    await end()
    await choose('STU_001')
    const partial = await start(mode)
    await evaluate('window.__failCollectionWrites=true')
    await answer(mode, false)
    await tap(`${scene}.hintButton`)
    await until(`document.querySelector('.collection-gate').textContent.includes('Failed')`)
    const before = await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>s.request.client_session_id===${JSON.stringify(partial)})`)
    assert.ok(before.writes.length >= 3)
    await evaluate('document.querySelector(".collection-gate input[type=checkbox]").click()')
    assert.equal(await evaluate(`${button('End collection / switch learner')}.disabled`), true)
    await capture()
    if (mode === 'drag_drop') await send('Page.reload', { ignoreCache: true })
    else {
      await send('Target.closeTarget', { targetId: page })
      socket.close()
      await fetch('http://127.0.0.1:9247/json/new?about:blank', { method: 'PUT' })
      page = await connect()
      await send('Page.navigate', { url: 'http://127.0.0.1:5197' })
    }
    await choose('STU_002')
    await until(`document.querySelector('[role=alert]')?.textContent.includes('previous learner')`)
    assert.equal(await evaluate('!!document.querySelector("canvas")'), false)
    await choose('STU_001')
    assert.equal(await evaluate('!!document.querySelector("canvas")'), false)
    const restored = await evaluate(`JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>s.request.client_session_id===${JSON.stringify(partial)})`)
    assert.deepEqual(restored.writes, before.writes)
    await evaluate(`${button('Retry / recover saved evidence')}.click()`)
    await until(`JSON.parse(localStorage.getItem('game.collection.pending.v1')).sessions.find(s=>s.request.client_session_id===${JSON.stringify(partial)}).writes.length===0`)
    await end()
    await choose('STU_002')
    const second = await start(mode)
    await answer(mode, false)
    await tap(`${scene}.hintButton`)
    await complete(mode, second)
    await end()
    console.log(`PASS ${mode}: wrong/correct/hint, real persistence, interruption recovery, learner switch`)
  }
  await capture()
  assert.deepEqual(errors, [])
  const result = { kind: 'synthetic_engineering_only', sessions, actions, captures, errors, browserProfile: profile, checks: ['invalid identity blocked', 'two complete modes for both assigned codes', 'lost server response replay', 'network interruption', 'refresh recovery', 'tab closure recovery', 'unchanged pending IDs and payloads', 'unsaved switching blocked', 'partial sessions preserved'] }
  await fs.writeFile(path.join(output, 'browser-evidence.json'), JSON.stringify(result, null, 2))
  console.log(`PASS browser collection. Reconcile PostgreSQL and CSV separately. Evidence: ${output}`)
} catch (error) {
  try { await capture(); const shot = await send('Page.captureScreenshot'); await fs.writeFile(path.join(output, 'failure.png'), Buffer.from(shot.data, 'base64')) } catch { /* retain available diagnostics */ }
  await fs.writeFile(path.join(output, 'failure.json'), JSON.stringify({ error: String(error), errors, sessions, actions, captures, network }, null, 2))
  throw error
} finally {
  socket?.close()
  for (const child of children) child.kill('SIGTERM')
}
