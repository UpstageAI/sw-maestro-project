"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MarkdownRenderer = void 0;
const marked_1 = require("marked");
class MarkdownRenderer {
    constructor(doc, sectionIndex, afterParagraphIndex) {
        this.insertedCount = 0;
        this.doc = doc;
        this.sectionIndex = sectionIndex;
        this.currentIndex = afterParagraphIndex;
    }
    render(markdown) {
        const tokens = marked_1.Lexer.lex(markdown);
        for (const token of tokens) {
            this.renderBlock(token);
        }
        return this.insertedCount;
    }
    insert(text, charStyle, paraStyle) {
        const idx = this.doc.insertParagraph(this.sectionIndex, this.currentIndex, text);
        if (idx === -1)
            return -1;
        this.currentIndex = idx;
        this.insertedCount++;
        if (charStyle && Object.keys(charStyle).length > 0) {
            this.doc.applyCharacterStyle(this.sectionIndex, idx, 0, charStyle);
        }
        if (paraStyle && Object.keys(paraStyle).length > 0) {
            this.doc.applyParagraphStyle(this.sectionIndex, idx, paraStyle);
        }
        return idx;
    }
    extractSegments(tokens) {
        const segments = [];
        for (const token of tokens) {
            if (token.type === 'text') {
                segments.push({ text: token.text });
            }
            else if (token.type === 'strong') {
                const inner = token;
                const text = inner.tokens ? inner.tokens.map(t => t.text || '').join('') : inner.text;
                segments.push({ text, bold: true });
            }
            else if (token.type === 'em') {
                const inner = token;
                const text = inner.tokens ? inner.tokens.map(t => t.text || '').join('') : inner.text;
                segments.push({ text, italic: true });
            }
            else if (token.type === 'codespan') {
                segments.push({ text: token.text, code: true });
            }
        }
        return segments;
    }
    dominantStyle(segments) {
        const total = segments.reduce((acc, s) => acc + s.text.length, 0);
        if (total === 0)
            return {};
        const boldLen = segments.filter(s => s.bold).reduce((acc, s) => acc + s.text.length, 0);
        const italicLen = segments.filter(s => s.italic).reduce((acc, s) => acc + s.text.length, 0);
        const codeLen = segments.filter(s => s.code).reduce((acc, s) => acc + s.text.length, 0);
        const style = {};
        if (boldLen / total > 0.4)
            style.bold = true;
        if (italicLen / total > 0.4)
            style.italic = true;
        if (codeLen / total > 0.4)
            style.fontName = 'Courier New';
        return style;
    }
    renderBlock(token) {
        switch (token.type) {
            case 'heading': {
                const t = token;
                const fontSizeMap = { 1: 18, 2: 16, 3: 14 };
                const fontSize = fontSizeMap[t.depth] ?? 12;
                const text = t.tokens ? t.tokens.map(i => i.text || '').join('') : t.text;
                this.insert(text, { bold: true, fontSize });
                break;
            }
            case 'paragraph': {
                const t = token;
                const segments = this.extractSegments(t.tokens ?? []);
                const plainText = segments.map(s => s.text).join('');
                const charStyle = this.dominantStyle(segments);
                this.insert(plainText, charStyle);
                break;
            }
            case 'list': {
                const t = token;
                let num = typeof t.start === 'number' ? t.start : 1;
                for (const item of t.items) {
                    const prefix = t.ordered ? `${num}. ` : '• ';
                    const text = prefix + item.text;
                    this.insert(text, {}, { marginLeft: 20 });
                    if (t.ordered)
                        num++;
                }
                break;
            }
            case 'blockquote': {
                const t = token;
                for (const inner of t.tokens ?? []) {
                    if (inner.type === 'paragraph') {
                        const p = inner;
                        const text = p.tokens ? p.tokens.map(i => i.text || '').join('') : p.text;
                        this.insert(text, { italic: true }, { marginLeft: 30 });
                    }
                }
                break;
            }
            case 'code': {
                const t = token;
                for (const line of t.text.split('\n')) {
                    this.insert(line || ' ', { fontName: 'Courier New', fontSize: 10 });
                }
                break;
            }
            case 'hr': {
                this.insert('─'.repeat(30));
                break;
            }
            case 'space':
                break;
            default:
                break;
        }
    }
}
exports.MarkdownRenderer = MarkdownRenderer;
