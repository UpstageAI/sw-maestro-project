import { describe, it, expect } from 'vitest';
import JSZip from 'jszip';
import { HwpxDocument } from './HwpxDocument';
import { MarkdownRenderer } from './MarkdownRenderer';

/**
 * Build a minimal HWPX with a realistic secPr (A4 page, 8504 L/R margins).
 * Used to verify lineseg horzsize computation and absence of placeholders.
 */
async function buildHwpxWithSecPr(): Promise<Buffer> {
  const zip = new JSZip();

  zip.file(
    'Contents/header.xml',
    `<?xml version="1.0" encoding="UTF-8"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"><hh:docInfo><hh:title>T</hh:title></hh:docInfo></hh:head>`
  );

  // A4: width 59528, L/R margin 8504 each → expected text area horzsize = 42520
  const sectionXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"><hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="0"><hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0"><hp:pagePr landscape="0" width="59528" height="84188" gutterType="LEFT_ONLY"><hp:pageMar header="4252" footer="4252" left="8504" right="8504" top="5668" bottom="4252" gutter="0"/></hp:pagePr></hp:secPr><hp:t>seed</hp:t></hp:run></hp:p></hs:sec>`;

  zip.file('Contents/section0.xml', sectionXml);
  zip.file(
    '[Content_Types].xml',
    `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>`
  );

  return Buffer.from(await zip.generateAsync({ type: 'nodebuffer' }));
}

async function readSection(buffer: Buffer): Promise<string> {
  const zip = await JSZip.loadAsync(buffer);
  return (await zip.file('Contents/section0.xml')?.async('string')) ?? '';
}

describe('Lineseg layout — HWPX 표준 준수', () => {
  it('insertParagraph creates linesegarray with horzsize matching pagePr - pageMar', async () => {
    const buffer = await buildHwpxWithSecPr();
    const doc = await HwpxDocument.createFromBuffer('id', '/tmp/t.hwpx', buffer);

    doc.insertParagraph(0, 0, '본문 한 줄');

    const saved = await doc.save();
    const xml = await readSection(saved);

    // No "lineseg 미계산" placeholder
    expect(xml).not.toContain('horzsize="0"');

    // The inserted paragraph carries a real lineseg with computed horzsize
    expect(xml).toMatch(/<hp:linesegarray><hp:lineseg[^>]*horzsize="42520"[^>]*\/><\/hp:linesegarray>/);
    expect(xml).toMatch(/<hp:lineseg[^>]*flags="393216"/);
  });

  it('Markdown render of 23 paragraphs leaves zero placeholder linesegs', async () => {
    const buffer = await buildHwpxWithSecPr();
    const doc = await HwpxDocument.createFromBuffer('id', '/tmp/t.hwpx', buffer);

    const md = Array.from({ length: 23 }, (_, i) => `문단 ${i + 1}`).join('\n\n');
    const renderer = new MarkdownRenderer(doc, 0, 0);
    const inserted = renderer.render(md);
    expect(inserted).toBe(23);

    const saved = await doc.save();
    const xml = await readSection(saved);

    expect(xml).not.toContain('horzsize="0"');
    // All 23 inserts should produce a properly-sized lineseg
    const matches = xml.match(/<hp:lineseg[^>]*horzsize="42520"/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(23);
  });

  it('falls back to default horzsize when secPr is missing', async () => {
    const zip = new JSZip();
    zip.file(
      'Contents/header.xml',
      `<?xml version="1.0" encoding="UTF-8"?><hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"><hh:docInfo><hh:title>T</hh:title></hh:docInfo></hh:head>`
    );
    // Section without pagePr/pageMar
    zip.file(
      'Contents/section0.xml',
      `<?xml version="1.0" encoding="UTF-8"?><hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"><hp:p id="0"><hp:run><hp:t>seed</hp:t></hp:run></hp:p></hs:sec>`
    );
    zip.file(
      '[Content_Types].xml',
      `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>`
    );
    const buffer = Buffer.from(await zip.generateAsync({ type: 'nodebuffer' }));

    const doc = await HwpxDocument.createFromBuffer('id', '/tmp/t.hwpx', buffer);
    doc.insertParagraph(0, 0, 'fallback');
    const saved = await doc.save();
    const xml = await readSection(saved);

    expect(xml).not.toContain('horzsize="0"');
    // Default A4 minus standard margins
    expect(xml).toMatch(/<hp:lineseg[^>]*horzsize="42520"/);
  });
});
