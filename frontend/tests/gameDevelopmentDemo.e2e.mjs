/** Isolated local demo E2E: actual backend/model, synthetic tester, no research DB. */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const output = path.join(root, 'artifacts', 'development-demo-' + Date.now())
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
  async function point(expression) {
    await until(`${scene}?.cameras && (${expression})`)
    await evaluate(`(() => {
      const s=${scene}, o=${expression}, c=s.cameras.main;
      const m=o.getWorldTransformMatrix();
      const p=c.matrixCombined.transformPoint(m.tx,m.ty);
      const canvas=s.game.canvas, r=canvas.getBoundingClientRect();
      const y=r.top+p.y*r.height/canvas.height;
      window.scrollBy(0,y<80 ? y-80 : Math.max(0,y-window.innerHeight+90));
    })()`)
    await delay(180)
    await until(`${scene}?.cameras && (${expression})`)
    return evaluate(`(() => {
      const s=${scene},o=${expression},canvas=s.game.canvas;
      const m=o.getWorldTransformMatrix(),p=s.cameras.main.matrixCombined.transformPoint(m.tx,m.ty);
      s.game.scale.updateBounds();
      const b=canvas.getBoundingClientRect();
      return {x:b.left+p.x*b.width/canvas.width,y:b.top+p.y*b.height/canvas.height};
    })()`)
  }
  async function tap(expression, touch = false) {
    const p = await point(expression)
    if (touch) {
      await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p] })
      await delay(80)
      await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
    } else {
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...p })
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...p })
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...p })
    }
    await delay(60)
  }
  const findButton = label => `${scene}.children.list.find(o=>o.type==='Container' && o.list?.some(t=>t.text===${JSON.stringify(label)} || t.text?.startsWith(${JSON.stringify(label + '\n')})))`
  const card = type => `${scene}.children.list.find(o=>o.type==='Container' && o.list?.some(t=>t.text===${JSON.stringify(type)}))`
  const correctCard = `${scene}.operationButtons.find(b=>b.getData('choice').isCorrect)`
  async function enter(value, touch=false) {
    for (const digit of value) await tap(findButton(digit), touch)
  }

  await send('Browser.getVersion')
  console.log('Browser protocol connected.')
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Fetch.enable', { patterns:[{urlPattern:'*/src/game/phaser/GameConfig.ts*',requestStage:'Response'}] })
  await send('Emulation.setDeviceMetricsOverride', {width:1440,height:1100,deviceScaleFactor:1,mobile:false})
  await send('Page.navigate', {url:'http://127.0.0.1:5196/development-demo'})
  await until(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Start Game')`)
  await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent==='Start Game').click()`)
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  const reports = []
  for (const mode of ['Drag & Drop','Hangman']) {
    await tap(card(mode))
    await until(`${scene}?.session?.levels?.length===6`)
    for(let task=0;task<6;task++) {
      if(mode==='Hangman') {
        await until(`${scene}.keyButtons?.length===12`)
        await enter(await evaluate(`${scene}.currentVariant.finalAnswer`))
        await tap(`${scene}.submitButton`)
      } else {
        for(let step=0;step<12;step++) {
          await until(`${scene}.operationButtons?.some(b=>b.getData('choice').isCorrect)`)
          const oldStep=await evaluate(`${scene}.currentStepIndex`)
          await tap(correctCard)
          await until(`${scene}.hasAnsweredStepCorrectly`)
          await until(`${scene}.nextButton?.input?.enabled || ${scene}.currentStepIndex!==${oldStep} || document.querySelector('dialog[open]')`)
          if(await evaluate(`!!document.querySelector('dialog[open]')`))break
          if(await evaluate(`${scene}.currentStepIndex!==${oldStep}`))continue
          await tap(`${scene}.nextButton`)
          await until(`${scene}.session.levelIndex!==${task}`)
          break
        }
      }
      if(mode==='Hangman' && task<5) {
        await until(`${scene}.nextButton?.input?.enabled`)
        await tap(`${scene}.nextButton`)
      }
    }
    await until(`document.querySelector('dialog[open]')`)
    assert.ok(await evaluate(`document.querySelector('dialog').textContent.includes('DEMO_TEAM')`))
    assert.equal(await evaluate(`Object.values(localStorage).some(v=>v.includes('DEMO_TEAM'))`),false)
    await evaluate(`document.querySelector('dialog input[type=checkbox]').click();document.querySelector('dialog input[type=password]').value=${JSON.stringify(key)};document.querySelector('dialog form').requestSubmit()`)
    for(let i=0;i<750;i++) {
      if(await evaluate(`document.querySelectorAll('.game-ml-card progress').length===3`))break
      if(await evaluate(`!!document.querySelector('dialog [role=alert]')`))throw Error(await evaluate(`document.querySelector('dialog [role=alert]').textContent`))
      await delay(100)
    }
    assert.equal(await evaluate(`document.querySelectorAll('.game-ml-card progress').length`),3)
    assert.equal(await evaluate(`document.querySelector('.game-ml-card').textContent.includes('Development Demo')`),false)
    assert.ok(await evaluate(`document.querySelector('.game-ml-card').textContent.includes('Experimental Prediction')`))
    assert.equal(await evaluate(`document.querySelector('dialog input[type=password]').value`),'')
    const level = await evaluate(`document.querySelector('.game-ml-card__estimate h3').textContent`)
    const probabilities = await evaluate(`[...document.querySelectorAll('.game-ml-card progress')].map(p=>p.value)`)
    reports.push({mode,level,probabilities,classification:'DEVELOPMENT_DEMO_NOT_RESEARCH'})
    console.log(`${mode}: saved six tasks, key verified, real frozen model ${level}; three probabilities rendered.`)
    await evaluate(`document.querySelector('.game-ml-card').scrollIntoView({block:'center'})`)
    await delay(200)
    const capture=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})
    await fs.writeFile(path.join(output,mode==='Hangman'?'hangman.png':'drag-drop.png'),Buffer.from(capture.data,'base64'))
    await tap(findButton('Choose Another Game'))
    await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  }
  assert.deepEqual(errors,[])
  await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({reports,errors,source:'Actual isolated demo backend and frozen worker; synthetic development tester only'},null,2))
  console.log('PASS: isolated demo browser flow. '+output)
} finally {
  socket?.close()
  for(const child of children)child.kill('SIGTERM')
}
