export type LineType1 = 'Solid' | 'Dash' | 'Dot' | 'DashDot' | 'DashDotDot' | 'LongDash' | 'CircleDot' | 'DoubleSlim' | 'SlimThick' | 'ThickSlim' | 'SlimThickSlim' | 'None' | 'solid' | 'dash' | 'dot' | 'dashDot' | 'dashDotDot' | 'longDash' | 'circleDot' | 'doubleSlim' | 'slimThick' | 'thickSlim' | 'slimThickSlim' | 'none';
export type LineType2 = LineType1;
export type LineType3 = 'Solid' | 'Dot' | 'Thick' | 'Dash' | 'DashDot' | 'DashDotDot';
export type LineWidth = '0.1mm' | '0.12mm' | '0.15mm' | '0.2mm' | '0.25mm' | '0.3mm' | '0.4mm' | '0.5mm' | '0.6mm' | '0.7mm' | '1.0mm' | '1.5mm' | '2.0mm' | '3.0mm' | '4.0mm' | '5.0mm';
export type NumberType1 = 'Digit' | 'CircledDigit' | 'RomanCapital' | 'RomanSmall' | 'LatinCapital' | 'LatinSmall' | 'CircledLatinCapital' | 'CircledLatinSmall' | 'HangulSyllable' | 'CircledHangulSyllable' | 'HangulJamo' | 'CircledHangulJamo' | 'HangulPhonetic' | 'Ideograph' | 'CircledIdeograph' | 'DecimalEnclosedInParentheses' | 'digit' | 'circledDigit' | 'romanCapital' | 'romanSmall' | 'latinCapital' | 'latinSmall' | 'circledLatinCapital' | 'circledLatinSmall' | 'hangulSyllable' | 'circledHangulSyllable' | 'hangulJamo' | 'circledHangulJamo' | 'hangulPhonetic' | 'ideograph' | 'circledIdeograph' | 'decimalEnclosedInParentheses';
export type NumberType2 = NumberType1 | 'DecagonCircle' | 'DecagonCircleHanja' | 'Symbol' | 'UserChar';
export type AlignmentType1 = 'Justify' | 'Left' | 'Right' | 'Center' | 'Distribute' | 'DistributeSpace' | 'justify' | 'left' | 'right' | 'center' | 'distribute' | 'distributeSpace';
export type AlignmentType2 = 'Left' | 'Center' | 'Right';
export type ArrowType = 'Normal' | 'Arrow' | 'Spear' | 'ConcaveArrow' | 'EmptyDiamond' | 'EmptyCircle' | 'EmptyBox' | 'FilledDiamond' | 'FilledCircle' | 'FilledBox';
export type ArrowSize = 'SmallSmall' | 'SmallMedium' | 'SmallLarge' | 'MediumSmall' | 'MediumMedium' | 'MediumLarge' | 'LargeSmall' | 'LargeMedium' | 'LargeLarge';
export type LangType = 'Hangul' | 'Latin' | 'Hanja' | 'Japanese' | 'Other' | 'Symbol' | 'User';
export type HatchStyle = 'Horizontal' | 'Vertical' | 'BackSlash' | 'Slash' | 'Cross' | 'CrossDiagonal';
export type InfillMode = 'Tile' | 'TileHorzTop' | 'TileHorzBottom' | 'TileVertLeft' | 'TileVertRight' | 'Total' | 'Center' | 'CenterTop' | 'CenterBottom' | 'LeftCenter' | 'LeftTop' | 'LeftBottom' | 'RightCenter' | 'RightTop' | 'RightBottom' | 'Zoom';
export type LineWrapType = 'Break' | 'Squeeze' | 'Keep' | 'break' | 'squeeze' | 'keep';
export type TextWrapType = 'Square' | 'Tight' | 'Through' | 'TopAndBottom' | 'BehindText' | 'InFrontOfText' | 'square' | 'tight' | 'through' | 'topAndBottom' | 'behindText' | 'inFrontOfText';
export type TextFlowType = 'BothSides' | 'LeftOnly' | 'RightOnly' | 'LargestOnly' | 'bothSides' | 'leftOnly' | 'rightOnly' | 'largestOnly';
export type FieldType = 'Clickhere' | 'Hyperlink' | 'Bookmark' | 'Formula' | 'Summery' | 'UserInfo' | 'Date' | 'DocDate' | 'Path' | 'Crossref' | 'Mailmerge' | 'Memo' | 'RevisionChange' | 'RevisionSign' | 'RevisionDelete' | 'RevisionAttach' | 'RevisionClipping' | 'RevisionSawtooth' | 'RevisionThinking' | 'RevisionPraise' | 'RevisionLine' | 'RevisionSimpleChange' | 'RevisionHyperlink' | 'RevisionLineAttach' | 'RevisionLineLink' | 'RevisionLineTransfer' | 'RevisionRightmove' | 'RevisionLeftmove' | 'RevisionTransfer' | 'RevisionSplit' | 'unknown' | 'hyperlink' | 'bookmark' | 'formula' | 'memo' | 'date' | 'docDate' | 'path' | 'mailMerge' | 'crossRef' | 'clickHere' | 'summary' | 'userInfo' | 'revisionSign' | 'privateTxt' | 'tableOfContents';
export type UnderlineType = 'Bottom' | 'Center' | 'Top' | 'None' | 'bottom' | 'center' | 'top' | 'none';
export type StrikeoutType = 'None' | 'Continuous';
export type ShadowType = 'None' | 'Drop' | 'Cont';
export type EmphasisMark = 'None' | 'Dot' | 'Circle' | 'Ring' | 'Caron' | 'UnderDot' | 'UnderLine' | 'Triangle' | 'none' | 'dot' | 'circle' | 'ring' | 'caron' | 'underDot' | 'underLine' | 'triangle';
export type HeadingType = 'None' | 'Outline' | 'Number' | 'Bullet' | 'none' | 'outline' | 'number' | 'bullet';
export type GradationType = 'Linear' | 'Radial' | 'Conical' | 'Square' | 'linear' | 'radial' | 'conical' | 'square';
export type PageBreakType = 'Table' | 'Cell' | 'None' | 'table' | 'cell' | 'none';
export type VertAlign = 'Top' | 'Center' | 'Bottom' | 'Inside' | 'Outside' | 'Para' | 'top' | 'center' | 'bottom' | 'inside' | 'outside' | 'para';
export type HorzAlign = 'Left' | 'Center' | 'Right' | 'Inside' | 'Outside' | 'left' | 'center' | 'right' | 'inside' | 'outside';
export type VertRelTo = 'Paper' | 'Page' | 'Para' | 'paper' | 'page' | 'para';
export type HorzRelTo = 'Paper' | 'Page' | 'Column' | 'Para' | 'paper' | 'page' | 'column' | 'para';
export type SizeRelTo = 'Paper' | 'Page' | 'Column' | 'Para' | 'Absolute';
export type GutterType = 'LeftOnly' | 'LeftRight' | 'TopBottom';
export type PageStartsOn = 'Both' | 'Even' | 'Odd' | 'both' | 'even' | 'odd';
export type ArcType = 'Normal' | 'Pie' | 'Chord';
export type OleObjectType = 'Unknown' | 'Embedded' | 'Link' | 'Static' | 'Equation';
export type DrawAspect = 'Content' | 'ThumbNail' | 'Icon' | 'DocPrint';
export type ColumnType = 'Newspaper' | 'BalancedNewspaper' | 'Parallel' | 'newspaper' | 'balanced' | 'parallel';
export type ColumnLayout = 'Left' | 'Right' | 'Mirror' | 'left' | 'right' | 'mirror';
export interface ColumnInfo {
    width: number;
    gap: number;
}
export type NoteNumberingType = 'Continuous' | 'OnSection' | 'OnPage';
export type NotePlacement = 'EachColumn' | 'MergedColumn' | 'RightMostColumn' | 'EndOfDocument' | 'EndOfSection';
export type TabType = 'Left' | 'Right' | 'Center' | 'Decimal' | 'left' | 'right' | 'center' | 'decimal';
export type BreakLatinWord = 'KeepWord' | 'Hyphenation' | 'BreakWord' | 'keepWord' | 'normal' | 'hyphenation' | 'breakWord';
export interface FontInfo {
    id: number;
    type?: 'rep' | 'ttf' | 'hft';
    name: string;
    substFont?: {
        type?: 'rep' | 'ttf' | 'hft';
        name: string;
    };
    typeInfo?: {
        familyType?: number;
        serifStyle?: number;
        weight?: number;
        proportion?: number;
        contrast?: number;
        strokeVariation?: number;
        armStyle?: number;
        letterform?: number;
        midline?: number;
        xHeight?: number;
    };
}
export interface BorderStyle {
    type?: LineType1;
    width?: LineWidth | string | number;
    color?: string;
}
export interface WindowBrush {
    faceColor?: string;
    hatchColor?: string;
    hatchStyle?: HatchStyle;
    alpha?: number;
}
export interface GradationFill {
    type: GradationType;
    angle?: number;
    centerX?: number;
    centerY?: number;
    step?: number;
    colorNum?: number;
    stepCenter?: number;
    alpha?: number;
    colors: string[];
}
export interface ImageBrush {
    mode: InfillMode;
    bright?: number;
    contrast?: number;
    effect?: 'RealPic' | 'GrayScale' | 'BlackWhite';
    binItem?: string;
    alpha?: number;
}
export interface FillBrush {
    windowBrush?: WindowBrush;
    gradation?: GradationFill;
    imageBrush?: ImageBrush;
}
export interface BorderFillStyle {
    id: number;
    threeD?: boolean;
    shadow?: boolean;
    slash?: number;
    backSlash?: number;
    crookedSlash?: number;
    centerLine?: boolean;
    leftBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    rightBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    topBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    bottomBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    diagonal?: BorderStyle;
    diagonalBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    antiDiagonalBorder?: BorderStyle | {
        style?: string;
        width?: number | string;
        color?: string;
    };
    fillBrush?: FillBrush;
    fillColor?: string;
    fillType?: FillType;
    gradation?: {
        type: GradationType;
        angle?: number;
        centerX?: number;
        centerY?: number;
        step?: number;
        colors: string[];
    };
    imageFill?: {
        mode: ImageFillMode;
        alpha?: number;
        binaryItemId?: string;
    };
}
export interface CharShape {
    id: number;
    tagName?: 'charShape' | 'charPr';
    height?: number;
    textColor?: string;
    shadeColor?: string;
    useFontSpace?: boolean;
    useKerning?: boolean;
    symMark?: EmphasisMark;
    borderFillId?: number;
    fontRefs?: {
        hangul?: number;
        latin?: number;
        hanja?: number;
        japanese?: number;
        other?: number;
        symbol?: number;
        user?: number;
    };
    fontNames?: {
        hangul?: string;
        latin?: string;
        hanja?: string;
        japanese?: string;
        other?: string;
        symbol?: string;
        user?: string;
    };
    ratio?: {
        hangul?: number;
        latin?: number;
        hanja?: number;
        japanese?: number;
        other?: number;
        symbol?: number;
        user?: number;
    };
    charSpacing?: {
        hangul?: number;
        latin?: number;
        hanja?: number;
        japanese?: number;
        other?: number;
        symbol?: number;
        user?: number;
    };
    relSize?: {
        hangul?: number;
        latin?: number;
        hanja?: number;
        japanese?: number;
        other?: number;
        symbol?: number;
        user?: number;
    };
    charOffset?: {
        hangul?: number;
        latin?: number;
        hanja?: number;
        japanese?: number;
        other?: number;
        symbol?: number;
        user?: number;
    };
    italic?: boolean;
    bold?: boolean;
    underline?: boolean | {
        type: UnderlineType;
        shape: LineType2;
        color: string;
    };
    underlineType?: UnderlineType | 'bottom' | 'center' | 'top' | 'none';
    underlineShape?: UnderlineShape;
    underlineColor?: string;
    strikethrough?: boolean;
    strikeout?: boolean | {
        type: StrikeoutType;
        shape: LineType2;
        color: string;
    };
    strikeoutShape?: StrikeoutShape;
    strikeoutColor?: string;
    outline?: LineType3 | {
        type: LineType3;
    };
    shadow?: ShadowType | {
        type: ShadowType;
        color?: string;
        offsetX?: number;
        offsetY?: number;
        alpha?: number;
    };
    shadowX?: number;
    shadowY?: number;
    shadowColor?: string;
    emboss?: boolean;
    engrave?: boolean;
    superscript?: boolean;
    subscript?: boolean;
    smallCaps?: boolean;
    emphasisMark?: EmphasisMark | 'none' | 'dot' | 'circle' | 'ring' | 'caron' | 'underDot' | 'underLine' | 'triangle';
    relativeSize?: number;
    fontName?: string;
    fontSize?: number;
    color?: string;
    backgroundColor?: string;
}
export interface TabItem {
    pos: number;
    type: TabType;
    leader: LineType2;
}
export interface TabDef {
    id: number;
    autoTabLeft?: boolean;
    autoTabRight?: boolean;
    items: TabItem[];
}
export interface ParaHeadInfo {
    level: number;
    alignment?: AlignmentType2;
    useInstWidth?: boolean;
    autoIndent?: boolean;
    widthAdjust?: number;
    textOffsetType?: 'percent' | 'hwpunit';
    textOffset?: number;
    numFormat?: NumberType1;
    charShape?: number;
    text?: string;
}
export interface NumberingDef {
    id: number;
    start?: number;
    paraHeads: ParaHeadInfo[];
}
export interface BulletDef {
    id: number;
    char?: string;
    image?: boolean;
    useImage?: boolean;
    paraHead?: ParaHeadInfo;
}
export interface ParaShape {
    id: number;
    align?: AlignmentType1;
    verAlign?: 'Baseline' | 'Top' | 'Center' | 'Bottom';
    headingType?: HeadingType;
    heading?: number;
    level?: number;
    tabDef?: number;
    breakLatinWord?: BreakLatinWord;
    breakNonLatinWord?: boolean;
    condense?: number;
    widowOrphan?: boolean;
    keepWithNext?: boolean;
    keepLines?: boolean;
    pageBreakBefore?: boolean;
    fontLineHeight?: boolean;
    snapToGrid?: boolean;
    lineWrap?: LineWrapType;
    autoSpaceEAsianEng?: boolean;
    autoSpaceEAsianNum?: boolean;
    borderFillId?: number;
    margin?: {
        indent?: number;
        left?: number;
        right?: number;
        prev?: number;
        next?: number;
        lineSpacingType?: 'Percent' | 'Fixed' | 'BetweenLines' | 'AtLeast';
        lineSpacing?: number;
    };
    border?: {
        borderFill?: number;
        offsetLeft?: number;
        offsetRight?: number;
        offsetTop?: number;
        offsetBottom?: number;
        connect?: boolean;
        ignoreMargin?: boolean;
    };
    lineSpacing?: number;
    lineSpacingType?: string;
    marginTop?: number;
    marginBottom?: number;
    marginLeft?: number;
    marginRight?: number;
    firstLineIndent?: number;
    tabDefId?: number;
    suppressLineNumbers?: boolean;
    headingLevel?: number;
    widowControl?: boolean;
}
export interface StyleDef {
    id: number;
    type?: 'Para' | 'Char' | 'para' | 'char';
    name?: string;
    engName?: string;
    paraShape?: number;
    charShape?: number;
    nextStyle?: number;
    langId?: number;
    lockForm?: boolean;
    paraPrIdRef?: number;
    charPrIdRef?: number;
    nextStyleIdRef?: number;
}
export interface MemoShape {
    id: number;
    width?: number;
    lineType?: LineType1;
    lineColor?: string;
    fillColor?: string;
    activeColor?: string;
    memoType?: string;
}
export interface CharacterStyle {
    bold?: boolean;
    italic?: boolean;
    underline?: boolean | {
        type: UnderlineType;
        shape: LineType2;
        color: string;
    };
    underlineType?: UnderlineType;
    underlineShape?: LineType2 | UnderlineShape;
    underlineColor?: string;
    strikethrough?: boolean;
    strikeoutShape?: LineType2 | StrikeoutShape;
    strikeoutColor?: string;
    fontName?: string;
    fontSize?: number;
    fontColor?: string;
    backgroundColor?: string;
    superscript?: boolean;
    subscript?: boolean;
    charSpacing?: number | FontRef;
    relativeSize?: number | FontRef;
    charOffset?: number | FontRef;
    emphasisMark?: EmphasisMark;
    useFontSpace?: boolean;
    useKerning?: boolean;
    outline?: LineType3 | {
        type: LineType3;
    };
    shadow?: ShadowType | {
        type: ShadowType;
        color?: string;
        offsetX?: number;
        offsetY?: number;
        alpha?: number;
    };
    shadowX?: number;
    shadowY?: number;
    shadowColor?: string;
    emboss?: boolean;
    engrave?: boolean;
    smallCaps?: boolean;
    allCaps?: boolean;
}
export interface TabInfo {
    width: number;
    leader?: 'none' | 'dot' | 'hyphen' | 'underscore' | 'solid' | 'dash' | 'dashDot' | 'dashDotDot';
}
export interface HyperlinkField {
    fieldType: 'Hyperlink' | 'hyperlink';
    url: string;
    name?: string;
    command?: string;
}
export interface BookmarkField {
    fieldType: 'Bookmark' | 'bookmark';
    bookmarkName: string;
}
export interface MemoField {
    fieldType: 'Memo' | 'memo';
    memoContent?: string;
    author?: string;
    date?: string;
}
export interface FormulaField {
    fieldType: 'Formula' | 'formula';
    formulaScript?: string;
}
export interface FieldControl {
    fieldType: FieldType;
    name?: string;
    instId?: string;
    editable?: boolean;
    dirty?: boolean;
    property?: string;
    command?: string;
    text?: string;
}
export interface TextRun {
    text: string;
    charPrIDRef?: number;
    charStyle?: CharacterStyle;
    tab?: TabInfo;
    hyperlink?: HyperlinkField;
    field?: FieldControl;
    markPen?: {
        color: string;
    };
    hasMemo?: boolean;
    memoId?: string;
    footnoteRef?: number;
    endnoteRef?: number;
}
export interface PageDef {
    landscape?: 0 | 1;
    width?: number;
    height?: number;
    gutterType?: GutterType;
    margin?: {
        left?: number;
        right?: number;
        top?: number;
        bottom?: number;
        header?: number;
        footer?: number;
        gutter?: number;
    };
}
export interface StartNumber {
    pageStartsOn?: PageStartsOn;
    page?: number;
    figure?: number;
    table?: number;
    equation?: number;
}
export interface HideOptions {
    header?: boolean;
    footer?: boolean;
    masterPage?: boolean;
    border?: boolean;
    fill?: boolean;
    pageNumPos?: boolean;
    emptyLine?: boolean;
}
export interface AutoNumFormat {
    type?: NumberType2;
    userChar?: string;
    prefixChar?: string;
    suffixChar?: string;
    superscript?: boolean;
}
export interface NoteLine {
    length?: string;
    type?: LineType1;
    width?: LineWidth | string;
    color?: string;
}
export interface NoteSpacing {
    aboveLine?: number;
    belowLine?: number;
    betweenNotes?: number;
}
export interface NoteNumbering {
    type?: NoteNumberingType;
    newNumber?: number;
}
export interface NotePlacementInfo {
    place?: NotePlacement;
    beneathText?: boolean;
}
export interface FootnoteShape {
    autoNumFormat?: AutoNumFormat;
    noteLine?: NoteLine;
    noteSpacing?: NoteSpacing;
    noteNumbering?: NoteNumbering;
    notePlacement?: NotePlacementInfo;
}
export interface PageBorderFill {
    type?: PageStartsOn;
    borderFill?: number;
    textBorder?: boolean;
    headerInside?: boolean;
    footerInside?: boolean;
    fillArea?: 'Paper' | 'Page' | 'Border';
    offset?: {
        left?: number;
        right?: number;
        top?: number;
        bottom?: number;
    };
}
export interface MasterPage {
    type?: PageStartsOn;
    textWidth?: number;
    textHeight?: number;
    hasTextRef?: boolean;
    hasNumRef?: boolean;
    paragraphs?: HwpxParagraph[];
    isExtended?: boolean;
    pageNumber?: number;
    pageDuplicate?: boolean;
    pageFront?: boolean;
}
export interface SectionDef {
    textDirection?: 0 | 1;
    spaceColumns?: number;
    tabStop?: number;
    outlineShape?: number;
    lineGrid?: number;
    charGrid?: number;
    firstBorder?: boolean;
    firstFill?: boolean;
    extMasterpageCount?: number;
    memoShapeId?: number;
    pageDef?: PageDef;
    startNumber?: StartNumber;
    hide?: HideOptions;
    footnoteShape?: FootnoteShape;
    endnoteShape?: FootnoteShape;
    pageBorderFill?: PageBorderFill[];
    masterPage?: MasterPage[];
}
export interface ColumnLine {
    type?: LineType1;
    width?: LineWidth | string;
    color?: string;
}
export interface Column {
    width?: number;
    gap?: number;
}
export interface ColumnDef {
    type?: ColumnType;
    count?: number;
    layout?: ColumnLayout;
    sameSize?: boolean;
    sameGap?: number;
    columnLine?: ColumnLine;
    columns?: Column[];
}
export interface ShapeSize {
    width: number;
    height: number;
    widthRelTo?: SizeRelTo;
    heightRelTo?: SizeRelTo;
    protect?: boolean;
}
export interface ShapePosition {
    treatAsChar?: boolean;
    affectLSpacing?: boolean;
    vertRelTo?: VertRelTo;
    vertAlign?: VertAlign;
    horzRelTo?: HorzRelTo;
    horzAlign?: HorzAlign;
    vertOffset?: number;
    horzOffset?: number;
    flowWithText?: boolean;
    allowOverlap?: boolean;
    holdAnchorAndSO?: boolean;
}
export interface ObjectMargin {
    left: number;
    right: number;
    top: number;
    bottom: number;
}
export interface Caption {
    side?: 'Left' | 'Right' | 'Top' | 'Bottom';
    fullSize?: boolean;
    width?: number;
    gap?: number;
    lastWidth?: number;
    paragraphs?: HwpxParagraph[];
}
export interface ShapeObject {
    instId?: string;
    zOrder?: number;
    numberingType?: NumberingType;
    textWrap?: TextWrapType;
    textFlow?: TextFlowType;
    lock?: boolean;
    size?: ShapeSize;
    position?: ShapePosition;
    outMargin?: ObjectMargin;
    caption?: Caption;
    shapeComment?: string;
}
export interface CellZone {
    startRowAddr: number;
    startColAddr: number;
    endRowAddr: number;
    endColAddr: number;
    borderFill?: number;
}
export interface CellMargin {
    left?: number;
    right?: number;
    top?: number;
    bottom?: number;
}
export type CellElement = {
    type: 'paragraph';
    data: HwpxParagraph;
} | {
    type: 'table';
    data: HwpxTable;
};
export interface TableCell {
    name?: string;
    colAddr?: number;
    rowAddr?: number;
    colSpan?: number;
    rowSpan?: number;
    width?: number;
    height?: number;
    header?: boolean;
    hasMargin?: boolean;
    protect?: boolean;
    editable?: boolean;
    dirty?: boolean;
    borderFillId?: number;
    paragraphs: HwpxParagraph[];
    nestedTables?: HwpxTable[];
    elements?: CellElement[];
    backgroundColor?: string;
    backgroundGradation?: {
        type: GradationType;
        angle?: number;
        colors: string[];
    };
    borderTop?: BorderStyle;
    borderBottom?: BorderStyle;
    borderLeft?: BorderStyle;
    borderRight?: BorderStyle;
    verticalAlign?: 'top' | 'middle' | 'bottom';
    marginTop?: number;
    marginBottom?: number;
    marginLeft?: number;
    marginRight?: number;
    textDirection?: 'horizontal' | 'vertical';
    lineWrap?: LineWrapType;
}
export interface TableRow {
    cells: TableCell[];
    height?: number;
}
export interface HwpxTable {
    id: string;
    pageBreak?: PageBreakType;
    repeatHeader?: boolean;
    rowCount?: number;
    colCount?: number;
    rowCnt?: number;
    colCnt?: number;
    cellSpacing?: number;
    borderFillId?: number;
    shapeObject?: ShapeObject;
    inMargin?: ObjectMargin;
    cellZoneList?: CellZone[];
    rows: TableRow[];
    width?: number;
    height?: number;
    columnWidths?: number[];
    borderCollapse?: boolean;
    zOrder?: number;
    numberingType?: NumberingType;
    textWrap?: TextWrapType;
    textFlow?: TextFlowType;
    position?: ShapePosition;
    outMargin?: ObjectMargin;
    lock?: boolean;
    linesegs?: LineSeg[];
}
export interface ShapeComponent {
    hRef?: string;
    xPos?: number;
    yPos?: number;
    groupLevel?: number;
    oriWidth?: number;
    oriHeight?: number;
    curWidth?: number;
    curHeight?: number;
    horzFlip?: boolean;
    vertFlip?: boolean;
    instId?: string;
    rotationInfo?: {
        angle: number;
        centerX?: number;
        centerY?: number;
    };
    renderingInfo?: {
        transMatrix?: number[];
        scaMatrix?: number[];
        rotMatrix?: number[];
    };
}
export interface LineShape {
    color?: string;
    width?: number;
    style?: LineType1;
    endCap?: 'Round' | 'Flat';
    headStyle?: ArrowType;
    tailStyle?: ArrowType;
    headSize?: ArrowSize;
    tailSize?: ArrowSize;
    outlineStyle?: 'Normal' | 'Outer' | 'Inner';
    alpha?: number;
}
export interface ImageRect {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    x3?: number;
    y3?: number;
}
export interface ImageClip {
    left: number;
    top: number;
    right: number;
    bottom: number;
}
export interface ShadowEffect {
    style?: string;
    alpha?: number;
    radius?: number;
    direction?: number;
    distance?: number;
    alignStyle?: string;
    skewX?: number;
    skewY?: number;
    scaleX?: number;
    scaleY?: number;
    rotationStyle?: string;
    color?: string;
}
export interface GlowEffect {
    alpha?: number;
    radius?: number;
    color?: string;
}
export interface SoftEdgeEffect {
    radius?: number;
}
export interface ReflectionEffect {
    alignStyle?: string;
    radius?: number;
    direction?: number;
    distance?: number;
    skewX?: number;
    skewY?: number;
    scaleX?: number;
    scaleY?: number;
    rotationStyle?: string;
    startAlpha?: number;
    startPos?: number;
    endAlpha?: number;
    endPos?: number;
    fadeDirection?: number;
}
export interface ImageEffects {
    shadow?: ShadowEffect;
    glow?: GlowEffect;
    softEdge?: SoftEdgeEffect;
    reflection?: ReflectionEffect;
}
export interface HwpxImage {
    id: string;
    binaryId: string;
    width: number;
    height: number;
    orgWidth?: number;
    orgHeight?: number;
    reverse?: boolean;
    shapeObject?: ShapeObject;
    shapeComponent?: ShapeComponent;
    lineShape?: LineShape;
    imageRect?: ImageRect;
    imageClip?: ImageClip;
    effects?: ImageEffects;
    inMargin?: ObjectMargin;
    data?: string;
    mimeType?: string;
    alt?: string;
    zOrder?: number;
    numberingType?: NumberingType;
    textWrap?: TextWrapType;
    textFlow?: TextFlowType;
    position?: ShapePosition;
    outMargin?: ObjectMargin;
    flip?: {
        horizontal?: boolean;
        vertical?: boolean;
    };
    rotation?: {
        angle?: number;
        centerX?: number;
        centerY?: number;
    };
    brightness?: number;
    contrast?: number;
    alpha?: number;
    effect?: string;
    shapeComment?: string;
}
export interface DrawingObject {
    shapeComponent?: ShapeComponent;
    lineShape?: LineShape;
    fillBrush?: FillBrush;
    drawText?: {
        lastWidth?: number;
        name?: string;
        editable?: boolean;
        textMargin?: ObjectMargin;
        paragraphs?: HwpxParagraph[];
    };
    shadow?: {
        type?: ShadowType;
        color?: string;
        offsetX?: number;
        offsetY?: number;
        alpha?: number;
    };
}
export interface HwpxLine {
    id: string;
    startX?: number;
    startY?: number;
    endX?: number;
    endY?: number;
    isReverseHV?: boolean;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
    strokeColor?: string;
    strokeWidth?: number;
    strokeStyle?: 'solid' | 'dashed' | 'dotted';
}
export interface HwpxRect {
    id: string;
    ratio?: number;
    x0?: number;
    y0?: number;
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
    x3?: number;
    y3?: number;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
    fillColor?: string;
    strokeColor?: string;
    strokeWidth?: number;
    cornerRadius?: number;
}
export interface HwpxEllipse {
    id: string;
    intervalDirty?: boolean;
    hasArcProperty?: boolean;
    arcType?: ArcType;
    centerX?: number;
    centerY?: number;
    axis1X?: number;
    axis1Y?: number;
    axis2X?: number;
    axis2Y?: number;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
    cx?: number;
    cy?: number;
    rx?: number;
    ry?: number;
    fillColor?: string;
    strokeColor?: string;
    strokeWidth?: number;
}
export interface HwpxArc {
    id: string;
    type?: ArcType;
    centerX: number;
    centerY: number;
    axis1X?: number;
    axis1Y?: number;
    axis2X?: number;
    axis2Y?: number;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
}
export interface HwpxPolygon {
    id: string;
    points: Array<{
        x: number;
        y: number;
    }>;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
}
export interface CurveSegment {
    type: 'Line' | 'Curve';
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}
export interface HwpxCurve {
    id: string;
    segments: CurveSegment[];
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
}
export interface HwpxConnectLine {
    id: string;
    type?: string;
    startX?: number;
    startY?: number;
    endX?: number;
    endY?: number;
    startSubjectID?: string;
    startSubjectIndex?: number;
    endSubjectID?: string;
    endSubjectIndex?: number;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
}
export interface HwpxTextBox {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    paragraphs: HwpxParagraph[];
    fillColor?: string;
    strokeColor?: string;
    strokeWidth?: number;
}
export interface HwpxHorizontalRule {
    id: string;
    width: number | 'full';
    height: number;
    color?: string;
    style?: 'solid' | 'dashed' | 'dotted' | 'double';
    align?: 'left' | 'center' | 'right';
}
export interface FormCharShape {
    charShape?: number;
    followContext?: boolean;
    autoSize?: boolean;
    wordWrap?: boolean;
}
export interface ButtonSet {
    caption?: string;
    value?: string;
    radioGroupName?: string;
    triState?: boolean;
    backStyle?: string;
}
export interface FormObject {
    name?: string;
    foreColor?: string;
    backColor?: string;
    groupName?: string;
    tabStop?: boolean;
    tabOrder?: number;
    enabled?: boolean;
    borderType?: number;
    drawFrame?: boolean;
    printable?: boolean;
    formCharShape?: FormCharShape;
    buttonSet?: ButtonSet;
}
export interface HwpxButton {
    id: string;
    shapeObject?: ShapeObject;
    formObject?: FormObject;
}
export interface HwpxRadioButton extends HwpxButton {
}
export interface HwpxCheckButton extends HwpxButton {
}
export interface HwpxComboBox {
    id: string;
    listBoxRows?: number;
    listBoxWidth?: number;
    text?: string;
    editEnable?: boolean;
    shapeObject?: ShapeObject;
    formObject?: FormObject;
}
export interface HwpxEdit {
    id: string;
    multiLine?: boolean;
    passwordChar?: string;
    maxLength?: number;
    scrollBars?: boolean;
    tabKeyBehavior?: string;
    number?: boolean;
    readOnly?: boolean;
    alignText?: string;
    text?: string;
    shapeObject?: ShapeObject;
    formObject?: FormObject;
}
export interface HwpxListBox {
    id: string;
    text?: string;
    itemHeight?: number;
    topIndex?: number;
    shapeObject?: ShapeObject;
    formObject?: FormObject;
}
export interface HwpxScrollBar {
    id: string;
    delay?: number;
    largeChange?: number;
    smallChange?: number;
    min?: number;
    max?: number;
    page?: number;
    value?: number;
    type?: string;
    shapeObject?: ShapeObject;
    formObject?: FormObject;
}
export interface HwpxUnknownObject {
    id: string;
    ctrlId?: string;
    x0?: number;
    y0?: number;
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
    x3?: number;
    y3?: number;
    shapeObject?: ShapeObject;
    drawingObject?: DrawingObject;
}
export type ParameterItemType = 'Bstr' | 'Integer' | 'Set' | 'Array' | 'BinData';
export interface ParameterItem {
    itemId: string;
    type: ParameterItemType;
    value?: string | number;
    parameterSet?: ParameterSet;
    parameterArray?: ParameterArray;
}
export interface ParameterSet {
    setId?: string;
    count?: number;
    items: ParameterItem[];
}
export interface ParameterArray {
    count?: number;
    items: ParameterItem[];
}
export interface HwpxContainer {
    id: string;
    shapeObject?: ShapeObject;
    shapeComponent?: ShapeComponent;
    children: Array<HwpxLine | HwpxRect | HwpxEllipse | HwpxArc | HwpxPolygon | HwpxCurve | HwpxImage | HwpxContainer>;
}
export interface HwpxOle {
    id: string;
    objectType?: OleObjectType;
    extentX?: number;
    extentY?: number;
    binItem?: string;
    drawAspect?: DrawAspect;
    hasMoniker?: boolean;
    eqBaseLine?: number;
    shapeObject?: ShapeObject;
    shapeComponent?: ShapeComponent;
    lineShape?: LineShape;
}
export interface HwpxEquation {
    id: string;
    lineMode?: boolean;
    baseUnit?: number;
    textColor?: string;
    baseLine?: number;
    version?: string;
    script?: string;
    shapeObject?: ShapeObject;
}
export interface HwpxTextArt {
    id: string;
    text?: string;
    x0?: number;
    y0?: number;
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
    x3?: number;
    y3?: number;
    shape?: {
        fontName?: string;
        fontStyle?: string;
        fontType?: 'ttf' | 'htf';
        textShape?: number;
        lineSpacing?: number;
        charSpacing?: number;
        align?: AlignmentType1;
        shadow?: {
            type?: ShadowType;
            color?: string;
            offsetX?: number;
            offsetY?: number;
            alpha?: number;
        };
    };
    outlineData?: Array<{
        x: number;
        y: number;
    }>;
}
export interface HwpxHyperlink {
    url: string;
    text: string;
}
export interface Bookmark {
    name: string;
}
export interface AutoNum {
    number?: number;
    numberType?: 'Page' | 'Footnote' | 'Endnote' | 'Figure' | 'Table' | 'Equation' | 'TotalPage';
    format?: AutoNumFormat;
}
export interface NewNum extends AutoNum {
}
export interface PageNumCtrl {
    pageStartsOn?: PageStartsOn;
}
export interface PageHiding {
    hideHeader?: boolean;
    hideFooter?: boolean;
    hideMasterPage?: boolean;
    hideBorder?: boolean;
    hideFill?: boolean;
    hidePageNum?: boolean;
}
export interface PageNum {
    pos?: 'None' | 'TopLeft' | 'TopCenter' | 'TopRight' | 'BottomLeft' | 'BottomCenter' | 'BottomRight' | 'OutsideTop' | 'OutsideBottom' | 'InsideTop' | 'InsideBottom';
    formatType?: NumberType1;
    sideChar?: string;
}
export interface IndexMark {
    keyFirst?: string;
    keySecond?: string;
}
export interface Compose {
    circleType?: number;
    charSize?: number;
    composeType?: number;
    charShapeIds?: number[];
}
export interface Dutmal {
    posType?: 'Top' | 'Bottom';
    sizeRatio?: number;
    option?: number;
    styleNo?: number;
    align?: AlignmentType1;
    mainText?: string;
    subText?: string;
}
export interface HiddenComment {
    paragraphs: HwpxParagraph[];
}
export interface ParagraphStyle {
    align?: 'left' | 'center' | 'right' | 'justify' | 'distribute';
    lineSpacing?: number;
    lineSpacingType?: 'percent' | 'fixed' | 'betweenLines' | 'atLeast';
    marginTop?: number;
    marginBottom?: number;
    marginLeft?: number;
    marginRight?: number;
    firstLineIndent?: number;
    tabDefId?: number;
    condense?: number;
    breakLatinWord?: BreakLatinWord;
    breakNonLatinWord?: boolean;
    snapToGrid?: boolean;
    suppressLineNumbers?: boolean;
    headingType?: HeadingType;
    headingLevel?: number;
    borderFillId?: number;
    autoSpaceEAsianEng?: boolean;
    autoSpaceEAsianNum?: boolean;
    keepWithNext?: boolean;
    keepLines?: boolean;
    pageBreakBefore?: boolean;
    widowControl?: boolean;
}
export interface LineSeg {
    vertpos: number;
    vertsize: number;
    textheight: number;
    baseline: number;
    spacing: number;
}
export interface HwpxParagraph {
    id: string;
    paraPrId?: number;
    style?: number;
    instId?: string;
    pageBreak?: boolean;
    columnBreak?: boolean;
    runs: TextRun[];
    paraStyle?: ParagraphStyle;
    listType?: 'none' | 'bullet' | 'number';
    listLevel?: number;
    linesegs?: LineSeg[];
    _xmlPosition?: {
        sectionIndex: number;
        start: number;
        end: number;
    };
}
export interface HeaderFooter {
    applyPageType?: PageStartsOn;
    seriesNum?: number;
    paragraphs: HwpxParagraph[];
}
export interface Footnote {
    id: string;
    number?: number;
    type?: 'footnote' | 'endnote';
    paragraphs: HwpxParagraph[];
}
export interface Endnote {
    id: string;
    number?: number;
    paragraphs: HwpxParagraph[];
}
export type SectionElement = {
    type: 'paragraph';
    data: HwpxParagraph;
} | {
    type: 'table';
    data: HwpxTable;
} | {
    type: 'image';
    data: HwpxImage;
} | {
    type: 'line';
    data: HwpxLine;
} | {
    type: 'rect';
    data: HwpxRect;
} | {
    type: 'ellipse';
    data: HwpxEllipse;
} | {
    type: 'arc';
    data: HwpxArc;
} | {
    type: 'polygon';
    data: HwpxPolygon;
} | {
    type: 'curve';
    data: HwpxCurve;
} | {
    type: 'connectline';
    data: HwpxConnectLine;
} | {
    type: 'textbox';
    data: HwpxTextBox;
} | {
    type: 'equation';
    data: HwpxEquation;
} | {
    type: 'ole';
    data: HwpxOle;
} | {
    type: 'container';
    data: HwpxContainer;
} | {
    type: 'textart';
    data: HwpxTextArt;
} | {
    type: 'unknownobject';
    data: HwpxUnknownObject;
} | {
    type: 'hr';
    data: HwpxHorizontalRule;
} | {
    type: 'button';
    data: HwpxButton;
} | {
    type: 'radiobutton';
    data: HwpxRadioButton;
} | {
    type: 'checkbutton';
    data: HwpxCheckButton;
} | {
    type: 'combobox';
    data: HwpxComboBox;
} | {
    type: 'edit';
    data: HwpxEdit;
} | {
    type: 'listbox';
    data: HwpxListBox;
} | {
    type: 'scrollbar';
    data: HwpxScrollBar;
};
export interface PageSettings {
    width: number;
    height: number;
    marginTop: number;
    marginBottom: number;
    marginLeft: number;
    marginRight: number;
    headerMargin?: number;
    footerMargin?: number;
    gutterMargin?: number;
    orientation?: 'portrait' | 'landscape';
    gutterType?: GutterType;
}
export interface SectionProperties {
    textDirection?: 'horizontal' | 'vertical';
    spaceColumns?: number;
    tabStop?: number;
    outlineShapeIdRef?: number;
    memoShapeIdRef?: number;
    masterPageCnt?: number;
    masterPage?: MasterPage[];
    grid?: {
        lineGrid?: number;
        charGrid?: number;
        wonggojiFormat?: number;
    };
    startNum?: {
        pageStartsOn?: PageStartsOn;
        page?: number;
        pic?: number;
        tbl?: number;
        equation?: number;
    };
    visibility?: {
        hideFirstHeader?: boolean;
        hideFirstFooter?: boolean;
        hideFirstMasterPage?: boolean;
        border?: 'showAll' | 'hideAll' | 'showFirstPageOnly' | 'showAllButFirstPage';
        fill?: 'showAll' | 'hideAll' | 'showFirstPageOnly' | 'showAllButFirstPage';
        hideFirstPageNum?: boolean;
        hideFirstEmptyLine?: boolean;
        showLineNumber?: boolean;
    };
    pageBorderFill?: Array<{
        type?: PageStartsOn;
        borderFillIdRef?: number;
        textBorder?: 'paper' | 'page' | 'content';
        headerInside?: boolean;
        footerInside?: boolean;
        fillArea?: 'paper' | 'page' | 'content';
        offset?: ObjectMargin;
    }>;
}
export interface FootnoteEndnoteProperties {
    autoNumFormat?: {
        type?: NumberType2;
        userChar?: string;
        prefixChar?: string;
        suffixChar?: string;
        superscript?: boolean;
    };
    noteLine?: {
        length?: number;
        type?: LineType1;
        width?: LineWidth | string;
        color?: string;
    };
    noteSpacing?: {
        betweenNotes?: number;
        belowLine?: number;
        aboveLine?: number;
    };
    numbering?: {
        type?: NoteNumberingType;
        newNum?: number;
    };
    placement?: {
        place?: NotePlacement;
        beneathText?: boolean;
    };
}
export interface Memo {
    id: string;
    author: string;
    date: string;
    content: string[];
    linkedText?: string;
}
export interface HwpxSection {
    id?: string;
    elements: SectionElement[];
    pageSettings?: PageSettings;
    sectionProperties?: SectionProperties;
    sectionDef?: SectionDef;
    columnDef?: ColumnDef;
    footnoteProperties?: FootnoteEndnoteProperties;
    endnoteProperties?: FootnoteEndnoteProperties;
    header?: HeaderFooter;
    footer?: HeaderFooter;
    memos?: Memo[];
}
export interface HwpxMetadata {
    title?: string;
    subject?: string;
    creator?: string;
    createdDate?: string;
    modifiedDate?: string;
    description?: string;
    keywords?: string[];
    comments?: string;
    forbiddenStrings?: string[];
}
export interface DocSetting {
    beginNumber?: {
        page?: number;
        footnote?: number;
        endnote?: number;
        picture?: number;
        table?: number;
        equation?: number;
        totalPage?: number;
    };
    caretPos?: {
        list?: string;
        para?: string;
        pos?: string;
    };
}
export interface HwpxStyles {
    charShapes: Map<number, CharShape>;
    paraShapes: Map<number, ParaShape>;
    fonts: Map<number, string>;
    fontsByLang: Map<string, string>;
    borderFills: Map<number, BorderFillStyle>;
    tabDefs: Map<number, TabDef>;
    numberings: Map<number, NumberingDef>;
    bullets: Map<number, BulletDef>;
    styles: Map<number, StyleDef>;
    memoShapes: Map<number, MemoShape>;
}
export interface BinItem {
    type: 'Link' | 'Embedding' | 'Storage';
    aPath?: string;
    rPath?: string;
    binData?: string;
    format?: 'jpg' | 'bmp' | 'gif' | 'png' | 'ole';
}
export interface BinData {
    id: string;
    size?: number;
    encoding?: 'Base64';
    compress?: boolean;
    data: string;
}
export type HwpmlStyle = 'embed' | 'export';
export interface HwpmlRoot {
    version?: string;
    subVersion?: string;
    style2?: HwpmlStyle;
    head?: HwpmlHead;
    body?: HwpmlBody;
    tail?: HwpmlTail;
}
export interface HwpmlHead {
    secCnt?: number;
    docSummary?: HwpxMetadata;
    docSetting?: DocSetting;
    mappingTable?: HwpxStyles;
    compatibleDocument?: CompatibleDocument;
}
export interface HwpmlBody {
    sections: HwpxSection[];
}
export interface HwpmlTail {
    binDataStorage?: BinDataStorage;
    scriptCode?: ScriptCode;
    xmlTemplate?: XmlTemplate;
}
export interface BinDataStorage {
    binData: BinData[];
}
export interface ScriptCode {
    type?: 'JScript';
    version?: string;
    header?: string;
    source?: string;
    preScript?: ScriptFunction[];
    postScript?: ScriptFunction[];
}
export interface ScriptFunction {
    name?: string;
    code: string;
}
export interface XmlTemplate {
    schema?: string;
    instance?: string;
}
export interface CompatibleDocument {
    targetProgram?: 'None' | 'Hwp70' | 'Word';
    layoutCompatibility?: LayoutCompatibility;
}
export interface LayoutCompatibility {
    applyFontWeightToBold?: boolean;
    useInnerUnderline?: boolean;
    fixedUnderlineWidth?: boolean;
    doNotApplyStrikeout?: boolean;
    useLowercaseStrikeout?: boolean;
    extendLineheightToOffset?: boolean;
    treatQuotationAsLatin?: boolean;
    doNotAlignWhitespaceOnRight?: boolean;
    doNotAdjustWordInJustify?: boolean;
    baseCharUnitOnEAsian?: boolean;
    baseCharUnitOfIndentOnFirstChar?: boolean;
    adjustLineheightToFont?: boolean;
    adjustBaselineInFixedLinespacing?: boolean;
    excludeOverlappingParaSpacing?: boolean;
    applyNextspacingOfLastPara?: boolean;
    applyAtLeastToPercent100Pct?: boolean;
    doNotApplyAutoSpaceEAsianEng?: boolean;
    doNotApplyAutoSpaceEAsianNum?: boolean;
    adjustParaBorderfillToSpacing?: boolean;
    connectParaBorderfillOfEqualBorder?: boolean;
    adjustParaBorderOffsetWithBorder?: boolean;
    extendLineheightToParaBorderOffset?: boolean;
    applyParaBorderToOutside?: boolean;
    baseLinespacingOnLinegrid?: boolean;
    applyCharSpacingToCharGrid?: boolean;
    doNotApplyGridInHeaderfooter?: boolean;
    extendHeaderfooterToBody?: boolean;
    adjustEndnotePositionToFootnote?: boolean;
    doNotApplyImageEffect?: boolean;
    doNotApplyShapeComment?: boolean;
    doNotAdjustEmptyAnchorLine?: boolean;
    overlapBothAllowOverlap?: boolean;
    doNotApplyVertOffsetOfForward?: boolean;
    extendVertLimitToPageMargins?: boolean;
    doNotHoldAnchorOfTable?: boolean;
    doNotFormattingAtBeneathAnchor?: boolean;
    doNotApplyExtensionCharCompose?: boolean;
}
export interface HwpxContent {
    metadata: HwpxMetadata;
    docSetting?: DocSetting;
    sections: HwpxSection[];
    images: Map<string, HwpxImage>;
    binItems: Map<string, BinItem>;
    binData: Map<string, BinData>;
    footnotes: Footnote[];
    endnotes: Endnote[];
    styles?: HwpxStyles;
    hwpmlVersion?: string;
    hwpmlSubVersion?: string;
    hwpmlStyle?: HwpmlStyle;
    compatibleDocument?: CompatibleDocument;
}
export type UnderlineShape = 'solid' | 'dash' | 'dot' | 'dashDot' | 'dashDotDot' | 'long' | 'thick' | 'double' | 'wave' | 'doubleWave' | 'thickWave';
export type StrikeoutShape = 'none' | 'continuous' | 'dash' | 'dot' | 'dashDot' | 'dashDotDot' | 'double' | '3D';
export type OutlineType = 'none' | 'solid' | 'dot' | 'dash' | 'dashDot' | 'dashDotDot' | 'thick' | 'double' | 'triple' | 'thin';
export type BreakWordType = 'normal' | 'hyphenation' | 'breakWord' | 'keepWord';
export type FillType = 'none' | 'color' | 'gradation' | 'image';
export type ImageFillMode = 'tile' | 'tileHorz' | 'tileVert' | 'totalFit' | 'fit' | 'center' | 'onceAbsoluteScale';
export type TabLeader = 'none' | 'solid' | 'dash' | 'dot' | 'dashDot' | 'dashDotDot';
export type NumFormat = 'digit' | 'romanCapital' | 'romanSmall' | 'latinCapital' | 'latinSmall' | 'hangulSyllable' | 'hangulJamo' | 'circledDigit' | 'decimalEnclosedInParentheses';
export type NumberingType = 'None' | 'Figure' | 'Table' | 'Equation' | 'Picture' | 'none' | 'figure' | 'table' | 'equation' | 'picture';
export interface FontRef {
    hangul?: number;
    latin?: number;
    hanja?: number;
    japanese?: number;
    other?: number;
    symbol?: number;
    user?: number;
}
