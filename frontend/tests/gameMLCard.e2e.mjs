/** Isolated presentation tests. No backend, credentials, genuine records or API calls.
 * node --experimental-strip-types tests/gameMLCard.e2e.mjs
 * Only CDP replaces the served entry with the explicitly labelled test harness.
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { mockGameMLPrediction } from './fixtures/gameMLPrediction.fixture.ts'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const output = path.join(root, 'artifacts', 'game-ml-card-' + Date.now())
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-ml-card-'))
const children = []
const errors = []
const apiRequests = []
const researchModal = process.env.GAME_RESEARCH_MODAL_TEST === '1'
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function launch(command, args) {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, VITE_API_BASE_URL: 'http://127.0.0.1:9/api/v1' }, stdio: 'ignore', windowsHide: true })
  children.push(child)
  return child
}
async function ready(url, child) {
  for (let i = 0; i < 200; i++) {
    if (child.exitCode !== null) throw Error('Isolated browser process exited')
    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* local startup */ }
    await delay(100)
  }
  throw Error('Timed out starting isolated visual test')
}

try {
  await fs.mkdir(output, { recursive: true })
  for (const port of [5194, 9244]) {
    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); throw Error(`Port ${port} is occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5194', '--strictPort'])
  const chrome = launch(process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', [
    '--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*',
    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9244', `--user-data-dir=${profile}`, 'about:blank',
  ])
  await Promise.all([ready('http://127.0.0.1:5194', vite), ready('http://127.0.0.1:9244/json', chrome)])
  const targets = await (await fetch('http://127.0.0.1:9244/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Browser debugger timed out')), 15000)
    socket.addEventListener('open', () => { clearTimeout(timer); resolve() }, { once: true })
    socket.addEventListener('error', reject, { once: true })
  })
  let nextId = 0
  const pending = new Map()
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId
    const timer = setTimeout(() => { pending.delete(id); reject(Error(`Browser command timed out: ${method}`)) }, 20000)
    pending.set(id, { resolve, reject, timer })
    socket.send(JSON.stringify({ id, method, params }))
  })
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text)
    if (message.method === 'Network.requestWillBeSent' && new URL(message.params.request.url).pathname.startsWith('/api/v1/')) apiRequests.push(message.params.request.url)
    if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId
      try {
        const body = await send('Fetch.getResponseBody', { requestId })
        const source = body.base64Encoded ? Buffer.from(body.body, 'base64').toString() : body.body
        const patched = source.replace('/src/main.tsx', researchModal ? '/tests/fixtures/researcherMLVisualHarness.tsx' : '/tests/fixtures/gameMLVisualHarness.tsx')
        assert.notEqual(source, patched, 'Isolated test entry interception failed')
        await send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'text/html' }], body: Buffer.from(patched).toString('base64') })
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
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  async function loaded(scenario, label) {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(`Boolean(document.querySelector('main[data-ml-scenario="${scenario}"][data-ml-label="${label}"] .game-ml-card'))`)) return
      await delay(100)
    }
    throw Error('Card failed to render: ' + errors.join('; '))
  }
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Network.enable')
  await send('Network.setBlockedURLs', { urls: ['*://fonts.googleapis.com/*', '*://fonts.gstatic.com/*', '*/api/v1/*'] })
  if (researchModal) {
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `(() => {
      const realFetch=window.fetch.bind(window), rows=new Map();
      localStorage.clear(); sessionStorage.clear();
      window.__fixtureKey=crypto.randomUUID()+crypto.randomUUID();
      window.__verificationCalls=0; window.__cancelCalls=0;
      const scenario=new URLSearchParams(location.search).get('state');
      const reply=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
      window.fetch=async(input,init={})=>{
        const url=new URL(typeof input==='string'?input:input.url,location.href);
        if(!url.pathname.includes('/api/'))return realFetch(input,init);
        const body=init.body?JSON.parse(init.body):{};
        if(url.pathname.endsWith('/sessions')){rows.set(body.client_session_id,body);return reply({...body,game_session_id:body.client_session_id,status:'in_progress'});}
        if(url.pathname.endsWith('/events')||url.pathname.endsWith('/task-attempts'))return reply({});
        if(url.pathname.endsWith('/complete')){
          if(scenario==='pending'||scenario==='savefail')return reply({},503);
          const id=url.pathname.split('/').at(-2),row=rows.get(id);
          return reply({...row,game_session_id:id,status:'completed',completed_at:new Date().toISOString(),
            research_verification:{receipt:'s'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()}});
        }
        if(url.pathname.endsWith('/cancel')){window.__cancelCalls++;return reply({});}
        if(url.pathname.endsWith('/research-verification')){
          window.__verificationCalls++;
          if(body.researcher_key!==window.__fixtureKey)return reply({},401);
          if(scenario==='disabled')return reply({},503);
          if(scenario==='unapproved')return reply({},404);
          if(scenario==='rate')return new Response('{}',{status:429,headers:{'Retry-After':'60'}});
          if(scenario==='network')throw new TypeError('Synthetic network failure');
          const prediction=${JSON.stringify(mockGameMLPrediction('Intermediate'))};
          if(scenario==='malformed')prediction.probabilities={Beginner:1};
          if(scenario==='slow'||scenario==='cancel-busy')return new Promise(resolve=>{window.__resolvePrediction=()=>resolve(reply(prediction));});
          return reply(prediction);
        }
        return reply({},503);
      };
    })()` })
  }
  await send('Fetch.enable', { patterns: [{ urlPattern: 'http://127.0.0.1:5194/*', resourceType: 'Document', requestStage: 'Response' }] })
  const checks = []
  if (researchModal) {
    for (const width of [1440,390,320]) {
      await send('Emulation.setDeviceMetricsOverride', {width,height:1000,deviceScaleFactor:1,mobile:width!==1440})
      for (const scenario of ['ready','pending','savefail','wrong','disabled','unapproved','network','malformed','rate','slow','cancel-busy','cancel']) {
        await send('Page.navigate',{url:`http://127.0.0.1:5194/?state=${scenario}`})
        for(let i=0;i<100;i++){if(await evaluate(`Boolean(document.querySelector('main[data-scenario="${scenario}"][data-prepared=true]') && document.querySelector('.game-ml-card'))`))break;await delay(100);}
        assert.ok(await evaluate(`!!document.querySelector('.game-ml-card')`), `Scenario ${scenario}: ${errors.join('; ')}`)
        if (scenario==='pending'||scenario==='savefail') {
          assert.equal(await evaluate(`!!document.querySelector('dialog[open]')`),false)
          assert.equal(await evaluate('window.__verificationCalls'),0)
        } else {
          for(let i=0;i<100;i++){if(await evaluate(`!!document.querySelector('dialog[open]')`))break;await delay(50);}
          assert.equal(await evaluate(`document.querySelector('dialog h2').textContent`),'Researcher Verification')
          assert.equal(await evaluate(`document.activeElement.type`),'password')
          assert.equal(await evaluate(`document.querySelector('dialog').scrollWidth>document.querySelector('dialog').clientWidth+1`),false)
          if(scenario==='ready') {
            const tree=await send('Accessibility.getFullAXTree')
            assert.ok(tree.nodes.some(node=>node.role?.value==='dialog'&&node.name?.value==='Researcher Verification'))
            await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,nativeVirtualKeyCode:9})
            await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,nativeVirtualKeyCode:9})
            assert.equal(await evaluate(`document.activeElement.textContent`),'Cancel')
            await evaluate(`document.querySelector('dialog input[type=password]').focus()`)
            if(width===320) {
              await evaluate(`document.documentElement.style.fontSize='200%'`)
              assert.equal(await evaluate(`document.querySelector('dialog').scrollWidth>document.querySelector('dialog').clientWidth+1`),false)
              const enlarged=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})
              await fs.writeFile(path.join(output,'modal-320-text-200.png'),Buffer.from(enlarged.data,'base64'))
              await evaluate(`document.documentElement.style.fontSize=''`)
            }
          }
          if(scenario==='cancel') {
            await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27})
            await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27})
            await delay(100)
            assert.equal(await evaluate(`!!document.querySelector('dialog[open]')`),false)
            assert.equal(await evaluate('window.__verificationCalls'),0)
          } else {
            await evaluate(`document.querySelector('dialog input[type=checkbox]').click()`)
            await evaluate(`document.querySelector('dialog input[type=password]').value=${scenario==='wrong'?JSON.stringify('wrong-fixture-key'):'window.__fixtureKey'};document.querySelector('dialog form').requestSubmit()`)
            if(scenario==='slow'||scenario==='cancel-busy') {
              await delay(100)
              assert.equal(await evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true)
              await evaluate(scenario==='slow' ? `document.querySelector('#fixture-switch').click()` : `document.querySelector('dialog button[type=button]').click()`)
              await delay(200)
              await evaluate(`window.__resolvePrediction()`)
              await delay(150)
              assert.equal(await evaluate(`document.querySelectorAll('.game-ml-card progress').length`),0)
              if(scenario==='slow') assert.ok(await evaluate(`document.querySelector('dialog').textContent.includes('STU_998')`))
              else assert.equal(await evaluate(`!!document.querySelector('dialog[open]')`),false)
            } else {
              for(let i=0;i<100;i++){if(await evaluate(`Boolean(document.querySelector('.game-ml-card progress')||document.querySelector('dialog [role=alert]'))`))break;await delay(50);}
              if(scenario==='wrong') {
                assert.equal(await evaluate(`document.querySelector('dialog input[type=password]').value`),'')
                assert.ok(await evaluate(`document.querySelector('dialog [role=alert]').textContent.includes('not accepted')`))
                await evaluate(`document.querySelector('dialog input[type=password]').value=window.__fixtureKey;document.querySelector('dialog form').requestSubmit()`)
                for(let i=0;i<100;i++){if(await evaluate(`Boolean(document.querySelector('.game-ml-card progress'))`))break;await delay(50);}
              }
              if(scenario==='ready'||scenario==='wrong') {
                assert.equal(await evaluate(`document.querySelector('.game-ml-card__estimate h3').textContent`),'Intermediate')
                assert.equal(await evaluate(`!!document.querySelector('dialog[open]')`),false)
                assert.equal(await evaluate(`document.querySelector('dialog input[type=password]').value`),'')
              } else {
                assert.equal(await evaluate(`document.querySelectorAll('.game-ml-card progress').length`),0)
                if(scenario==='rate') assert.equal(await evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true)
              }
            }
          }
          if(scenario==='wrong') {
            // Screenshot the valid modal layout separately, without any key.
            await send('Page.reload'); await delay(300)
          }
        }
        const leaks=await evaluate(`Object.values(localStorage).concat(Object.values(sessionStorage)).some(value=>value.includes(window.__fixtureKey))`)
        assert.equal(leaks,false)
        const screenshot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})
        await fs.writeFile(path.join(output,`modal-${scenario}-${width}.png`),Buffer.from(screenshot.data,'base64'))
        checks.push({width,scenario})
      }
    }
  } else {
  for (const width of [1440, 390, 320]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width !== 1440 })
    for (const scenario of ['Beginner', 'Intermediate', 'Advanced', 'loading', 'unavailable', 'error', 'invalid', 'default']) {
      for (const label of [true, false]) {
        await send('Page.navigate', { url: `http://127.0.0.1:5194/?state=${scenario}&label=${label}` })
        await loaded(scenario, label)
        const dom = await evaluate(`(() => {
          const card=document.querySelector('.game-ml-card');
          return {title:card.querySelector('h2').textContent,body:card.textContent,
            experimental:!!card.querySelector('.game-ml-card__experimental'),busy:card.getAttribute('aria-busy'),
            estimated:card.querySelector('.game-ml-card__estimate h3')?.textContent,
            bars:[...card.querySelectorAll('progress')].map(p=>({value:p.value,max:p.max,name:p.getAttribute('aria-label'),text:p.getAttribute('aria-valuetext')})),
            alert:!!card.querySelector('[role=alert]'),
            overflow:card.scrollWidth>card.clientWidth+1 || document.documentElement.scrollWidth>innerWidth+1,
            labelled:document.getElementById(card.getAttribute('aria-labelledby'))?.textContent,
            mockLabel:document.body.textContent.includes('Visual test only — mock data, not a student prediction.')};
        })()`)
        assert.equal(dom.title, 'ML Model Estimate')
        assert.equal(dom.labelled, 'ML Model Estimate')
        assert.equal(dom.experimental, label)
        assert.equal(dom.overflow, false, `Overflow: ${scenario} at ${width}`)
        assert.equal(dom.mockLabel, true)
        if (['Beginner', 'Intermediate', 'Advanced'].includes(scenario)) {
          const prediction = mockGameMLPrediction(scenario)
          assert.equal(dom.estimated, scenario)
          assert.deepEqual(dom.bars.map(p=>p.value), Object.values(prediction.probabilities))
          assert.ok(dom.bars.every(p=>p.max===1 && p.name.endsWith('model-estimated probability') && p.text.endsWith('%')))
          if (scenario==='Intermediate') assert.deepEqual(dom.bars.map(p=>p.text), ['18%', '64.5%', '17.5%'])
          const ax = await send('Accessibility.getFullAXTree')
          assert.equal(ax.nodes.filter(node=>node.role?.value==='progressbar' && node.name?.value?.endsWith('model-estimated probability')).length, 3)
          if (width===320 && scenario==='Intermediate' && label) {
            await evaluate(`document.documentElement.style.fontSize='200%'`)
            assert.equal(await evaluate(`document.documentElement.scrollWidth>innerWidth+1 || document.querySelector('.game-ml-card').scrollWidth>document.querySelector('.game-ml-card').clientWidth+1`), false)
            const capture=await send('Page.captureScreenshot', {format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:await evaluate('document.documentElement.scrollHeight'),scale:1}})
            await fs.writeFile(path.join(output, 'mock-Intermediate-320-text-200.png'), Buffer.from(capture.data,'base64'))
            await evaluate(`document.documentElement.style.fontSize=''`)
          }
        } else {
          assert.equal(dom.bars.length, 0)
          assert.equal(dom.estimated, undefined)
          assert.equal(dom.busy, scenario==='loading' ? 'true' : 'false')
          assert.equal(dom.alert, scenario==='error')
          assert.ok(dom.body.includes(scenario==='loading' ? 'Preparing your estimate' : scenario==='error' ? 'Estimate could not be loaded' : 'Prediction unavailable'))
        }
        if ((label && scenario!=='invalid' && scenario!=='default') || (!label && scenario==='Advanced' && width===1440)) {
          const capture=await send('Page.captureScreenshot', {format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:await evaluate('document.documentElement.scrollHeight'),scale:1}})
          await fs.writeFile(path.join(output, `mock-${scenario}-${width}${label?'':'-label-hidden'}.png`), Buffer.from(capture.data,'base64'))
        }
        checks.push({width,scenario,label})
      }
    }
  }
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(apiRequests, [])
  await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify({checks,errors,apiRequests,mockDataOnly:true},null,2))
  console.log(`PASS: ${checks.length} isolated ${researchModal?'researcher-modal':'card'} cases, native accessibility tree, 200% text, no real API requests. Screenshots: ${output}`)
} finally {
  socket?.close()
  for (const child of children) child.kill('SIGTERM')
}
