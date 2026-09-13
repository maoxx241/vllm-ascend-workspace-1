// node render_atlas.cjs <node_modules> [browser-executable]
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const modules = process.argv[2];
if (!modules) throw new Error('Pass the directory containing playwright and sharp.');
const {chromium} = require(path.join(modules, 'playwright'));
const sharp = require(path.join(modules, 'sharp'));
const root = __dirname;
for (const directory of ['png', 'evidence']) {
  fs.mkdirSync(path.join(root, directory), {recursive: true});
}

(async () => {
  const atlas = JSON.parse(fs.readFileSync(path.join(root, 'atlas.json'), 'utf8'));
  const browser = await chromium.launch({headless:true, ...(process.argv[3] ? {executablePath:process.argv[3]} : {})});
  try {
    const context = await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:2});
    const page = await context.newPage();
    const results = [];
    for(const diagram of atlas.pages) {
      await page.goto(pathToFileURL(path.join(root,'svg',diagram.slug+'.svg')).href);
      await page.evaluate(()=>document.fonts.ready);
      const errors = await page.evaluate(() => {
        const all=[];
        for(const t of document.querySelectorAll('text')) {
          const b=t.getBBox();
          const data=t.getAttribute('data-bounds');
          const [x,y,w,h]=data ? data.split(',').map(Number) : [0,0,1600,1000];
          if(b.x<x-2 || b.y<y-2 || b.x+b.width>x+w+2 || b.y+b.height>y+h+2)
            all.push({text:t.textContent,actual:{x:b.x,y:b.y,width:b.width,height:b.height},expected:{x,y,width:w,height:h}});
        }
        return all;
      });
      await page.screenshot({path:path.join(root,'png',diagram.slug+'.png')});
      results.push({slug:diagram.slug,overflows:errors});
      console.log(diagram.slug+': '+errors.length+' text bounds issues');
    }
    await page.setViewportSize({width:1680,height:1120});
    await page.goto(pathToFileURL(path.join(root,'index.html')).href);
    await page.evaluate(()=>document.fonts.ready);
    const indexCheck = await page.evaluate(()=>({sections:document.querySelectorAll('section').length,images:[...document.images].map(i=>({loaded:i.complete&&i.naturalWidth>0,alt:i.alt})),horizontalOverflow:document.documentElement.scrollWidth>innerWidth}));
    await page.screenshot({path:path.join(root,'evidence','index-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(root,'evidence','index-mobile.png')});
    const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    await context.close();
    const thumbs=[];
    for(let i=0;i<atlas.pages.length;i++) {
      const data=await sharp(path.join(root,'png',atlas.pages[i].slug+'.png')).resize(640,400).toBuffer();
      thumbs.push({input:data,left:(i%2)*640,top:Math.floor(i/2)*400});
    }
    await sharp({create:{width:1280,height:1600,channels:3,background:'#eef5fc'}}).composite(thumbs).png().toFile(path.join(root,'contact-sheet.png'));
    const report={date:'2026-09-14',diagrams:results,index:indexCheck,mobileOverflow};
    fs.writeFileSync(path.join(root,'evidence','render-check.json'),JSON.stringify(report,null,2)+'\n');
    if(results.some(r=>r.overflows.length)||indexCheck.horizontalOverflow||mobileOverflow||indexCheck.images.some(x=>!x.loaded))process.exitCode=1;
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
