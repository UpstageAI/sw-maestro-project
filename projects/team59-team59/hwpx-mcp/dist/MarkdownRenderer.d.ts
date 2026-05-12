import { HwpxDocument } from './HwpxDocument';
export declare class MarkdownRenderer {
    private doc;
    private sectionIndex;
    private currentIndex;
    private insertedCount;
    constructor(doc: HwpxDocument, sectionIndex: number, afterParagraphIndex: number);
    render(markdown: string): number;
    private insert;
    private extractSegments;
    private dominantStyle;
    private renderBlock;
}
