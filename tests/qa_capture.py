import asyncio, json, os, sys
from playwright.async_api import async_playwright

async def run(base, out):
    os.makedirs(out, exist_ok=True)
    results = {'base': base, 'viewports': {}, 'console': [], 'page_errors': [], 'failed_requests': [], 'checks': {}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-gpu'])
        for name, w, h in [('desktop',1440,1000),('mobile',390,844),('short',375,667),('narrow',360,800),('wide-mobile',430,932)]:
            page = await browser.new_page(viewport={'width':w,'height':h}, device_scale_factor=1)
            page.on('console', lambda m: results['console'].append({'type':m.type,'text':m.text}) if m.type == 'error' else None)
            page.on('pageerror', lambda e: results['page_errors'].append(str(e)))
            page.on('requestfailed', lambda r: results['failed_requests'].append({'url':r.url,'failure':r.failure}))
            await page.goto(base, wait_until='networkidle')
            await page.wait_for_timeout(700)
            geom = await page.evaluate("""()=>({innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyScroll:document.body.scrollWidth,h1:document.querySelectorAll('h1').length,cta:[...document.querySelectorAll('.hero .button')].map(x=>{let r=x.getBoundingClientRect();return {text:x.textContent.trim(),top:r.top,bottom:r.bottom,w:r.width,h:r.height}}),heroImg:document.querySelector('.hero-media img').currentSrc,broken:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src)})""")
            results['viewports'][name] = geom
            if name in ('desktop','mobile'):
                await page.screenshot(path=f'{out}/{name}-full.png', full_page=True)
                await page.screenshot(path=f'{out}/{name}-hero.png', full_page=False)
            await page.close()
        page = await browser.new_page(viewport={'width':390,'height':844})
        await page.goto(base, wait_until='networkidle')
        await page.locator('button.access').evaluate("e=>e.click()")
        await page.wait_for_timeout(80)
        results['checks']['access_open'] = await page.locator('#access-panel').is_visible()
        await page.locator('[data-access="contrast"]').evaluate("e=>e.click()")
        results['checks']['contrast_class'] = await page.locator('body').evaluate("e=>e.classList.contains('high-contrast')")
        await page.locator('#access-close').evaluate("e=>e.click()")
        results['checks']['access_closed'] = not await page.locator('#access-panel').is_visible()
        await page.fill('#name','בדיקת QA')
        await page.fill('#phone','0501234567')
        await page.fill('#message','בדיקת טופס')
        try:
            async with page.expect_popup(timeout=5000) as pi:
                await page.click('form button[type=submit]')
            pop = await pi.value
            results['checks']['form_popup'] = pop.url
            await pop.close()
        except Exception as e:
            results['checks']['form_popup'] = 'ERROR:' + str(e)
        results['checks']['tel'] = await page.get_attribute('a.header-call','href')
        results['checks']['whatsapp'] = await page.get_attribute('a.whatsapp','href')
        results['checks']['anchors'] = await page.evaluate("""()=>[...document.querySelectorAll('a[href^="#"]')].map(a=>({href:a.getAttribute('href'),ok:!!document.querySelector(a.getAttribute('href'))}))""")
        await browser.close()
    with open(out+'/results.json','w') as f:
        json.dump(results,f,ensure_ascii=False,indent=2)
    print(json.dumps(results,ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(run(sys.argv[1],sys.argv[2]))
