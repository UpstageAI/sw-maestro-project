import JSZip from 'jszip';
import { HwpxContent, HwpxParagraph, TextRun, CharacterStyle, ParagraphStyle, HwpxTable, TableCell, PageSettings, Footnote, Endnote, Memo, ColumnDef, CharShape, ParaShape } from './types';
type DocumentFormat = 'hwpx' | 'hwp';
export interface ImagePositionOptions {
    /** Position type: 'inline' (flows with text like a character) or 'floating' (positioned relative to anchor) */
    positionType?: 'inline' | 'floating';
    /** Vertical reference point: 'para' (paragraph), 'paper' (page) */
    vertRelTo?: 'para' | 'paper';
    /** Horizontal reference point: 'column', 'para' (paragraph), 'paper' (page) */
    horzRelTo?: 'column' | 'para' | 'paper';
    /** Vertical alignment: 'top', 'center', 'bottom' */
    vertAlign?: 'top' | 'center' | 'bottom';
    /** Horizontal alignment: 'left', 'center', 'right' */
    horzAlign?: 'left' | 'center' | 'right';
    /** Vertical offset from anchor in points */
    vertOffset?: number;
    /** Horizontal offset from anchor in points */
    horzOffset?: number;
    /** Text wrap mode */
    textWrap?: 'top_and_bottom' | 'square' | 'tight' | 'behind_text' | 'in_front_of_text' | 'none';
}
export interface DocumentChunk {
    id: string;
    text: string;
    startOffset: number;
    endOffset: number;
    sectionIndex: number;
    elementType: 'paragraph' | 'table' | 'mixed';
    elementIndex?: number;
    tableIndex?: number;
    cellPosition?: {
        row: number;
        col: number;
    };
    metadata: {
        charCount: number;
        wordCount: number;
        hasTable: boolean;
        headingLevel?: number;
    };
}
export interface PositionIndexEntry {
    id: string;
    type: 'heading' | 'paragraph' | 'table' | 'image';
    text: string;
    sectionIndex: number;
    elementIndex: number;
    offset: number;
    level?: number;
    tableInfo?: {
        tableIndex: number;
        rows: number;
        cols: number;
    };
}
export declare class HwpxDocument {
    private _id;
    private _path;
    private _zip;
    private _content;
    private _isDirty;
    private _format;
    private _undoStack;
    private _redoStack;
    private _pendingTextReplacements;
    private _pendingDirectTextUpdates;
    private _pendingTableCellUpdates;
    private _pendingNestedTableInserts;
    private _pendingImageInserts;
    private _pendingCellImageInserts;
    private _pendingTableInserts;
    private _tableInsertCounter;
    private _pendingImageDeletes;
    private _pendingTableDeletes;
    private _pendingParagraphDeletes;
    private _pendingCellMerges;
    private _pendingCellSplits;
    private _pendingHangingIndents;
    private _pendingTableCellHangingIndents;
    private _pendingParagraphInserts;
    private _pendingParagraphStyles;
    private _pendingCharacterStyles;
    private _pendingTableRowInserts;
    private _pendingTableRowDeletes;
    private _pendingTableColumnInserts;
    private _pendingTableColumnDeletes;
    private _pendingParagraphCopies;
    private _pendingParagraphMoves;
    private _pendingHeaderUpdates;
    private _pendingFooterUpdates;
    private _charPrCache;
    private _originalCharPrCount?;
    private constructor();
    private static readonly NESTED_CHECK_LOOKBACK;
    private static readonly SEARCH_SKIP_OFFSET;
    /**
     * Find the closing tag position using balanced bracket matching.
     * Handles nested elements of the same type correctly.
     * @param xml The XML string to search in
     * @param startPos Position right after the opening tag
     * @param openTag Opening tag pattern (e.g., '<hp:tbl')
     * @param closeTag Closing tag (e.g., '</hp:tbl>')
     * @returns Position after the closing tag, or -1 if not found
     */
    private static findClosingTagPosition;
    static createFromBuffer(id: string, path: string, data: Buffer): Promise<HwpxDocument>;
    static createNew(id: string, title?: string, creator?: string): HwpxDocument;
    get id(): string;
    get path(): string;
    get format(): DocumentFormat;
    get isDirty(): boolean;
    get zip(): JSZip | null;
    get content(): HwpxContent;
    private saveState;
    private serializeContent;
    private deserializeContent;
    canUndo(): boolean;
    canRedo(): boolean;
    undo(): boolean;
    redo(): boolean;
    /**
     * Clear all pending operation arrays.
     * Called by undo/redo to prevent memory/XML desync.
     */
    private clearAllPendingArrays;
    /**
     * Mark document as modified and invalidate agentic reading cache.
     * Call this after any modification that changes document structure or content.
     */
    private markModified;
    getSerializableContent(): object;
    getAllText(): string;
    getStructure(): object;
    private findParagraphByPath;
    getParagraphs(sectionIndex?: number): Array<{
        section: number;
        index: number;
        text: string;
        style?: ParagraphStyle;
    }>;
    getParagraph(sectionIndex: number, paragraphIndex: number): {
        text: string;
        runs: TextRun[];
        style?: ParagraphStyle;
    } | null;
    updateParagraphText(sectionIndex: number, elementIndex: number, runIndex: number, text: string): void;
    updateParagraphRuns(sectionIndex: number, elementIndex: number, runs: TextRun[]): void;
    /**
     * Update paragraph text while preserving the style structure of existing runs.
     *
     * Strategy:
     * - If new text is shorter/equal: distribute text across existing runs proportionally
     * - If new text is longer: extend the last run
     * - Preserves charPrIDRef of each run
     *
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @param newText New text content
     * @returns true if successful, false otherwise
     */
    updateParagraphTextPreserveStyles(sectionIndex: number, elementIndex: number, newText: string): boolean;
    insertParagraph(sectionIndex: number, afterElementIndex: number, text?: string): number;
    deleteParagraph(sectionIndex: number, elementIndex: number): boolean;
    appendTextToParagraph(sectionIndex: number, elementIndex: number, text: string): void;
    applyCharacterStyle(sectionIndex: number, elementIndex: number, runIndex: number, style: Partial<CharacterStyle>): void;
    getCharacterStyle(sectionIndex: number, elementIndex: number, runIndex?: number): CharacterStyle | CharacterStyle[] | null;
    applyParagraphStyle(sectionIndex: number, elementIndex: number, style: Partial<ParagraphStyle>): void;
    getParagraphStyle(sectionIndex: number, elementIndex: number): ParagraphStyle | null;
    /**
     * Set hanging indent on a paragraph.
     * In HWPML, hanging indent uses:
     * - intent: negative value (pulls first line left)
     * - left: positive value (base left margin for other lines)
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @param indentPt Indent amount in points (positive value)
     * @returns true if successful, false otherwise
     */
    setHangingIndent(sectionIndex: number, elementIndex: number, indentPt: number): boolean;
    /**
     * Get hanging indent value for a paragraph.
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @returns Indent value in points, 0 if no hanging indent, null if invalid indices
     */
    getHangingIndent(sectionIndex: number, elementIndex: number): number | null;
    /**
     * Remove hanging indent from a paragraph.
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @returns true if successful, false otherwise
     */
    removeHangingIndent(sectionIndex: number, elementIndex: number): boolean;
    /**
     * Load character property cache from header.xml.
     * Maps charPr id to font size in pt.
     */
    private loadCharPrCache;
    /**
     * Get font size from charPr id.
     * @param charPrId Character property ID
     * @returns Font size in pt, or undefined if not found
     */
    getFontSizeFromCharPrId(charPrId: number): Promise<number | undefined>;
    /**
     * Get font size of a paragraph from XML.
     * Reads charPrIDRef from the first run in the paragraph.
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @returns Font size in pt, or undefined if not found
     */
    getParagraphFontSize(sectionIndex: number, elementIndex: number): Promise<number | undefined>;
    /**
     * Get font size of a paragraph in a table cell from XML.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @returns Font size in pt, or undefined if not found
     */
    getTableCellParagraphFontSize(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number): Promise<number | undefined>;
    /**
     * Automatically set hanging indent based on detected marker in paragraph text.
     * Uses HangingIndentCalculator to detect markers like "○ ", "1. ", "가. " etc.
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @param fontSize Font size in pt (if not provided, reads from document)
     * @returns Calculated indent value in pt, or 0 if no marker detected
     */
    setAutoHangingIndent(sectionIndex: number, elementIndex: number, fontSize?: number): number;
    /**
     * Automatically set hanging indent with dynamic font size from document.
     * Async version that reads actual font size from the document.
     * @param sectionIndex Section index
     * @param elementIndex Paragraph element index
     * @param fallbackFontSize Fallback font size in pt if document font size not found (default: 10)
     * @returns Calculated indent value in pt, or 0 if no marker detected
     */
    setAutoHangingIndentAsync(sectionIndex: number, elementIndex: number, fallbackFontSize?: number): Promise<number>;
    /**
     * Set hanging indent on a paragraph inside a table cell.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @param indentPt Indent value in points (positive)
     * @returns true if successful, false otherwise
     */
    setTableCellHangingIndent(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number, indentPt: number): boolean;
    /**
     * Get hanging indent value for a paragraph inside a table cell.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @returns Indent value in points, 0 if no hanging indent, null if invalid indices
     */
    getTableCellHangingIndent(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number): number | null;
    /**
     * Remove hanging indent from a paragraph inside a table cell.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @returns true if successful, false otherwise
     */
    removeTableCellHangingIndent(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number): boolean;
    /**
     * Automatically set hanging indent on a paragraph inside a table cell
     * based on detected marker in the text.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @param fontSize Font size in pt (default: 10)
     * @returns Calculated indent value in pt, or 0 if no marker detected
     */
    setTableCellAutoHangingIndent(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number, fontSize?: number): number;
    /**
     * Automatically set hanging indent on a paragraph inside a table cell
     * with dynamic font size from document.
     * Async version that reads actual font size from the document.
     * @param sectionIndex Section index
     * @param tableIndex Table index within section
     * @param row Row index (0-based)
     * @param col Column index (0-based)
     * @param paragraphIndex Paragraph index within cell (0-based)
     * @param fallbackFontSize Fallback font size in pt if document font size not found (default: 10)
     * @returns Calculated indent value in pt, or 0 if no marker detected
     */
    setTableCellAutoHangingIndentAsync(sectionIndex: number, tableIndex: number, row: number, col: number, paragraphIndex: number, fallbackFontSize?: number): Promise<number>;
    private findTable;
    getTables(): Array<{
        section: number;
        index: number;
        rows: number;
        cols: number;
    }>;
    /**
     * Get table map with headers - maps table indices to their header paragraphs
     * Returns array of table info including the header text from the preceding paragraph
     */
    getTableMap(): Array<{
        table_index: number;
        section_index: number;
        header: string;
        rows: number;
        cols: number;
        is_empty: boolean;
        first_row_preview: string[];
    }>;
    /**
     * Check if a table is empty or contains only placeholder text
     */
    private isTableEmpty;
    /**
     * Find tables that are empty or contain only placeholders
     */
    findEmptyTables(): Array<{
        table_index: number;
        section_index: number;
        header: string;
        rows: number;
        cols: number;
    }>;
    /**
     * Get tables within a specific section
     */
    getTablesBySection(sectionIndex: number): Array<{
        table_index: number;
        local_index: number;
        header: string;
        rows: number;
        cols: number;
        is_empty: boolean;
    }>;
    /**
     * Find tables by header text (partial match, case-insensitive)
     */
    findTableByHeader(searchText: string): Array<{
        table_index: number;
        section_index: number;
        header: string;
        rows: number;
        cols: number;
        is_empty: boolean;
        first_row_preview: string[];
    }>;
    /**
     * Get summary of multiple tables by index range
     */
    getTablesSummary(startIndex?: number, endIndex?: number): Array<{
        table_index: number;
        section_index: number;
        header: string;
        size: string;
        is_empty: boolean;
        content_preview: string;
    }>;
    /**
     * Find cells by label text and return the adjacent cell position.
     * Useful for form-like documents where labels identify input fields.
     * @param labelText - The label text to search for (case-insensitive, partial match)
     * @param direction - Direction to find target cell: 'right' (default) or 'down'
     * @returns Array of found positions with label and target cell info
     */
    findCellByLabel(labelText: string, direction?: 'right' | 'down'): Array<{
        tableIndex: number;
        sectionIndex: number;
        labelRow: number;
        labelCol: number;
        targetRow: number;
        targetCol: number;
        targetCellText: string;
    }>;
    /**
     * Fill table cells using path-based mappings (jkf87 style).
     * Path format: "labelText > direction" or chained "labelText > dir > dir"
     * @param mappings - Object mapping paths to values, e.g., { "이름: > right": "홍길동", "합계 > down > down": "1000" }
     * @returns Object with success count, failed paths, and details
     */
    fillByPath(mappings: Record<string, string>): {
        success: number;
        failed: string[];
        details: Array<{
            path: string;
            tableIndex: number;
            row: number;
            col: number;
            previousValue: string;
            newValue: string;
        }>;
    };
    /**
     * Resolve a path string to a cell position.
     * Path format: "labelText > direction" or chained "labelText > dir > dir"
     * Directions: right, left, up, down
     * @param path - Path string like "이름: > right" or "합계 > down > down"
     * @returns Cell position or null if not found
     */
    private resolvePathToPosition;
    /**
     * Get context around a specific cell (neighboring cells' content).
     * Useful for understanding a cell's position and meaning in a table.
     * @param tableIndex - Global table index
     * @param row - Row index (0-based)
     * @param col - Column index (0-based)
     * @param depth - How many cells in each direction to include (default: 1)
     * @returns Object with center cell and neighboring cells' content
     */
    getCellContext(tableIndex: number, row: number, col: number, depth?: number): {
        center: string;
        [key: string]: string | undefined;
    } | null;
    /**
     * Batch fill a table with 2D array data.
     * Useful for filling multiple cells at once from structured data.
     * @param tableIndex - Global table index
     * @param data - 2D array of strings to fill (row-major order)
     * @param startRow - Starting row index (default: 0)
     * @param startCol - Starting column index (default: 0)
     * @returns Object with success count and any out-of-bounds cells
     */
    batchFillTable(tableIndex: number, data: string[][], startRow?: number, startCol?: number): {
        success: number;
        outOfBounds: Array<{
            row: number;
            col: number;
            value: string;
        }>;
        updated: Array<{
            row: number;
            col: number;
            previousValue: string;
            newValue: string;
        }>;
    };
    /**
     * Convert global table index to section and local index
     * @param globalTableIndex - Global table index (0-based across all sections)
     * @returns Object with section_index and local_index, or null if not found
     */
    convertGlobalToLocalTableIndex(globalTableIndex: number): {
        section_index: number;
        local_index: number;
    } | null;
    /**
     * Get document outline - hierarchical structure showing headers and their associated tables
     */
    getDocumentOutline(): Array<{
        type: 'section' | 'heading' | 'table' | 'paragraph';
        level: number;
        text: string;
        section_index: number;
        table_index?: number;
        element_index: number;
    }>;
    /**
     * Convert a global table index to element index in its section
     * @param tableIndex - Global table index (0-based across all sections)
     * @returns Object with section_index and element_index, or null if not found
     */
    getElementIndexForTable(tableIndex: number): {
        section_index: number;
        element_index: number;
        table_info: {
            rows: number;
            cols: number;
            header: string;
        };
    } | null;
    /**
     * Find element index of a paragraph containing specific text
     * @param searchText - Text to search for (partial match, case-insensitive)
     * @param sectionIndex - Optional: limit search to specific section
     * @returns Array of matching positions with context
     */
    findParagraphByText(searchText: string, sectionIndex?: number): Array<{
        section_index: number;
        element_index: number;
        text: string;
        context_before: string;
        context_after: string;
    }>;
    /**
     * Get context around an element index (useful for verifying insertion point)
     * @param sectionIndex - Section index
     * @param elementIndex - Element index
     * @param contextRange - Number of elements before/after to include (default: 2)
     */
    getInsertContext(sectionIndex: number, elementIndex: number, contextRange?: number): {
        target_element: {
            type: string;
            text: string;
        };
        elements_before: Array<{
            type: string;
            text: string;
            element_index: number;
        }>;
        elements_after: Array<{
            type: string;
            text: string;
            element_index: number;
        }>;
        recommended_insert_after: number;
    } | null;
    /**
     * Find insertion position by searching for a header/title text
     * Returns position right after the found paragraph (good for inserting content under a header)
     * @param headerText - Text to search for in paragraph headers
     */
    /**
     * Find insertion position after header/text.
     * @param headerText - Text to search for
     * @param searchIn - Where to search: 'paragraphs', 'table_cells', or 'all' (default)
     */
    findInsertPositionAfterHeader(headerText: string, searchIn?: 'paragraphs' | 'table_cells' | 'all'): {
        section_index: number;
        element_index: number;
        insert_after: number;
        header_found: string;
        found_in: 'paragraph' | 'table_cell';
        table_info?: {
            table_index: number;
            row: number;
            col: number;
        };
        next_element: {
            type: string;
            text: string;
        } | null;
    } | null;
    /**
     * Find text in table cells
     * @param searchText - Text to search for (partial match)
     */
    private findTextInTableCells;
    /**
     * Find insertion position right after a specific table
     * @param tableIndex - Global table index
     */
    findInsertPositionAfterTable(tableIndex: number): {
        section_index: number;
        element_index: number;
        insert_after: number;
        table_info: {
            rows: number;
            cols: number;
            header: string;
        };
        next_element: {
            type: string;
            text: string;
        } | null;
    } | null;
    getTable(sectionIndex: number, tableIndex: number): {
        rows: number;
        cols: number;
        data: any[][];
    } | null;
    getTableCell(sectionIndex: number, tableIndex: number, row: number, col: number): {
        text: string;
        cell: TableCell;
    } | null;
    updateTableCell(sectionIndex: number, tableIndex: number, row: number, col: number, text: string, charShapeId?: number): boolean;
    setCellProperties(sectionIndex: number, tableIndex: number, row: number, col: number, props: Partial<TableCell>): boolean;
    insertTableRow(sectionIndex: number, tableIndex: number, afterRowIndex: number, cellTexts?: string[]): boolean;
    deleteTableRow(sectionIndex: number, tableIndex: number, rowIndex: number): boolean;
    /**
     * Delete an entire table from the document
     */
    deleteTable(sectionIndex: number, tableIndex: number): boolean;
    insertTableColumn(sectionIndex: number, tableIndex: number, afterColIndex: number): boolean;
    deleteTableColumn(sectionIndex: number, tableIndex: number, colIndex: number): boolean;
    getTableAsCsv(sectionIndex: number, tableIndex: number, delimiter?: string): string | null;
    searchText(query: string, options?: {
        caseSensitive?: boolean;
        regex?: boolean;
        includeTables?: boolean;
    }): Array<{
        section: number;
        element: number;
        text: string;
        matches: string[];
        count: number;
        location?: {
            type: 'paragraph' | 'table';
            tableIndex?: number;
            row?: number;
            col?: number;
        };
    }>;
    replaceText(oldText: string, newText: string, options?: {
        caseSensitive?: boolean;
        regex?: boolean;
        replaceAll?: boolean;
    }): number;
    /**
     * Replace text within a specific table cell.
     * This is more targeted than replaceText and works directly on cell content.
     */
    replaceTextInCell(sectionIndex: number, tableIndex: number, row: number, col: number, oldText: string, newText: string, options?: {
        caseSensitive?: boolean;
        regex?: boolean;
        replaceAll?: boolean;
    }): {
        success: boolean;
        count: number;
        error?: string;
    };
    getMetadata(): HwpxContent['metadata'];
    setMetadata(metadata: Partial<HwpxContent['metadata']>): void;
    getPageSettings(sectionIndex?: number): PageSettings | null;
    setPageSettings(sectionIndex: number, settings: Partial<PageSettings>): boolean;
    getWordCount(): {
        characters: number;
        charactersNoSpaces: number;
        words: number;
        paragraphs: number;
    };
    copyParagraph(sourceSection: number, sourceParagraph: number, targetSection: number, targetAfter: number): boolean;
    moveParagraph(sourceSection: number, sourceParagraph: number, targetSection: number, targetAfter: number): boolean;
    /**
     * Move a table from one location to another within the document.
     * Uses XML-based approach for accurate preservation of table structure.
     */
    moveTable(sectionIndex: number, tableIndex: number, targetSectionIndex: number, targetAfterIndex: number): {
        success: boolean;
        error?: string;
    };
    /**
     * Copy a table to another location (preserving original).
     * Generates new IDs for the copied table.
     */
    copyTable(sectionIndex: number, tableIndex: number, targetSectionIndex: number, targetAfterIndex: number): {
        success: boolean;
        error?: string;
    };
    /**
     * Validate XML tag balance for specified tags.
     * Returns balanced status and any mismatches found.
     */
    validateTagBalance(xml: string): {
        balanced: boolean;
        mismatches: Array<{
            tag: string;
            opens: number;
            closes: number;
        }>;
    };
    /**
     * Validate XML text content is properly escaped.
     */
    validateXmlEscaping(xml: string): {
        valid: boolean;
        issues?: string[];
    };
    private _pendingTableMoves;
    getImages(): Array<{
        id: string;
        width: number;
        height: number;
    }>;
    insertTable(sectionIndex: number, afterElementIndex: number, rows: number, cols: number, options?: {
        width?: number;
        cellWidth?: number;
    }): {
        tableIndex: number;
    } | null;
    /**
     * Insert a nested table inside a table cell.
     * @param sectionIndex Section index
     * @param parentTableIndex Parent table index
     * @param row Row index in parent table
     * @param col Column index in parent table
     * @param nestedRows Number of rows in nested table
     * @param nestedCols Number of columns in nested table
     * @param options Optional data for cells
     */
    insertNestedTable(sectionIndex: number, parentTableIndex: number, row: number, col: number, nestedRows: number, nestedCols: number, options?: {
        data?: string[][];
    }): {
        success: boolean;
        error?: string;
    };
    /**
     * Merge multiple cells in a table into a single cell.
     * The top-left cell becomes the master cell, and other cells in the range are removed.
     *
     * @param sectionIndex Section index
     * @param tableIndex Table index within the section
     * @param startRow Starting row index (0-based)
     * @param startCol Starting column index (0-based)
     * @param endRow Ending row index (0-based, inclusive)
     * @param endCol Ending column index (0-based, inclusive)
     * @returns true if merge was successful, false otherwise
     */
    mergeCells(sectionIndex: number, tableIndex: number, startRow: number, startCol: number, endRow: number, endCol: number): boolean;
    /**
     * Split a merged cell back into individual cells.
     * Only works on cells with colSpan > 1 or rowSpan > 1.
     *
     * @param sectionIndex Section index
     * @param tableIndex Table index within the section
     * @param row Row index of the merged cell (0-based)
     * @param col Column index of the merged cell (0-based)
     * @returns true if split was successful, false otherwise
     */
    splitCell(sectionIndex: number, tableIndex: number, row: number, col: number): boolean;
    getHeader(sectionIndex: number): {
        paragraphs: any[];
    } | null;
    setHeader(sectionIndex: number, text: string): boolean;
    getFooter(sectionIndex: number): {
        paragraphs: any[];
    } | null;
    setFooter(sectionIndex: number, text: string): boolean;
    getFootnotes(): Footnote[];
    insertFootnote(sectionIndex: number, paragraphIndex: number, text: string): {
        id: string;
    } | null;
    getEndnotes(): Endnote[];
    insertEndnote(sectionIndex: number, paragraphIndex: number, text: string): {
        id: string;
    } | null;
    getBookmarks(): {
        name: string;
        section: number;
        paragraph: number;
    }[];
    insertBookmark(sectionIndex: number, paragraphIndex: number, name: string): boolean;
    getHyperlinks(): {
        url: string;
        text: string;
        section: number;
        paragraph: number;
    }[];
    insertHyperlink(sectionIndex: number, paragraphIndex: number, url: string, text: string): boolean;
    /**
     * Insert an image into the document.
     *
     * @param sectionIndex Section to insert into
     * @param afterElementIndex Insert after this element index (-1 for beginning)
     * @param imageData Image data including base64 data and MIME type
     *   - width: Target width in points (optional if preserveAspectRatio is true)
     *   - height: Target height in points (optional if preserveAspectRatio is true)
     *   - preserveAspectRatio: If true, maintains original image aspect ratio.
     *     When only width is specified, height is auto-calculated.
     *     When only height is specified, width is auto-calculated.
     *     When neither is specified, uses original dimensions (scaled to fit if too large).
     *   - position: Positioning options for the image (inline/floating, alignment, offset, text wrap)
     * @returns Object with image ID or null on failure
     */
    insertImage(sectionIndex: number, afterElementIndex: number, imageData: {
        data: string;
        mimeType: string;
        width?: number;
        height?: number;
        preserveAspectRatio?: boolean;
        position?: ImagePositionOptions;
        headerText?: string;
    }): {
        id: string;
        actualWidth: number;
        actualHeight: number;
    } | null;
    /**
     * Insert an image inside a table cell
     * @param sectionIndex - Section containing the table
     * @param tableIndex - Table index (local to section)
     * @param row - Row index (0-based)
     * @param col - Column index (0-based)
     * @param imageData - Image data including base64, mimeType, and optional dimensions
     * @returns Object with image ID and actual dimensions, or null on failure
     */
    insertImageInCell(sectionIndex: number, tableIndex: number, row: number, col: number, imageData: {
        data: string;
        mimeType: string;
        width?: number;
        height?: number;
        preserveAspectRatio?: boolean;
        afterText?: string;
    }): {
        id: string;
        actualWidth: number;
        actualHeight: number;
    } | null;
    /**
     * Get existing image IDs from ZIP file
     */
    private getExistingImageIds;
    updateImageSize(imageId: string, width: number, height: number): boolean;
    deleteImage(imageId: string): boolean;
    insertLine(sectionIndex: number, x1: number, y1: number, x2: number, y2: number, options?: {
        color?: string;
        width?: number;
    }): {
        id: string;
    } | null;
    insertRect(sectionIndex: number, x: number, y: number, width: number, height: number, options?: {
        fillColor?: string;
        strokeColor?: string;
    }): {
        id: string;
    } | null;
    insertEllipse(sectionIndex: number, cx: number, cy: number, rx: number, ry: number, options?: {
        fillColor?: string;
        strokeColor?: string;
    }): {
        id: string;
    } | null;
    insertEquation(sectionIndex: number, afterElementIndex: number, script: string): {
        id: string;
    } | null;
    getEquations(): {
        id: string;
        script: string;
    }[];
    getMemos(): Memo[];
    insertMemo(sectionIndex: number, paragraphIndex: number, content: string, author?: string): {
        id: string;
    } | null;
    deleteMemo(memoId: string): boolean;
    getSections(): {
        index: number;
        pageSettings: PageSettings;
    }[];
    insertSection(afterSectionIndex: number): number;
    deleteSection(sectionIndex: number): boolean;
    getStyles(): {
        id: number;
        name: string;
        type: string;
    }[];
    getCharShapes(): CharShape[];
    getParaShapes(): ParaShape[];
    applyStyle(sectionIndex: number, paragraphIndex: number, styleId: number): boolean;
    getColumnDef(sectionIndex: number): ColumnDef | null;
    setColumnDef(sectionIndex: number, columns: number, gap?: number): boolean;
    save(): Promise<Buffer>;
    private syncContentToZip;
    /**
     * Invalidate cached XML positions for all paragraphs.
     * Called after save() because XML modifications may shift byte positions.
     * The positions will be re-populated on next document reload.
     */
    private invalidateXmlPositions;
    /**
     * Get cached XML position for a paragraph at the given section and element index.
     * Returns undefined if no cached position is available.
     * The cached positions are populated during parsing in HwpxParser.parseSection().
     */
    private getCachedXmlPosition;
    /**
     * Remove Fasoo DRM tracking information from content.hpf.
     * Fasoo DRM adds tracking IDs to the description metadata which causes
     * "document corrupted or tampered" warnings when the file is modified externally.
     */
    private removeFasooDrmTracking;
    /**
     * Apply pending image deletions to the ZIP.
     * Removes <hp:pic> elements from section XML and deletes BinData files.
     */
    private applyImageDeletesToZip;
    /**
     * Apply table deletes to XML.
     * Removes tables from the section XML.
     * Uses findAllTables for proper nested table handling.
     */
    private applyTableDeletesToXml;
    /**
     * Apply paragraph/element deletes to XML.
     * Removes paragraphs or tables from the section XML.
     */
    private applyParagraphDeletesToXml;
    /**
     * Apply table inserts to XML.
     * Inserts new tables into the section XML.
     */
    private applyTableInsertsToXml;
    /**
     * Apply table move/copy operations to XML.
     * Extracts table XML from source and inserts at target position.
     */
    private applyTableMovesToXml;
    /**
     * Regenerate all IDs in XML to avoid duplicates.
     */
    private regenerateIdsInXml;
    /**
     * Find the position to insert an element after a given element index.
     * Returns the position after the closing tag of the element.
     */
    private findInsertPositionForElement;
    /**
     * Apply paragraph inserts to XML.
     * Inserts new paragraphs at the specified positions.
     */
    private applyParagraphInsertsToXml;
    /**
     * Apply nested table inserts to XML.
     * Inserts a new table inside a cell of an existing table.
     */
    private applyNestedTableInsertsToXml;
    /**
     * Generate XML for a nested table.
     */
    private generateNestedTableXml;
    /**
     * Insert a nested table XML into a cell XML.
     * Finds the last <hp:p> in the cell and inserts the table inside a run.
     */
    private insertNestedTableIntoCell;
    /**
     * Apply cell merges to XML.
     * Updates colSpan/rowSpan attributes on master cell and removes merged cells.
     * Groups merges by table to handle multiple merges in the same table correctly.
     */
    private applyCellMergesToXml;
    /**
     * Apply merge to a single table XML.
     * @returns Updated table XML or null if merge failed
     */
    private applyMergeToTable;
    /**
     * Apply cell splits to XML.
     * Resets colSpan/rowSpan to 1 and creates new cells to fill the split area.
     */
    private applyCellSplitsToXml;
    /**
     * Apply split to a single table XML.
     * @returns Updated table XML or null if split failed
     */
    private applySplitToTable;
    /**
     * Generate an empty cell XML for split operations.
     */
    private generateEmptyCell;
    /**
     * Apply table cell updates to XML while preserving original structure.
     * This function modifies only the text content of specific cells,
     * keeping all other XML elements, attributes, and structure intact.
     *
     * Safety features:
     * - Backs up original XML before modification
     * - Validates XML structure after changes
     * - Reverts to original if validation fails
     */
    private applyTableCellUpdatesToXml;
    /**
     * Basic XML structure validation.
     * Checks for common corruption indicators.
     * Note: This is intentionally lenient to avoid false positives.
     */
    private validateXmlStructure;
    /**
     * Check tag balance for a specific element name.
     * Returns the difference (open - close). 0 means balanced.
     */
    private checkTagBalance;
    /**
     * Validate table structure integrity.
     * Checks:
     * - Row count consistency (declared vs actual)
     * - Cell count per row matches colCnt when accounting for colSpan
     * - colAddr/rowAddr continuity
     * - No orphaned cells (rowSpan consistency)
     * @returns Error message if validation fails, null if valid
     */
    private validateTableStructure;
    /**
     * Extract all nested tables from XML content.
     * Uses balanced bracket matching to find complete table elements.
     */
    private extractNestedTables;
    /**
     * Find a table by its ID in XML.
     */
    private findTableById;
    /**
     * Extract complete table XML from a regex match.
     */
    private extractTableFromMatch;
    /**
     * Find all tables in XML and return their positions and content.
     */
    /**
     * Find top-level paragraph and table elements (direct children of section).
     * Uses depth tracking to skip elements nested inside <hp:tbl>, <hp:tc>, <hp:secPr>, etc.
     * Only counts <hp:p> and <hp:tbl> at depth 0 (relative to section root).
     */
    private findTopLevelElements;
    private findAllTables;
    /**
     * Find all elements of a given type using depth tracking.
     * This correctly handles nested elements (e.g., nested tables).
     * @param xml The XML string to search in
     * @param elementName The element name without namespace prefix (e.g., 'tr', 'tc')
     * @returns Array of elements with their positions
     */
    private findAllElementsWithDepth;
    /**
     * Update specific cells in a table XML string.
     * Groups updates by row to avoid index corruption when multiple cells in the same row are updated.
     */
    private updateTableCellsInXml;
    /**
     * Update multiple cells in a single row XML string.
     * Processes cells from right to left (descending col order) to avoid index shifting.
     */
    private updateMultipleCellsInRow;
    /**
     * Update a specific cell in a row XML string.
     * @deprecated Use updateMultipleCellsInRow for better index handling
     */
    private updateCellInRow;
    /**
     * Reset lineseg values to default so Hancom Word recalculates line layout.
     * When text content changes, the old lineseg values (horzsize, textpos, etc.)
     * no longer match the new text, causing rendering issues like overlapping text.
     * By resetting to default values, Hancom Word will recalculate proper line breaks.
     */
    private resetLinesegInXml;
    /**
     * Update text content in a cell XML string.
     * Handles both existing text replacement and empty cell population.
     * If charShapeId is provided, overrides the charPrIDRef attribute.
     */
    private updateTextInCell;
    /**
     * Update text content in a cell with chunked runs (for long text without newlines).
     * Splits long text into multiple <hp:run> elements within a single paragraph.
     */
    private updateTextInCellChunked;
    /**
     * Update text content in a cell with multiple paragraphs (for text with newlines).
     * Each line becomes a separate <hp:p> element, allowing independent styling.
     */
    private updateTextInCellMultiline;
    /**
     * Apply cell image inserts to XML
     * Inserts an image inside a table cell
     */
    private applyCellImageInsertsToXml;
    /**
     * Apply direct text updates (exact match replacement)
     * Groups updates by paragraph to handle multi-run updates correctly
     *
     * BUGFIX (2026-01-25): Pre-compute paragraph mappings before any modifications
     * to prevent text merging when multiple paragraphs have the same oldText pattern.
     * Updates are applied in reverse order (bottom-to-top) to avoid position shifts.
     */
    private applyDirectTextUpdatesToXml;
    /**
     * Replace multiple runs in a paragraph element at once
     * This is needed when updating run 0 also clears runs 1-N
     */
    private replaceMultipleRunsInElement;
    /**
     * Calculate the occurrence index for a paragraph with given ID.
     * Returns how many paragraphs with the same ID appear before this one.
     */
    private getParagraphOccurrence;
    /**
     * Find paragraph by its ID attribute and occurrence index.
     * Uses balanced tag matching to handle nested paragraphs.
     * @param xml - The XML content
     * @param paragraphId - The paragraph ID to find
     * @param occurrence - Which occurrence of this ID (0-indexed)
     */
    private findParagraphById;
    /**
     * Calculate Levenshtein distance between two strings.
     * Used for fuzzy paragraph matching when exact match fails.
     */
    private levenshteinDistance;
    /**
     * Find paragraph using fuzzy text matching with Levenshtein distance.
     * Fallback method when ID and index-based lookups fail.
     */
    private findParagraphByFuzzyMatch;
    /**
     * Find the target paragraph for an update operation.
     * Extracts paragraph-finding logic from replaceMultipleRunsInElement for reuse.
     * Returns the paragraph's start, end, and XML content in the original document.
     */
    private findTargetParagraphForUpdate;
    /**
     * Replace multiple runs in a paragraph element at once.
     * Finds hp:run elements and updates their hp:t content.
     */
    private replaceRunsInParagraphDirect;
    /**
     * Replace text in a single run directly using pre-computed target location.
     * Simpler version for single-run updates.
     */
    private replaceTextInElementDirect;
    /**
     * Replace text in a paragraph identified by both ID and text content.
     * This is more reliable because:
     * - Uses ID to narrow down candidates (even if not unique)
     * - Uses oldText to find the exact paragraph among candidates
     */
    private replaceTextInParagraphByIdAndText;
    /**
     * Replace text only within a specific element (paragraph) identified by elementIndex.
     * This ensures that identical text in other parts of the document is not affected.
     *
     * IMPORTANT: This follows the same element indexing as HwpxParser.parseSection:
     * - All top-level elements are counted: paragraphs, tables, images, shapes (23+ types)
     * - Paragraphs INSIDE tables are NOT counted (they're part of the table)
     * - Text replacement only applies to paragraph elements (type 'p')
     * - Other elements (images, shapes, etc.) are counted for indexing but not modified
     */
    private replaceTextInElementByIndex;
    private escapeRegex;
    /**
     * Replace text in a paragraph identified by its ID.
     * This is more reliable than index-based lookup because:
     * - Paragraph IDs are stable across document modifications
     * - Not affected by the presence of images, shapes, or other elements
     */
    private replaceTextInParagraphById;
    /**
     * Apply text replacements directly to XML files.
     * This is the safest approach as it preserves the original XML structure.
     */
    private applyTextReplacementsToXml;
    /**
     * Sync structural changes (paragraph text, table cells, etc.)
     * Regenerates section XML from _content to handle new elements.
     */
    private syncStructuralChangesToZip;
    /**
     * Generate complete section XML from HwpxSection content.
     */
    private generateSectionXml;
    /**
     * Generate paragraph XML from HwpxParagraph.
     */
    private generateParagraphXml;
    /**
     * Generate table XML from HwpxTable.
     */
    private generateTableXml;
    /**
     * Update section XML with current content.
     * Handles paragraphs and table cells.
     */
    private updateSectionXml;
    /**
     * Update paragraph XML with new text content.
     */
    private updateParagraphXml;
    /**
     * Serialize a CharShape object to XML string.
     * This preserves all character style properties including spacing (자간).
     */
    private serializeCharShape;
    /**
     * Sync charShapes from memory to header.xml.
     * This ensures character styles (including spacing) are preserved after save.
     */
    private syncCharShapesToZip;
    /**
     * Sync metadata to header.xml
     */
    private syncMetadataToZip;
    private escapeXml;
    /**
     * Default chunk size for splitting long text (in characters).
     * Texts longer than this will be split into multiple <hp:run> elements.
     */
    private static readonly TEXT_CHUNK_SIZE;
    /**
     * Split long text into chunks for safer XML processing.
     * Attempts to split at word boundaries (spaces, punctuation) when possible.
     * @param text The text to split
     * @param maxChunkSize Maximum characters per chunk (default: TEXT_CHUNK_SIZE)
     * @returns Array of text chunks
     */
    private splitTextIntoChunks;
    /**
     * Generate multiple <hp:run> elements for chunked text.
     * Used when text is too long to be in a single run.
     */
    private generateChunkedRuns;
    /**
     * Get image dimensions from base64 encoded data
     * Returns width and height in pixels
     */
    private getImageDimensions;
    /**
     * Get raw XML content of a section.
     * Useful for AI-based document manipulation.
     */
    getSectionXml(sectionIndex: number): Promise<string | null>;
    /**
     * Set (replace) raw XML content of a section.
     * WARNING: This completely replaces the section XML. Use with caution.
     * The XML must be valid HWPML format.
     *
     * @param sectionIndex The section index to replace
     * @param xml The new XML content (must be valid HWPML)
     * @param validate If true, performs basic XML validation before replacing
     * @returns Object with success status and any validation errors
     */
    setSectionXml(sectionIndex: number, xml: string, validate?: boolean): Promise<{
        success: boolean;
        error?: string;
    }>;
    /**
     * Validate section XML structure.
     */
    private validateSectionXml;
    /**
     * Render Mermaid diagram and insert as image into the document.
     * Uses mermaid.ink API for rendering.
     *
     * @param mermaidCode The Mermaid diagram code
     * @param sectionIndex Section to insert into
     * @param afterElementIndex Insert after this element index (-1 for beginning)
     * @param options Optional rendering options
     *   - width: Target width in points (optional)
     *   - height: Target height in points (optional)
     *   - preserveAspectRatio: If true, maintains original image aspect ratio (default: true)
     *     When only width is specified, height is auto-calculated.
     *     When only height is specified, width is auto-calculated.
     *   - position: Positioning options for the rendered diagram
     * @returns Object with image ID and actual dimensions, or error
     */
    renderMermaidToImage(mermaidCode: string, sectionIndex: number, afterElementIndex: number, options?: {
        width?: number;
        height?: number;
        theme?: 'default' | 'dark' | 'forest' | 'neutral';
        backgroundColor?: string;
        preserveAspectRatio?: boolean;
        position?: ImagePositionOptions;
        headerText?: string;
    }): Promise<{
        success: boolean;
        imageId?: string;
        actualWidth?: number;
        actualHeight?: number;
        error?: string;
    }>;
    /**
     * Get list of available sections.
     */
    getAvailableSections(): Promise<number[]>;
    /**
     * Apply pending image inserts to ZIP file.
     * 1. Add image file to BinData/ folder
     * 2. Update content.hpf manifest
     * 3. Add hp:pic tag to section XML
     */
    private applyImageInsertsToZip;
    /**
     * Get file extension from MIME type
     */
    private getExtensionFromMimeType;
    /**
     * Extract original image dimensions from base64 encoded image data.
     * Supports PNG and JPEG formats.
     * @param base64Data Base64 encoded image data
     * @param mimeType MIME type of the image
     * @returns { width, height } or null if unable to parse
     */
    private getImageDimensionsFromBase64;
    /**
     * Add image entry to content.hpf manifest
     */
    private addImageToContentHpf;
    /**
     * Add hp:pic tag to section XML
     */
    private addImageToSectionXml;
    /**
     * Find insertion position in XML by searching for text content.
     * Returns the position right after the paragraph containing the text, or null if not found.
     */
    private findInsertPositionByTextInXml;
    /**
     * Extract text content from paragraph XML
     */
    private extractTextFromParagraphXml;
    /**
     * Extract text content from cell XML (handles subList and nested paragraphs)
     */
    private extractTextFromCellXml;
    /**
     * Find all paragraphs in a table cell XML
     * Returns array of { start, end, xml } for each paragraph
     */
    private findAllParagraphsInCell;
    /**
     * Generate hp:pic XML tag for image with positioning options
     */
    private generateImagePicXml;
    /**
     * Analyze XML for issues like tag imbalance, malformed elements, etc.
     * @param sectionIndex Section to analyze (optional, all sections if not specified)
     * @returns Detailed analysis report
     */
    analyzeXml(sectionIndex?: number): Promise<{
        hasIssues: boolean;
        sections: Array<{
            sectionIndex: number;
            issues: Array<{
                type: 'tag_imbalance' | 'malformed_tag' | 'unclosed_tag' | 'orphan_close_tag' | 'nesting_error';
                severity: 'error' | 'warning';
                message: string;
                position?: number;
                context?: string;
                suggestedFix?: string;
            }>;
            tagCounts: Record<string, {
                open: number;
                close: number;
                balance: number;
            }>;
        }>;
        summary: string;
    }>;
    /**
     * Analyze XML content for issues
     */
    private analyzeXmlContent;
    /**
     * Find specific issues with tbl (table) tags
     */
    private findTblTagIssues;
    /**
     * Check for common nesting errors
     */
    private checkNestingErrors;
    /**
     * Attempt to repair XML issues in a section
     * @param sectionIndex Section to repair
     * @param options Repair options
     * @returns Repair result
     */
    repairXml(sectionIndex: number, options?: {
        removeOrphanCloseTags?: boolean;
        addMissingCloseTags?: boolean;
        fixTableStructure?: boolean;
        backup?: boolean;
    }): Promise<{
        success: boolean;
        message: string;
        repairsApplied: string[];
        originalXml?: string;
    }>;
    /**
     * Remove orphan closing tags (tbl, tr, tc, p, subList)
     */
    private removeOrphanCloseTags;
    /**
     * Fix tag imbalance globally (not just within tables)
     */
    private fixTagImbalanceGlobal;
    /**
     * Fix table structure issues
     */
    private fixTableStructure;
    /**
     * Fix tag imbalance for a specific element type
     */
    private fixTagImbalance;
    /**
     * Get raw XML of a section for manual inspection/editing
     */
    getRawSectionXml(sectionIndex: number): Promise<string | null>;
    /**
     * Set raw XML of a section (use with caution)
     */
    setRawSectionXml(sectionIndex: number, xml: string, validate?: boolean): Promise<{
        success: boolean;
        message: string;
        issues?: Array<{
            type: string;
            message: string;
        }>;
    }>;
    /**
     * 위치 찾기 통합 도구
     * @param type 찾을 대상 유형: 'table' | 'paragraph' | 'insert_point'
     * @param query 검색할 텍스트
     * @returns 찾은 위치 정보 또는 null
     */
    findPosition(type: 'table' | 'paragraph' | 'insert_point', query: string): {
        type: string;
        sectionIndex: number;
        elementIndex?: number;
        tableIndex?: number;
        paragraphIndex?: number;
        foundIn?: 'paragraph' | 'table_cell';
        tableInfo?: {
            tableIndex: number;
            row: number;
            col: number;
        };
    } | null;
    /**
     * 테이블 조회 통합 도구
     * @param options 조회 옵션
     * @returns 테이블 정보
     */
    queryTable(options: {
        mode: 'list' | 'full' | 'cell' | 'map' | 'summary';
        tableIndex?: number;
        row?: number;
        col?: number;
        sectionIndex?: number;
    }): {
        tables?: Array<{
            index: number;
            rowCount: number;
            colCount: number;
            sectionIndex: number;
        }>;
        table?: HwpxTable | null;
        cell?: {
            text: string;
            paragraphs: HwpxParagraph[];
        } | null;
        map?: Array<{
            index: number;
            header: string;
            sectionIndex: number;
            elementIndex: number;
            firstRowPreview: string[];
        }>;
    };
    /**
     * 내용 수정 통합 도구
     * @param options 수정 옵션
     * @returns 성공 여부
     */
    modifyContent(options: {
        type: 'cell' | 'replace' | 'paragraph';
        tableIndex?: number;
        row?: number;
        col?: number;
        sectionIndex?: number;
        paragraphIndex?: number;
        runIndex?: number;
        text?: string;
        oldText?: string;
        newText?: string;
        replaceAll?: boolean;
        caseSensitive?: boolean;
    }): boolean;
    /**
     * 스타일 적용 통합 도구
     * 기존 applyStyle(sectionIndex, paragraphIndex, styleId)과 구분하기 위해 이름 변경
     * @param options 스타일 옵션
     * @returns 성공 여부
     */
    applyConsolidatedStyle(options: {
        target: 'paragraph' | 'table_cell' | 'text';
        sectionIndex?: number;
        paragraphIndex?: number;
        tableIndex?: number;
        row?: number;
        col?: number;
        runIndex?: number;
        style: {
            hangingIndent?: number;
            align?: 'left' | 'center' | 'right' | 'justify';
            lineSpacing?: number;
            bold?: boolean;
            italic?: boolean;
            fontSize?: number;
            fontColor?: string;
        };
    }): boolean;
    private _positionIndex;
    private _documentChunks;
    private _lastChunkTime;
    /**
     * Chunk document into overlapping segments for agentic reading
     * @param chunkSize Target chunk size in characters (default 500)
     * @param overlap Overlap between chunks in characters (default 100)
     * @returns Array of document chunks with position information
     */
    chunkDocument(chunkSize?: number, overlap?: number): DocumentChunk[];
    /**
     * Search chunks using keyword-based similarity scoring
     * Returns chunks ranked by relevance to the query
     * @param query Search query
     * @param topK Number of top results to return (default 5)
     * @param minScore Minimum similarity score threshold (default 0.1)
     */
    searchChunks(query: string, topK?: number, minScore?: number): Array<{
        chunk: DocumentChunk;
        score: number;
        matchedTerms: string[];
        snippet: string;
    }>;
    /**
     * Simple tokenizer for Korean and English text
     */
    private tokenize;
    /**
     * Extract table of contents based on formatting rules
     * Identifies headings by:
     * - Numbered patterns (1., 가., (1), ①)
     * - Short paragraphs followed by longer content
     * - Bold or larger font (if style info available)
     */
    extractToc(): Array<{
        level: number;
        title: string;
        sectionIndex: number;
        elementIndex: number;
        offset: number;
        children?: Array<{
            level: number;
            title: string;
            sectionIndex: number;
            elementIndex: number;
            offset: number;
        }>;
    }>;
    /**
     * Build hierarchical TOC structure from flat list
     */
    private buildTocHierarchy;
    /**
     * Build and store position index for quick lookup
     * Call this after document modifications to keep index updated
     */
    buildPositionIndex(): PositionIndexEntry[];
    /**
     * Get cached position index or build if needed
     */
    getPositionIndex(): PositionIndexEntry[];
    /**
     * Search position index by text query
     */
    searchPositionIndex(query: string, type?: 'heading' | 'paragraph' | 'table'): PositionIndexEntry[];
    /**
     * Get chunk at specific offset
     */
    getChunkAtOffset(offset: number): DocumentChunk | null;
    /**
     * Get surrounding chunks (context window)
     * @param chunkId ID of the center chunk
     * @param before Number of chunks before
     * @param after Number of chunks after
     */
    getChunkContext(chunkId: string, before?: number, after?: number): {
        chunks: DocumentChunk[];
        centerIndex: number;
    };
    /**
     * Clear cached chunks and position index
     * Call this after document modifications
     */
    invalidateReadingCache(): void;
    /**
     * Apply paragraph style changes (alignment, etc.) to XML files.
     * Creates new paraPr elements in header.xml and updates paragraph references in section XML.
     */
    private applyParagraphStylesToXml;
    /**
     * Apply character style changes (font, size, bold, italic) to XML files.
     * Creates new charPr elements in header.xml and updates run references in section XML.
     */
    private applyCharacterStylesToXml;
    /**
     * Apply hanging indent changes to XML files.
     * This adds new paraPr elements to header.xml and updates paragraph references in section XML.
     */
    private applyHangingIndentsToXml;
    /**
     * Apply table cell hanging indent changes to XML files.
     * This adds new paraPr elements to header.xml and updates paragraph references in table cells.
     */
    private applyTableCellHangingIndentsToXml;
    /**
     * Find a specific cell in table XML by row and column index.
     * Uses balanced bracket matching to correctly handle nested tables.
     * @returns Cell XML content and its position, or null if not found
     */
    private findTableCellInXml;
    private applyTableRowInsertsToXml;
    private applyTableRowDeletesToXml;
    private applyTableColumnInsertsToXml;
    private applyTableColumnDeletesToXml;
    /**
     * Find top-level paragraph/table XML elements in section XML with full content.
     * Returns elements with their complete XML (including closing tags).
     */
    private findTopLevelFullElements;
    private applyParagraphCopiesToXml;
    private applyParagraphMovesToXml;
    private applyHeaderFooterUpdatesToXml;
}
export {};
