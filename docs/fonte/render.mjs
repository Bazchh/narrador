// Renderiza um HTML em PDF A4 com rodapé e numeração, usando o Chrome instalado.
// Uso: node render.mjs <entrada.html> <saida.pdf> "<texto do rodapé>"
import puppeteer from 'puppeteer-core';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const [entrada, saida, rodape = ''] = process.argv.slice(2);
if (!entrada || !saida) {
  console.error('uso: node render.mjs <entrada.html> <saida.pdf> "<rodapé>"');
  process.exit(1);
}
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const browser = await puppeteer.launch({ executablePath: chrome, headless: true });
const page = await browser.newPage();
await page.goto(pathToFileURL(resolve(entrada)).href, { waitUntil: 'networkidle0' });
await page.pdf({
  path: resolve(saida),
  format: 'A4',
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: `<div style="width:100%;margin:0 16mm;font-family:'Segoe UI',Arial,sans-serif;font-size:8pt;color:#5b6577;display:flex;justify-content:space-between;border-top:1px solid #d7dde8;padding-top:4px">
      <span>${rodape}</span><span>página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>`,
  margin: { top: '16mm', bottom: '18mm', left: '16mm', right: '16mm' },
});
await browser.close();
console.log('ok', saida);
