// Puppeteer 测试 — 深圳地图 OD 流向图
import puppeteer from 'puppeteer';

const errors = [];
const warns = [];
const logs = [];

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox']
    });
    const page = await browser.newPage();

    page.on('console', msg => {
        const text = msg.text();
        if (msg.type() === 'error') errors.push(text);
        else if (msg.type() === 'warning') warns.push(text);
        else if (text.includes('Geo-OD') || text.includes('API') || text.includes('Error')) logs.push(text);
    });
    page.on('pageerror', err => errors.push('PAGE_ERROR: ' + err.message));

    try {
        console.log('=== Loading http://localhost:5000/ ===');
        await page.goto('http://localhost:5000/', {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        // 等待 GeoJSON 加载 + 地图渲染
        console.log('Waiting for GeoJSON + render...');
        await new Promise(r => setTimeout(r, 6000));

        const allCharts = await page.evaluate(() => {
            const cards = document.querySelectorAll('.chart-card');
            const results = [];
            cards.forEach(card => {
                const h3 = card.querySelector('h3');
                const chart = card.querySelector('.chart');
                const hasCanvas = chart ? chart.querySelector('canvas') !== null : false;
                const hasError = chart ? chart.innerHTML.includes('error-state') : false;
                const hasSvg = chart ? chart.querySelector('svg') !== null : false;
                results.push({
                    title: h3 ? h3.textContent.trim() : 'unknown',
                    id: chart ? chart.id : 'none',
                    hasCanvas: hasCanvas,
                    hasSvg: hasSvg,
                    hasError: hasError,
                    innerHTML_preview: chart ? chart.innerHTML.substring(0, 250) : 'N/A'
                });
            });
            return results;
        });

        console.log('\n=== All Charts Status ===');
        allCharts.forEach(c => {
            const ok = c.hasCanvas || c.hasSvg;
            const status = ok ? 'OK' : (c.hasError ? 'ERR' : '???');
            console.log(`  [${status}] ${c.title} (${c.id}) canvas=${c.hasCanvas} svg=${c.hasSvg}`);
            if (!ok) {
                console.log(`    innerHTML: ${c.innerHTML_preview}`);
            }
        });

        // Check map specifically — it uses SVG, not canvas (geo component)
        const mapState = await page.evaluate(() => {
            const dom = document.getElementById('chart-odlines');
            if (!dom) return {exists: false};
            const svgRoot = dom.querySelector('svg');
            const hasMap = svgRoot ? svgRoot.querySelector('g') !== null : false;
            const paths = svgRoot ? svgRoot.querySelectorAll('path').length : 0;
            return {
                exists: true,
                hasSvg: !!svgRoot,
                hasMapGroup: hasMap,
                pathCount: paths,
                hasError: dom.innerHTML.includes('error-state'),
                innerHTML_len: dom.innerHTML.length
            };
        });
        console.log('\n=== OD Map Chart ===');
        console.log(JSON.stringify(mapState, null, 2));

    } catch (e) {
        console.error('Test failed:', e.message);
    }

    console.log('\n=== Console Errors ===');
    const relevantErrors = errors.filter(e =>
        !e.includes('favicon') && !e.includes('shine')
    );
    if (relevantErrors.length === 0) console.log('  (none)');
    else relevantErrors.forEach(e => console.log('  [ERROR]', e));

    console.log('\n=== Geo-OD Logs ===');
    if (logs.length === 0) console.log('  (none)');
    else logs.forEach(l => console.log('  ', l));

    await browser.close();
})();
