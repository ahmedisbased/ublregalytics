import {
    useEffect,
    useLayoutEffect,
    useRef,
    useState,
    type ChangeEvent,
    type KeyboardEvent,
    type ReactNode,
} from 'react';
import {
    FaBalanceScale,
    FaCheckCircle,
    FaChevronLeft,
    FaChevronRight,
    FaEdit,
    FaExclamationCircle,
    FaFlag,
    FaLink,
    FaLock,
    FaPlay,
    FaPlus,
    FaSave,
    FaSearch,
    FaStop,
} from 'react-icons/fa';
import {
    batchUpdateAllRcoa,
    endRcoaReporting,
    fetchRcoaMetadata,
    fetchRcoaPage,
    getCurrentUser,
    insertRcoaRow,
    startRcoaReporting,
    type RcoaMetadataResponse,
    type RcoaMode,
    type RcoaRow,
} from '../../services/rcoaService';
import './rcoa.scss';

type ColumnFormat = 'text' | 'amount' | 'flag';

type RcoaColumn = {
    key: string;
    keys?: string[];
    label: string;
    editable?: boolean;
    code?: boolean;
    numeric?: boolean;
    format?: ColumnFormat;
};

type EditorField = {
    key: string;
    label: string;
    type?: 'text' | 'number';
    step?: string;
    sourceKeys?: string[];
};

type RcoaModeDefinition = {
    label: string;
    description: string;
    tableName: string;
    icon: ReactNode;
    columns: RcoaColumn[];
    fields: EditorField[];
    insertFields?: EditorField[];
    getRowKey: (row: RcoaRow) => string;
    buildPayload: (
        row: RcoaRow,
        draft: Record<string, string>,
        date: string,
    ) => Record<string, unknown>;
    buildInsertPayload?: (
        draft: Record<string, string>,
        date: string,
    ) => Record<string, unknown>;
};

type PendingChange = {
    mode: RcoaMode;
    rowKey: string;
    payload: Record<string, unknown>;
    values: Record<string, string>;
};

type EditMode = 'modal' | 'inline';
type ReportingStatus = 'not_started' | 'in_progress' | 'ending' | 'completed' | 'failed';

const today = new Date();

const toDateInputValue = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const todayValue = toDateInputValue(today);


const getEditWindowStart = () => {
    const targetMonth = today.getMonth() - 1;
    const lastDayOfTargetMonth = new Date(today.getFullYear(), targetMonth + 1, 0).getDate();
    const targetDay = Math.min(today.getDate(), lastDayOfTargetMonth);
    return toDateInputValue(new Date(today.getFullYear(), targetMonth, targetDay));
};

const editWindowStart = getEditWindowStart();

const toLocalDateTimestamp = (value: string) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return Number.NaN;

    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const date = new Date(year, month - 1, day);

    if (
        date.getFullYear() !== year
        || date.getMonth() !== month - 1
        || date.getDate() !== day
    ) {
        return Number.NaN;
    }

    return date.getTime();
};

const todayTimestamp = toLocalDateTimestamp(todayValue);
const editWindowStartTimestamp = toLocalDateTimestamp(editWindowStart);





const readRowValue = (row: RcoaRow, ...keys: string[]) => {
    for (const key of keys) {
        const candidates = [key, key.toUpperCase(), key.toLowerCase()];
        for (const candidate of candidates) {
            const value = row[candidate];
            if (value !== null && value !== undefined) {
                return String(value);
            }
        }

        const matchingKey = Object.keys(row).find((rowKey) => rowKey.toUpperCase() === key.toUpperCase());
        if (matchingKey) {
            const value = row[matchingKey];
            if (value !== null && value !== undefined) return String(value);
        }
    }
    return '';
};

const displayValue = (value: string) => value || '--';

const formatAmount = (value: string) => {
    if (!value) return '--';
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) return value;
    return new Intl.NumberFormat('en-US', {
        maximumFractionDigits: 2,
    }).format(numericValue);
};

const requiredDraftValue = (draft: Record<string, string>, key: string, label: string) => {
    const value = draft[key]?.trim() ?? '';
    if (!value) throw new Error(`${label} is required.`);
    return value;
};

const isNumericDraftValue = (field: EditorField, value: string, allowPartial = false) => {
    if (field.type !== 'number') return true;
    if (field.step === '1') return /^\d*$/.test(value);
    return allowPartial
        ? /^-?\d*(?:\.\d*)?$/.test(value)
        : /^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value);
};

const isCustomerNameField = (field: EditorField) => field.key === 'cust_name';
const CUSTOMER_NAME_PATTERN = /^[A-Za-z]+$/;
const CUSTOMER_NAME_INPUT_PATTERN = '[A-Za-z]*';
const CUSTOMER_NAME_ERROR = 'Customer name must contain only letters A-Z.';
const normalizeCustomerName = (value: string) => value.replace(/[^A-Za-z]/g, '');
const isValidCustomerName = (value: string) => CUSTOMER_NAME_PATTERN.test(value);

const getEditorInputType = (field: EditorField) => field.type === 'number' ? 'text' : field.type ?? 'text';

const EXPANDABLE_TEXT_FIELDS = new Set(['description', 'particulars', 'particulars_definition']);
const isExpandableTextField = (field: EditorField) => (
    field.type !== 'number' && EXPANDABLE_TEXT_FIELDS.has(field.key)
);

type AutoGrowingTextareaProps = {
    className?: string;
    value: string;
    ariaLabel?: string;
    disabled?: boolean;
    onChange: (event: ChangeEvent<HTMLTextAreaElement>) => void;
    onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

const AutoGrowingTextarea = ({
    className,
    value,
    ariaLabel,
    disabled,
    onChange,
    onKeyDown,
}: AutoGrowingTextareaProps) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useLayoutEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 320)}px`;
    }, [value]);

    return (
        <textarea
            ref={textareaRef}
            className={className}
            rows={1}
            value={value}
            aria-label={ariaLabel}
            disabled={disabled}
            onChange={onChange}
            onKeyDown={onKeyDown}
        />
    );
};

const getDraftForFields = (row: RcoaRow, fields: EditorField[]) => fields.reduce<Record<string, string>>(
    (draft, field) => {
        draft[field.key] = readRowValue(row, ...(field.sourceKeys ?? [field.key.toUpperCase()]));
        return draft;
    },
    {},
);

const getRowKey = (row: RcoaRow, keys: string[]) => JSON.stringify(
    keys.map((key) => readRowValue(row, key)),
);

const normalizeColumnKey = (key: string) => key.toUpperCase();

const formatColumnLabel = (key: string) => key
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());

const getTableColumns = (
    rows: RcoaRow[],
    definition: RcoaModeDefinition,
    rcoaMetadata: RcoaMetadataResponse | null,
) => {
    const configuredColumns = new Map(
        definition.columns.flatMap((column) => [column, ...(column.keys ?? []).map((key) => ({ ...column, key }))])
            .map((column) => [normalizeColumnKey(column.key), column] as const),
    );
    const returnedColumns = new Map(
        rows.flatMap((row) => Object.keys(row))
            .map((key) => [normalizeColumnKey(key), key] as const),
    );
    const metadata = rcoaMetadata?.tables[definition.tableName];
    if (!metadata) return [];

    return metadata.columns.map((metadataColumn): RcoaColumn => {
        const normalizedName = normalizeColumnKey(metadataColumn.name);
        const configuredColumn = configuredColumns.get(normalizedName);
        const returnedKey = returnedColumns.get(normalizedName);
        return configuredColumn ?? {
            key: returnedKey ?? metadataColumn.name,
            label: formatColumnLabel(metadataColumn.name),
            code: /(_CODE|_ID|_NO)$/i.test(metadataColumn.name),
        };
    });
};

const modeOrder: RcoaMode[] = [
    'gl-sl-mapping',
    'term-deposits',
    'loan-type',
    'sl-roca',
    'tfcs-sukus',
    'rcoa-manual-data',
    'adjustment',
];

const modeLabels: Record<RcoaMode, RcoaModeDefinition> = {
    'gl-sl-mapping': {
        label: 'GL-SL mapping',
        description: 'Connect general-ledger accounts to subsidiary-ledger codes.',
        tableName: 'DT_SDMT_UBL.GL_SL_MAPPING',
        icon: <FaLink />,
        columns: [
            { key: 'GL_EDW_ID', label: 'GL code', code: true },
            { key: 'GL_DESCRIPTION', label: 'GL description' },
            { key: 'CURY_EDW_ID', label: 'Currency / GL name' },
            { key: 'SL_CODE', label: 'SL code', code: true, numeric: true, editable: true },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [{ key: 'sl_code', label: 'SL code', type: 'number', step: '1' }],
        getRowKey: (row) => getRowKey(row, ['GL_EDW_ID', 'CURY_EDW_ID', 'START_DATE']),
        buildPayload: (row, draft, date) => ({
            gl_edw_id: readRowValue(row, 'GL_EDW_ID'),
            cury_edw_id: readRowValue(row, 'CURY_EDW_ID'),
            sl_code: requiredDraftValue(draft, 'sl_code', 'SL code'),
            start_date: date,
        }),
    },
    'term-deposits': {
        label: 'Term deposits',
        description: 'Maintain subsidiary-ledger mappings for term-deposit products.',
        tableName: 'DT_SDMT_UBL.RCOA_TD_MAPPING',
        icon: <FaBalanceScale />,
        columns: [
            { key: 'GL_EDW_ID', label: 'GL code', code: true },
            { key: 'CURY_EDW_ID', label: 'Currency' },
            { key: 'DEP_TERM_TYPE', label: 'Term type' },
            { key: 'DEP_TERM_PRD', label: 'Term period' },
            { key: 'SL_CODE', label: 'SL code', code: true, numeric: true, editable: true },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [{ key: 'sl_code', label: 'SL code', type: 'number', step: '1' }],
        getRowKey: (row) => getRowKey(row, [
            'GL_EDW_ID',
            'CURY_EDW_ID',
            'DEP_TERM_TYPE',
            'DEP_TERM_PRD',
            'START_DATE',
        ]),
        buildPayload: (row, draft, date) => ({
            gl_edw_id: readRowValue(row, 'GL_EDW_ID'),
            cury_edw_id: readRowValue(row, 'CURY_EDW_ID'),
            dep_term_type: readRowValue(row, 'DEP_TERM_TYPE'),
            dep_term_prd: readRowValue(row, 'DEP_TERM_PRD'),
            sl_code: requiredDraftValue(draft, 'sl_code', 'SL code'),
            start_date: date,
        }),
    },
    'loan-type': {
        label: 'Loan type',
        description: 'Map loan types and currencies to the correct subsidiary-ledger code.',
        tableName: 'DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING',
        icon: <FaFlag />,
        columns: [
            { key: 'SL_CODE', label: 'SL code', code: true, numeric: true, editable: true },
            { key: 'LOAN_TYPE', label: 'Loan type' },
            { key: 'LOAN_TYPE_DESC', label: 'Loan type description' },
            { key: 'CURY_EDW_ID', label: 'Currency' },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [{ key: 'sl_code', label: 'SL code', type: 'number', step: '1' }],
        getRowKey: (row) => getRowKey(row, ['SL_CODE', 'LOAN_TYPE', 'CURY_EDW_ID', 'START_DATE']),
        buildPayload: (row, draft, date) => ({
            sl_code: requiredDraftValue(draft, 'sl_code', 'SL code'),
            loan_type: readRowValue(row, 'LOAN_TYPE'),
            cury_edw_id: readRowValue(row, 'CURY_EDW_ID'),
            start_date: date,
        }),
    },
    'sl-roca': {
        label: 'SL ROCA',
        description: 'Review and maintain RCOA assignments at subsidiary-ledger level.',
        tableName: 'DT_SDMT_UBL.SL_RCOA_MAPPING',
        icon: <FaLink />,
        columns: [
            { key: 'SL_CODE', label: 'SL code', code: true },
            { key: 'RCOA_CODE', label: 'RCOA code', code: true, numeric: true, editable: true },
            { key: 'DESCRIPTION', label: 'Description', editable: true },
            { key: 'DOMAIN', label: 'Domain' },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [
            { key: 'rcoa_code', label: 'RCOA code', type: 'number', step: '1' },
            { key: 'description', label: 'Description' },
        ],
        getRowKey: (row) => getRowKey(row, ['SL_CODE', 'RCOA_CODE', 'START_DATE']),
        buildPayload: (row, draft, date) => {
            const rcoaCode = draft.rcoa_code?.trim() ?? '';
            const description = draft.description?.trim() ?? '';
            if (!rcoaCode && !description) {
                throw new Error('Enter an RCOA code or description before saving.');
            }
            const payload: Record<string, unknown> = {
                sl_code: readRowValue(row, 'SL_CODE'),
                rcoa_code: rcoaCode,
                description,
                start_date: date,
            };
            const originalRcoaCode = readRowValue(row, 'RCOA_CODE');
            const originalDescription = readRowValue(row, 'DESCRIPTION');
            if (originalRcoaCode) payload.original_rcoa_code = originalRcoaCode;
            if (originalDescription) payload.original_description = originalDescription;
            return payload;
        },
    },
    'tfcs-sukus': {
        label: 'TFCs / Sukuks',
        description: 'Maintain customer and RCOA mappings for TFC and Sukuk advances.',
        tableName: 'DT_SDMT_UBL.RCOA_ADVANCES_MAPPING',
        icon: <FaBalanceScale />,
        columns: [
            { key: 'LOAN_NO', label: 'Loan number', code: true, numeric: true },
            { key: 'CUST_NAME', label: 'Customer name', editable: true },
            { key: 'RCOA_CODE', label: 'RCOA code', code: true, numeric: true, editable: true },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [
            { key: 'cust_name', label: 'Customer name' },
            { key: 'rcoa_code', label: 'RCOA code', type: 'number', step: '1' },
        ],
        insertFields: [
            { key: 'loan_no', label: 'Loan number', type: 'number', step: '1' },
            { key: 'cust_name', label: 'Customer name' },
            { key: 'rcoa_code', label: 'RCOA code', type: 'number', step: '1' },
        ],
        buildInsertPayload: (draft, date) => {
            const customerName = requiredDraftValue(draft, 'cust_name', 'Customer name');
            if (!isValidCustomerName(customerName)) throw new Error(CUSTOMER_NAME_ERROR);
            return {
                start_date: date,
                loan_no: requiredDraftValue(draft, 'loan_no', 'Loan number'),
                cust_name: customerName,
                rcoa_code: requiredDraftValue(draft, 'rcoa_code', 'RCOA code'),
            };
        },
        getRowKey: (row) => getRowKey(row, ['LOAN_NO', 'START_DATE']),
        buildPayload: (row, draft, date) => {
            const custName = draft.cust_name?.trim() ?? '';
            const rcoaCode = draft.rcoa_code?.trim() ?? '';
            const originalCustName = readRowValue(row, 'CUST_NAME').trim();
            const originalRcoaCode = readRowValue(row, 'RCOA_CODE').trim();
            const customerNameChanged = custName !== originalCustName;
            if (customerNameChanged && !isValidCustomerName(custName)) {
                throw new Error(CUSTOMER_NAME_ERROR);
            }
            if (!custName && !rcoaCode) {
                throw new Error('Enter a customer name or RCOA code before saving.');
            }
            return {
                loan_no: readRowValue(row, 'LOAN_NO'),
                cust_name: customerNameChanged ? custName : null,
                rcoa_code: rcoaCode !== originalRcoaCode ? rcoaCode : null,
                start_date: date,
            };
        },
    },
    'rcoa-manual-data': {
        label: 'Manual RCOA data',
        description: 'Maintain manually supplied RCOA amounts, domains, and tiers.',
        tableName: 'DT_SDMT_UBL.RCOA_MANUAL_DATA',
        icon: <FaFlag />,
        columns: [
            { key: 'FLAG', label: 'Flag', format: 'flag' },
            { key: 'RCOA_CODE', label: 'RCOA code', code: true, numeric: true },
            { key: 'AMOUNT', label: 'Amount', numeric: true, editable: true, format: 'amount' },
            { key: 'DOMAIN', label: 'Domain', numeric: true, editable: true },
            { key: 'TIER', label: 'Tier', numeric: true, editable: true },
            { key: 'PARTICULARS', label: 'Particulars' },
            { key: 'PARTICULARS_DEFINITION', label: 'Particulars definition' },
            { key: 'START_DATE', label: 'Start date' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [
            { key: 'amount', label: 'Amount', type: 'number', step: '0.01' },
            { key: 'domain', label: 'Domain', type: 'number', step: '1', sourceKeys: ['DOMAIN'] },
            { key: 'tier', label: 'Tier', type: 'number', step: '1' },
        ],
        insertFields: [
            { key: 'rcoa_code', label: 'RCOA code', type: 'number', step: '1' },
            { key: 'domain', label: 'Domain', type: 'number', step: '1' },
            { key: 'tier', label: 'Tier', type: 'number', step: '1' },
            { key: 'amount', label: 'Amount', type: 'number', step: '0.01' },
            { key: 'flag', label: 'Flag' },
            { key: 'particulars', label: 'Particulars' },
            { key: 'particulars_definition', label: 'Particulars definition' },
        ],
        buildInsertPayload: (draft, date) => ({
            start_date: date,
            rcoa_code: requiredDraftValue(draft, 'rcoa_code', 'RCOA code'),
            domain: requiredDraftValue(draft, 'domain', 'Domain'),
            tier: requiredDraftValue(draft, 'tier', 'Tier'),
            amount: Number(requiredDraftValue(draft, 'amount', 'Amount')),
            flag: requiredDraftValue(draft, 'flag', 'Flag'),
            particulars: requiredDraftValue(draft, 'particulars', 'Particulars'),
            particulars_definition: requiredDraftValue(draft, 'particulars_definition', 'Particulars definition'),
        }),
        getRowKey: (row) => getRowKey(row, ['RCOA_CODE', 'START_DATE', 'DOMAIN', 'TIER']),
        buildPayload: (row, draft, date) => {
            const payload: Record<string, unknown> = {
                rcoa_code: readRowValue(row, 'RCOA_CODE'),
                start_date: date,
                domain: draft.domain?.trim() ?? '',
                tier: draft.tier?.trim() ?? '',
            };
            const originalDomain = readRowValue(row, 'DOMAIN');
            const originalTier = readRowValue(row, 'TIER');
            if (originalDomain) payload.original_domain = originalDomain;
            if (originalTier) payload.original_tier = originalTier;
            const amount = draft.amount?.trim() ?? '';
            if (amount) {
                const numericAmount = Number(amount);
                if (Number.isNaN(numericAmount)) throw new Error('Amount must be a valid number.');
                payload.amount = numericAmount;
            }
            if (!amount && !payload.domain && !payload.tier) {
                throw new Error('Enter at least one manual RCOA value before saving.');
            }
            return payload;
        },
    },
    adjustment: {
        label: 'Adjustment',
        description: 'Maintain date-scoped subsidiary-ledger adjustment values and flags.',
        tableName: 'DT_SDMT_UBL.RCOA_SL_WISE_ADJ',
        icon: <FaFlag />,
        columns: [
            { key: 'START_DATE', label: 'Start date' },
            { key: 'SL_CODE', label: 'SL code', code: true, numeric: true, editable: true },
            { key: 'AMOUNT', label: 'Amount', numeric: true, editable: true, format: 'amount' },
            { key: 'FLAG', label: 'Flag', editable: true, format: 'flag' },
            { key: 'UPDATE_DATE', label: 'Updated date' },
            { key: 'UPDATE_TS', label: 'Updated timestamp' },
        ],
        fields: [
            { key: 'sl_code', label: 'SL code', type: 'number', step: '1' },
            { key: 'amount', label: 'Amount', type: 'number', step: '0.01' },
            { key: 'flag', label: 'Flag' },
        ],
        insertFields: [
            { key: 'sl_code', label: 'SL code', type: 'number', step: '1' },
            { key: 'amount', label: 'Amount', type: 'number', step: '0.01' },
            { key: 'flag', label: 'Flag' },
        ],
        buildInsertPayload: (draft, date) => ({
            start_date: date,
            sl_code: requiredDraftValue(draft, 'sl_code', 'SL code'),
            amount: Number(requiredDraftValue(draft, 'amount', 'Amount')),
            flag: requiredDraftValue(draft, 'flag', 'Flag'),
        }),
        getRowKey: (row) => getRowKey(row, ['START_DATE', 'SL_CODE', 'AMOUNT', 'FLAG']),
        buildPayload: (row, draft, date) => {
            const payload: Record<string, unknown> = {
                start_date: date,
                sl_code: draft.sl_code?.trim() ?? '',
                flag: draft.flag?.trim() ?? '',
            };
            const originalSlCode = readRowValue(row, 'SL_CODE');
            const originalAmount = readRowValue(row, 'AMOUNT');
            const originalFlag = readRowValue(row, 'FLAG');
            if (originalSlCode) payload.original_sl_code = originalSlCode;
            if (originalAmount) payload.original_amount = Number(originalAmount);
            if (originalFlag) payload.original_flag = originalFlag;

            const amount = draft.amount?.trim() ?? '';
            if (amount) {
                const numericAmount = Number(amount);
                if (Number.isNaN(numericAmount)) throw new Error('Amount must be a valid number.');
                payload.amount = numericAmount;
            }
            if (!payload.sl_code && payload.amount === undefined && !payload.flag) {
                throw new Error('Enter at least one adjustment value before saving.');
            }
            return payload;
        },
    },
};

const getErrorMessage = (error: unknown, fallback: string) => {
    const response = (error as {
        response?: { status?: number; data?: { detail?: unknown; message?: unknown } };
    }).response;
    const detail = response?.data?.detail;
    if (typeof detail === 'string') return detail;

    if (Array.isArray(detail)) {
        const messages = detail.flatMap((item) => {
            if (!item || typeof item !== 'object') return [];
            const message = (item as { msg?: unknown }).msg;
            return typeof message === 'string' ? [message] : [];
        });
        if (messages.length) return messages.join(' ');
    }

    if (detail && typeof detail === 'object') {
        const detailRecord = detail as {
            message?: unknown;
            error_code?: unknown;
            request_id?: unknown;
        };
        const message = typeof detailRecord.message === 'string' ? detailRecord.message : '';
        const errorCode = typeof detailRecord.error_code === 'string' ? detailRecord.error_code : '';
        const requestId = typeof detailRecord.request_id === 'string' ? detailRecord.request_id : '';
        if (message || errorCode || requestId) {
            return [
                message || fallback,
                errorCode ? `Code: ${errorCode}` : '',
                requestId ? `Request ID: ${requestId}` : '',
            ].filter(Boolean).join(' ');
        }
    }

    const responseMessage = response?.data?.message;
    if (typeof responseMessage === 'string') return responseMessage;
    if (response?.status === 503) return 'Teradata is unavailable right now. Try again shortly.';
    return fallback;
};

const extractUserId = (subject: string) => {
    const candidate = subject.split('\\').pop() ?? subject;
    const userId = Number(candidate);
    return Number.isInteger(userId) ? userId : null;
};

const defaultPagination = {
    currentPage: 1,
    pageSize: 20,
    totalRecords: 0,
    totalPages: 1,
};

const Rcoa = () => {
    const [mode, setMode] = useState<RcoaMode>('gl-sl-mapping');
    const [reportDate, setReportDate] = useState(todayValue);
    const [appliedDate, setAppliedDate] = useState(todayValue);
    const [search, setSearch] = useState('');
    const [appliedSearch, setAppliedSearch] = useState('');
    const [page, setPage] = useState(1);
    const [rows, setRows] = useState<RcoaRow[]>([]);
    const [pagination, setPagination] = useState(defaultPagination);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [rcoaMetadata, setRcoaMetadata] = useState<RcoaMetadataResponse | null>(null);
    const [metadataError, setMetadataError] = useState<string | null>(null);
    const [metadataReloadToken, setMetadataReloadToken] = useState(0);
    const [notice, setNotice] = useState<string | null>(null);
    const [reloadToken, setReloadToken] = useState(0);
    const [userId, setUserId] = useState<number | null>(null);
    const [editingRow, setEditingRow] = useState<RcoaRow | null>(null);
    const [editingMode, setEditingMode] = useState<EditMode | null>(null);
    const [isInserting, setIsInserting] = useState(false);
    const [isInsertSaving, setIsInsertSaving] = useState(false);
    const [insertErrorMessage, setInsertErrorMessage] = useState<string | null>(null);
    const [draft, setDraft] = useState<Record<string, string>>({});
    const [insertDraft, setInsertDraft] = useState<Record<string, string>>({});
    const [highlightedRowKey, setHighlightedRowKey] = useState<string | null>(null);
    const [pendingChanges, setPendingChanges] = useState<Map<string, PendingChange>>(new Map());
    const [isSaving, setIsSaving] = useState(false);
    const [actionFilter, setActionFilter] = useState<'all' | 'editable'>('all');
    const [reportingStatus, setReportingStatus] = useState<ReportingStatus>('not_started');
    const [failedReportingAction, setFailedReportingAction] = useState<'start' | 'end' | null>(null);
    const [reportingAction, setReportingAction] = useState<'start' | 'end' | null>(null);
    const [isEndConfirmationOpen, setIsEndConfirmationOpen] = useState(false);

    const definition = modeLabels[mode];
    const appliedDateTimestamp = toLocalDateTimestamp(appliedDate);
    const isDateEditable = Number.isFinite(appliedDateTimestamp)
        && appliedDateTimestamp >= editWindowStartTimestamp
        && appliedDateTimestamp <= todayTimestamp;
    const reportingEnded = reportingStatus === 'completed';
    const canEditRows = isDateEditable && !reportingEnded && reportingStatus !== 'ending' && !isSaving;
    const editBlockReason = !isDateEditable
        ? 'selected date is outside the inclusive one-month editing window'
        : reportingStatus === 'ending'
            ? 'reporting is being ended'
        : reportingEnded
            ? 'reporting has ended'
            : isSaving
                ? 'another save is in progress'
                : 'editable';
    const totalPages = Math.max(1, pagination.totalPages || 1);
    const allPendingCount = pendingChanges.size;
    const pendingCount = allPendingCount;
    const canStartReporting = (
        reportingStatus === 'not_started'
        || (reportingStatus === 'failed' && failedReportingAction === 'start')
    ) && reportingAction === null && userId !== null;
    const canEndReporting = (
        reportingStatus === 'in_progress'
        || (reportingStatus === 'failed' && failedReportingAction === 'end')
    ) && reportingAction === null && allPendingCount === 0 && userId !== null;
    const reportingStatusLabel: Record<ReportingStatus, string> = {
        not_started: 'Not started',
        in_progress: 'In progress',
        ending: 'Ending',
        completed: 'Completed',
        failed: 'Failed',
    };
    const reportingStatusDescription: Record<ReportingStatus, string> = {
        not_started: 'Start reporting before making the cycle active.',
        in_progress: 'The reporting cycle is active and can be reviewed.',
        ending: 'The end-reporting procedure is running.',
        completed: 'The cycle is closed and cannot be edited.',
        failed: failedReportingAction === 'start'
            ? 'Starting reporting failed. Retry the start operation.'
            : failedReportingAction === 'end'
                ? 'Ending reporting failed. Retry the end operation.'
                : 'The reporting operation failed. Retry the available action.',
    };
    const startReportingDisabledReason = canStartReporting
        ? 'Ready to start reporting.'
        : reportingAction === 'start'
            ? 'Starting reporting...'
            : reportingAction === 'end'
                ? 'Wait for the end-reporting operation to finish.'
                : userId === null
                    ? 'Your user ID is not available yet.'
                    : reportingStatus === 'in_progress'
                        ? 'Reporting is already in progress.'
                        : reportingStatus === 'ending'
                            ? 'Reporting is being ended.'
                            : reportingStatus === 'completed'
                                ? 'Reporting has already completed.'
                                : 'Retry ending reporting before starting again.';
    const endReportingDisabledReason = canEndReporting
        ? 'Ready to end reporting.'
        : reportingAction === 'end'
            ? 'Ending reporting...'
            : reportingAction === 'start'
                ? 'Wait for the start-reporting operation to finish.'
                : allPendingCount > 0
                    ? `Save ${allPendingCount} pending change${allPendingCount === 1 ? '' : 's'} before ending reporting.`
                    : userId === null
                        ? 'Your user ID is not available yet.'
                        : reportingStatus === 'not_started'
                            ? 'Start reporting before ending the cycle.'
                            : reportingStatus === 'failed' && failedReportingAction === 'start'
                                ? 'Starting reporting must succeed before ending the cycle.'
                                : reportingStatus === 'completed'
                                    ? 'Reporting has already completed.'
                                    : 'Ending reporting is unavailable.';
    const visibleRows = actionFilter === 'editable' && !canEditRows ? [] : rows;
    const tableColumns = getTableColumns(rows, definition, rcoaMetadata);
    const pageError = metadataError ?? errorMessage;
    const isMetadataLoading = rcoaMetadata === null && !metadataError;
    const isPageLoading = isLoading || isMetadataLoading;

    useEffect(() => {
        let isMounted = true;

        getCurrentUser()
            .then((user) => {
                if (isMounted) setUserId(extractUserId(user.sub));
            })
            .catch(() => {
                if (isMounted) setUserId(null);
            });

        return () => {
            isMounted = false;
        };
    }, []);

    useEffect(() => {
        let isMounted = true;
        setMetadataError(null);

        fetchRcoaMetadata()
            .then((response) => {
                if (isMounted) setRcoaMetadata(response);
            })
            .catch((error: unknown) => {
                if (isMounted) {
                    setRcoaMetadata(null);
                    setMetadataError(getErrorMessage(error, 'Could not load the RCOA metadata contract.'));
                }
            });

        return () => {
            isMounted = false;
        };
    }, [metadataReloadToken]);

    useEffect(() => {
        const nextSearch = search.trim();
        if (nextSearch === appliedSearch) return undefined;

        const timeoutId = window.setTimeout(() => {
            setAppliedSearch(nextSearch);
            setPage(1);
            setNotice(null);
        }, 400);

        return () => window.clearTimeout(timeoutId);
    }, [appliedSearch, search]);

    useEffect(() => {
        let isMounted = true;

        setIsLoading(true);
        setErrorMessage(null);

        fetchRcoaPage(mode, appliedDate, page, appliedSearch)
            .then((response) => {
                if (!isMounted) return;
                console.log('[RCOA tab loaded]', {
                    mode,
                    appliedDate,
                    rowCount: response.data?.length ?? 0,
                    totalRecords: response.pagination?.totalRecords ?? 0,
                });
                setRows(response.data ?? []);
                setPagination(response.pagination ?? defaultPagination);
            })
            .catch((error: unknown) => {
                if (!isMounted) return;
                console.error('[RCOA tab load failed]', {
                    mode,
                    appliedDate,
                    error,
                });
                setRows([]);
                setPagination(defaultPagination);
                setErrorMessage(getErrorMessage(error, 'Could not load RCOA records.'));
            })
            .finally(() => {
                if (isMounted) setIsLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, [appliedDate, appliedSearch, mode, page, reloadToken]);

    useEffect(() => {
        console.log('[RCOA tab load/edit state]', {
            mode,
            appliedDate,
            page,
            search: appliedSearch,
            today: todayValue,
            editWindowStart,
            isDateEditable,
            reportingStatus,
            canEditRows,
        });

        console.log('[RCOA edit eligibility]', {
            mode,
            selectedDate: appliedDate,
            today: todayValue,
            editableFrom: editWindowStart,
            selectedDateTimestamp: appliedDateTimestamp,
            editableFromTimestamp: editWindowStartTimestamp,
            todayTimestamp,
            isDateEditable,
            reportingStatus,
            isSaving,
            canEditRows,
            reason: editBlockReason,
        });
    }, [appliedDate, appliedDateTimestamp, appliedSearch, canEditRows, editBlockReason, isDateEditable, isSaving, mode, page, reportingStatus]);

    const resetReportingState = () => {
        setReportingStatus('not_started');
        setFailedReportingAction(null);
        setReportingAction(null);
        setIsEndConfirmationOpen(false);
    };

    const clearPendingChanges = () => {
        setPendingChanges(new Map());
    };

    const handleApply = () => {
        if (isInsertSaving) return;

        const nextSearch = search.trim();
        setAppliedSearch(nextSearch);
        setPage(1);
        setNotice(null);

        if (reportDate !== appliedDate) {
            setAppliedDate(reportDate);
            resetReportingState();
            setEditingRow(null);
            setEditingMode(null);
            setIsInserting(false);
            setHighlightedRowKey(null);
            if (pendingChanges.size) {
                clearPendingChanges();
                setNotice('Pending changes were cleared because the reporting date changed.');
            }
        } else if (nextSearch === appliedSearch) {
            setReloadToken((current) => current + 1);
        }
    };

    const handleReset = () => {
        if (isInsertSaving) return;

        const dateChanged = todayValue !== appliedDate;
        const hasPendingChanges = pendingChanges.size > 0;
        setReportDate(todayValue);
        setAppliedDate(todayValue);
        setSearch('');
        setAppliedSearch('');
        setActionFilter('all');
        setPage(1);
        resetReportingState();
        setErrorMessage(null);
        setEditingRow(null);
        setEditingMode(null);
        setIsInserting(false);
        setHighlightedRowKey(null);
        if (hasPendingChanges && dateChanged) {
            clearPendingChanges();
            setNotice('Pending changes were cleared because the reporting date changed.');
        } else {
            setNotice(null);
        }
        setReloadToken((current) => current + 1);
    };

    const handleModeChange = (nextMode: RcoaMode) => {
        if (isInsertSaving) return;

        setMode(nextMode);
        setPage(1);
        setEditingRow(null);
        setEditingMode(null);
        setIsInserting(false);
        setHighlightedRowKey(null);
        setDraft({});
        setNotice(null);
        setErrorMessage(null);
    };

    const handleStartReporting = async () => {
        if (!canStartReporting || userId === null) return;

        setReportingAction('start');
        setReportingStatus('in_progress');
        setFailedReportingAction(null);
        setErrorMessage(null);
        try {
            await startRcoaReporting(appliedDate, userId);
            setReportingStatus('in_progress');
            setNotice(`Start reporting procedure completed successfully for ${appliedDate}.`);
        } catch (error: unknown) {
            setReportingStatus('failed');
            setFailedReportingAction('start');
            setErrorMessage(getErrorMessage(error, 'Could not start reporting for this date.'));
        } finally {
            setReportingAction(null);
        }
    };

    const openEndReportingConfirmation = () => {
        if (canEndReporting) setIsEndConfirmationOpen(true);
    };

    const handleEndReporting = async () => {
        if (!canEndReporting || userId === null) return;

        setIsEndConfirmationOpen(false);
        setReportingAction('end');
        setReportingStatus('ending');
        setFailedReportingAction(null);
        setErrorMessage(null);
        try {
            await endRcoaReporting(appliedDate, userId);
            setReportingStatus('completed');
            setNotice(`End reporting procedure completed successfully for ${appliedDate}.`);
        } catch (error: unknown) {
            setReportingStatus('failed');
            setFailedReportingAction('end');
            setErrorMessage(getErrorMessage(error, 'Could not end reporting for this date.'));
        } finally {
            setReportingAction(null);
        }
    };

    const getPendingKey = (row: RcoaRow) => `${mode}:${definition.getRowKey(row)}`;

    const openEditor = (row: RcoaRow) => {
        if (!canEditRows) return;

        const pending = pendingChanges.get(getPendingKey(row));
        const initialDraft = getDraftForFields(row, definition.fields);
        definition.fields.forEach((field) => {
            const pendingValue = pending?.values[field.key.toUpperCase()];
            if (pendingValue !== undefined) initialDraft[field.key] = pendingValue;
        });
        setDraft(initialDraft);
        setEditingRow(row);
        setEditingMode('modal');
        setHighlightedRowKey(getPendingKey(row));
        setErrorMessage(null);
    };

    const openInlineEditor = (row: RcoaRow) => {
        if (!canEditRows) return;
        if (editingRow && getPendingKey(editingRow) !== getPendingKey(row)) {
            try {
                const pendingChange = buildPendingChange();
                if (pendingChange) {
                    stagePendingChange(pendingChange);
                    setNotice('Previous inline change staged locally.');
                }
            } catch (error: unknown) {
                setErrorMessage(error instanceof Error ? error.message : 'Could not stage the current inline edit.');
                return;
            }
        }

        const pending = pendingChanges.get(getPendingKey(row));
        const initialDraft = getDraftForFields(row, definition.fields);
        definition.fields.forEach((field) => {
            const pendingValue = pending?.values[field.key.toUpperCase()];
            if (pendingValue !== undefined) initialDraft[field.key] = pendingValue;
        });
        setDraft(initialDraft);
        setEditingRow(row);
        setEditingMode('inline');
        setHighlightedRowKey(getPendingKey(row));
        setErrorMessage(null);
    };

    const closeEditor = () => {
        setEditingRow(null);
        setEditingMode(null);
        setDraft({});
    };

    const updateDraft = (field: string, value: string) => {
        setDraft((current) => ({ ...current, [field]: value }));
    };

    const updateEditorDraft = (field: EditorField, value: string) => {
        const normalizedValue = isCustomerNameField(field) ? normalizeCustomerName(value) : value;
        if (!isNumericDraftValue(field, normalizedValue, true)) return;
        updateDraft(field.key, normalizedValue);
    };

    const buildPendingChange = (): PendingChange | null => {
        if (!editingRow) return null;

        const existingPending = pendingChanges.get(getPendingKey(editingRow));
        const hasDraftChanges = definition.fields.some((field) => {
            const baseline = existingPending?.values[field.key.toUpperCase()]
                ?? readRowValue(editingRow, ...(field.sourceKeys ?? [field.key.toUpperCase()]));
            return (draft[field.key] ?? '') !== baseline;
        });

        if (!hasDraftChanges) return null;

        definition.fields.forEach((field) => {
            const value = draft[field.key]?.trim() ?? '';
            if (value && !isNumericDraftValue(field, value)) {
                throw new Error(`${field.label} must be numeric.`);
            }
            const baseline = existingPending?.values[field.key.toUpperCase()]
                ?? readRowValue(editingRow, ...(field.sourceKeys ?? [field.key.toUpperCase()]));
            if (isCustomerNameField(field) && value !== baseline.trim() && !isValidCustomerName(value)) {
                throw new Error(CUSTOMER_NAME_ERROR);
            }
        });

        const payload = definition.buildPayload(editingRow, draft, appliedDate);
        const values = definition.fields.reduce<Record<string, string>>((result, field) => {
            const value = draft[field.key] ?? '';
            result[field.key.toUpperCase()] = value;
            field.sourceKeys?.forEach((sourceKey) => {
                result[sourceKey.toUpperCase()] = value;
            });
            return result;
        }, {});
        const rowKey = getPendingKey(editingRow);

        return { mode, rowKey, payload, values };
    };

    const stagePendingChange = (pendingChange: PendingChange) => {
        setPendingChanges((current) => {
            const next = new Map(current);
            next.set(pendingChange.rowKey, pendingChange);
            return next;
        });
    };

    const handleEditorKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && event.currentTarget.tagName !== 'TEXTAREA') {
            event.preventDefault();
            handleStageChanges();
        }
    };

    const handleStageChanges = () => {
        if (!editingRow) return;

        setErrorMessage(null);
        try {
            const pendingChange = buildPendingChange();
            if (!pendingChange) {
                closeEditor();
                setNotice('No changes to stage.');
                return;
            }
            stagePendingChange(pendingChange);
            closeEditor();
            setNotice('Change staged locally. Use Save changes to write it to the backend.');
        } catch (error: unknown) {
            setErrorMessage(error instanceof Error ? error.message : 'Could not stage the change.');
        }
    };

    const handleSavePending = async () => {
        let changesToSave = [...pendingChanges.values()];

        if (editingRow) {
            try {
                const inlineChange = buildPendingChange();
                if (inlineChange) {
                    changesToSave = [
                        ...changesToSave.filter((change) => change.rowKey !== inlineChange.rowKey),
                        inlineChange,
                    ];
                    setPendingChanges((current) => {
                        const next = new Map(current);
                        next.set(inlineChange.rowKey, inlineChange);
                        return next;
                    });
                    closeEditor();
                } else {
                    closeEditor();
                }
            } catch (error: unknown) {
                setErrorMessage(error instanceof Error ? error.message : 'Could not stage the inline edit.');
                return;
            }
        }

        if (!changesToSave.length) return;

        setIsSaving(true);
        setErrorMessage(null);
        try {
            await batchUpdateAllRcoa(changesToSave.map((change) => ({
                mode: change.mode,
                change: change.payload,
            })));
            const changedModes = new Set(changesToSave.map((change) => change.mode));
            const changeCount = changesToSave.length;
            setPendingChanges(new Map());
            setNotice(`${changeCount} change${changeCount === 1 ? '' : 's'} saved across ${changedModes.size} dataset${changedModes.size === 1 ? '' : 's'}.`);
            setReloadToken((current) => current + 1);
        } catch (error: unknown) {
            setErrorMessage(getErrorMessage(error, 'Could not save the pending RCOA changes.'));
        } finally {
            setIsSaving(false);
        }
    };

    const openInsertEditor = () => {
        if (isInsertSaving || !canEditRows || !definition.insertFields || !definition.buildInsertPayload) return;
        setInsertDraft({});
        setIsInserting(true);
        setInsertErrorMessage(null);
        setNotice(null);
        setErrorMessage(null);
    };

    const closeInsertEditor = (force = false) => {
        if (isInsertSaving && !force) return;

        setIsInserting(false);
        setInsertDraft({});
        setInsertErrorMessage(null);
    };

    const updateInsertDraft = (field: EditorField, value: string) => {
        if (isInsertSaving) return;
        const normalizedValue = isCustomerNameField(field) ? normalizeCustomerName(value) : value;
        if (!isNumericDraftValue(field, normalizedValue, true)) return;
        setInsertDraft((current) => ({ ...current, [field.key]: normalizedValue }));
    };

    const handleInsert = async () => {
        if (isInsertSaving || !definition.insertFields || !definition.buildInsertPayload) return;

        setInsertErrorMessage(null);
        try {
            definition.insertFields.forEach((field) => {
                const value = insertDraft[field.key]?.trim() ?? '';
                if (!value) throw new Error(`${field.label} is required.`);
                if (!isNumericDraftValue(field, value)) throw new Error(`${field.label} must be numeric.`);
                if (isCustomerNameField(field) && !isValidCustomerName(value)) {
                    throw new Error(CUSTOMER_NAME_ERROR);
                }
            });

            const insertionDate = toDateInputValue(new Date());
            const payload = definition.buildInsertPayload(insertDraft, insertionDate);
            setIsInsertSaving(true);
            await insertRcoaRow(mode, payload);
            closeInsertEditor(true);
            setNotice(`${definition.label} row inserted successfully for ${insertionDate}. The list is refreshing.`);
            setReloadToken((current) => current + 1);
        } catch (error: unknown) {
            const message = getErrorMessage(
                error,
                error instanceof Error ? error.message : 'Could not insert the RCOA row.',
            );
            setInsertErrorMessage(message);
        } finally {
            setIsInsertSaving(false);
        }
    };

    const handleInsertKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && event.currentTarget.tagName !== 'TEXTAREA') {
            event.preventDefault();
            void handleInsert();
        }
    };

    const renderCell = (row: RcoaRow, column: RcoaColumn, isEditing: boolean) => {
        const value = readRowValue(row, ...(column.keys ?? [column.key]));
        const editorField = column.editable
            ? definition.fields.find((field) => [field.key, ...(field.sourceKeys ?? [])]
                .some((key) => normalizeColumnKey(key) === normalizeColumnKey(column.key)))
            : undefined;
        const classNames = [
            column.code ? 'rcoa-code' : '',
            column.numeric ? 'rcoa-number' : '',
            column.editable ? 'rcoa-editable-cell' : '',
        ].filter(Boolean).join(' ');
        let content: ReactNode = displayValue(value);

        if (isEditing && editorField) {
            const editorValue = draft[editorField.key] ?? value;
            content = isExpandableTextField(editorField) ? (
                <AutoGrowingTextarea
                    className="rcoa-auto-textarea rcoa-inline-textarea"
                    value={editorValue}
                    ariaLabel={`Edit ${column.label}`}
                    onChange={(event) => updateEditorDraft(editorField, event.target.value)}
                    onKeyDown={handleEditorKeyDown}
                />
            ) : (
                <input
                    className="rcoa-inline-input"
                    type={getEditorInputType(editorField)}
                    inputMode={editorField.type === 'number' ? editorField.step === '1' ? 'numeric' : 'decimal' : undefined}
                    step={editorField.step}
                    value={editorValue}
                    aria-label={`Edit ${column.label}`}
                    pattern={isCustomerNameField(editorField) ? CUSTOMER_NAME_INPUT_PATTERN : undefined}
                    title={isCustomerNameField(editorField) ? CUSTOMER_NAME_ERROR : undefined}
                    onChange={(event) => updateEditorDraft(editorField, event.target.value)}
                    onKeyDown={handleEditorKeyDown}
                />
            );
        } else if (column.format === 'amount') {
            content = formatAmount(value);
        } else if (column.format === 'flag') {
            content = <span className="rcoa-flag">{displayValue(value)}</span>;
        }

        return (
            <td
                key={column.key}
                className={classNames}
                title={column.editable ? `${column.label} is editable; double-click to edit inline` : undefined}
                onDoubleClick={column.editable && !isEditing ? () => openInlineEditor(row) : undefined}
            >
                {content}
            </td>
        );
    };

    const renderEditorFields = () => definition.fields.map((field) => {
        const value = draft[field.key] ?? '';
        return (
            <label className="rcoa-field" key={field.key}>
                <span>{field.label}</span>
                {isExpandableTextField(field) ? (
                    <AutoGrowingTextarea
                        className="rcoa-auto-textarea"
                        value={value}
                        ariaLabel={field.label}
                        onChange={(event) => updateEditorDraft(field, event.target.value)}
                        onKeyDown={handleEditorKeyDown}
                    />
                ) : (
                    <input
                        type={getEditorInputType(field)}
                        inputMode={field.type === 'number' ? field.step === '1' ? 'numeric' : 'decimal' : undefined}
                        step={field.step}
                        value={value}
                        pattern={isCustomerNameField(field) ? CUSTOMER_NAME_INPUT_PATTERN : undefined}
                        title={isCustomerNameField(field) ? CUSTOMER_NAME_ERROR : undefined}
                        onChange={(event) => updateEditorDraft(field, event.target.value)}
                        onKeyDown={handleEditorKeyDown}
                    />
                )}
            </label>
        );
    });

    const renderInsertFields = () => definition.insertFields?.map((field) => {
        const value = insertDraft[field.key] ?? '';
        return (
            <label className="rcoa-field" key={field.key}>
                <span>{field.label}</span>
                {isExpandableTextField(field) ? (
                    <AutoGrowingTextarea
                        className="rcoa-auto-textarea"
                        value={value}
                        ariaLabel={field.label}
                        disabled={isInsertSaving}
                        onChange={(event) => updateInsertDraft(field, event.target.value)}
                        onKeyDown={handleInsertKeyDown}
                    />
                ) : (
                    <input
                        type={getEditorInputType(field)}
                        inputMode={field.type === 'number' ? field.step === '1' ? 'numeric' : 'decimal' : undefined}
                        step={field.step}
                        value={value}
                        disabled={isInsertSaving}
                        pattern={isCustomerNameField(field) ? CUSTOMER_NAME_INPUT_PATTERN : undefined}
                        title={isCustomerNameField(field) ? CUSTOMER_NAME_ERROR : undefined}
                        onChange={(event) => updateInsertDraft(field, event.target.value)}
                        onKeyDown={handleInsertKeyDown}
                    />
                )}
            </label>
        );
    });

    const renderRowAction = (row: RcoaRow, pending: PendingChange | undefined, isEditing: boolean) => (
        isEditing ? (
            <div className="rcoa-inline-actions">
                <button
                    type="button"
                    className="rcoa-primary-button compact"
                    onClick={handleStageChanges}
                >
                    Stage
                </button>
                <button
                    type="button"
                    className="rcoa-ghost-button compact"
                    onClick={closeEditor}
                >
                    Cancel
                </button>
            </div>
        ) : (
            <button
                type="button"
                className={`rcoa-edit-button ${pending ? 'has-pending' : ''}`}
                onClick={() => openEditor(row)}
                disabled={!canEditRows || editingRow !== null}
                title={!canEditRows
                    ? `Editing unavailable: ${editBlockReason}`
                    : editingRow !== null
                        ? 'Finish or cancel the current inline edit first'
                        : 'Edit record'}
            >
                {canEditRows ? <FaEdit /> : <FaLock />}
                <span>{pending ? 'Pending' : canEditRows ? 'Edit' : 'Read-only'}</span>
            </button>
        )
    );

    return (
        <div className="rcoa-page container-fluid">
            <div className="rcoa-shell">
                <section className="rcoa-hero">
                    <div>
                        <p className="rcoa-kicker">Regulatory operations / RCOA</p>
                        <h1>RCOA data workspace</h1>
                        <p className="rcoa-hero-copy">
                            Review every mapping dataset, stage controlled edits, and close each reporting cycle cleanly.
                        </p>
                    </div>
                    <div className="rcoa-reporting-start">
                        <div className="rcoa-date-summary">
                            <span>Active reporting date</span>
                            <strong>{appliedDate}</strong>
                        </div>
                        <div className="rcoa-reporting-action">
                            <button
                                type="button"
                                className="rcoa-primary-button"
                                onClick={() => void handleStartReporting()}
                                disabled={!canStartReporting}
                                title={startReportingDisabledReason}
                            >
                                <FaPlay />
                                {reportingAction === 'start'
                                    ? 'Starting...'
                                    : reportingStatus === 'in_progress'
                                        ? 'Reporting in progress'
                                        : reportingStatus === 'completed'
                                            ? 'Reporting completed'
                                            : 'Start reporting'}
                            </button>
                            <span className="rcoa-action-hint">{startReportingDisabledReason}</span>
                        </div>
                    </div>
                </section>

                <section className="rcoa-status-strip" aria-live="polite">
                    <div className="rcoa-status-item">
                        <span className={`rcoa-status-dot is-${reportingStatus}`} />
                        <strong>Reporting: {reportingStatusLabel[reportingStatus]}</strong>
                    </div>
                    <span className="rcoa-status-description">{reportingStatusDescription[reportingStatus]}</span>
                    <span className="rcoa-status-divider" />
                    <span>{pagination.totalRecords} records in the current dataset</span>
                    <span className="rcoa-status-divider" />
                    <span className={!isDateEditable ? 'rcoa-lock-copy' : ''}>
                        {!isDateEditable ? <><FaLock /> Editing available from {editWindowStart}</> : 'Editing window is open for this date'}
                    </span>
                    {allPendingCount > 0 && (
                        <>
                            <span className="rcoa-status-divider" />
                            <span className="rcoa-pending-summary">{allPendingCount} unsaved change{allPendingCount === 1 ? '' : 's'}</span>
                        </>
                    )}
                </section>

                <section className="rcoa-workspace-card">
                    <div className="rcoa-mode-tabs" role="tablist" aria-label="RCOA dataset">
                        {modeOrder.map((option) => {
                            const optionPendingCount = [...pendingChanges.values()].filter((change) => change.mode === option).length;
                            return (
                                <button
                                    key={option}
                                    type="button"
                                    role="tab"
                                    aria-selected={mode === option}
                                    className={mode === option ? 'is-active' : ''}
                                    onClick={() => handleModeChange(option)}
                                >
                                    {modeLabels[option].icon}
                                    <span>{modeLabels[option].label}</span>
                                    {optionPendingCount > 0 && <small>{optionPendingCount}</small>}
                                </button>
                            );
                        })}
                    </div>

                    <div className="rcoa-mode-heading">
                        <div>
                            <p className="rcoa-kicker">Current dataset</p>
                            <h2>{definition.label}</h2>
                            <p>{definition.description}</p>
                        </div>
                        <div className="rcoa-mode-actions">
                            {pendingCount > 0 && (
                                <button
                                    type="button"
                                    className="rcoa-primary-button compact"
                                    onClick={handleSavePending}
                                    disabled={isSaving || !canEditRows}
                                >
                                    <FaSave />
                                    {isSaving ? 'Saving...' : `Save changes (${pendingCount})`}
                                </button>
                            )}
                            {definition.insertFields && !isInserting && (
                                <button
                                    type="button"
                                    className="rcoa-ghost-button compact"
                                    onClick={openInsertEditor}
                                    disabled={!canEditRows || editingRow !== null || isInserting}
                                    title={!canEditRows ? `Insert unavailable: ${editBlockReason}` : 'Insert a complete row'}
                                >
                                    <FaPlus />
                                    Insert row
                                </button>
                            )}
                            <span className="rcoa-date-pill">{appliedDate}</span>
                        </div>
                    </div>

                    <div className="rcoa-filter-bar">
                        <label className="rcoa-date-filter">
                            <span>Report date</span>
                            <input
                                type="date"
                                value={reportDate}
                                max={todayValue}
                                onChange={(event) => setReportDate(event.target.value)}
                            />
                        </label>
                        <label className="rcoa-search-filter">
                            <span>Search this dataset</span>
                            <div className="rcoa-search-input">
                                <FaSearch aria-hidden="true" />
                                <input
                                    type="search"
                                    value={search}
                                    placeholder="Search codes, names, or values"
                                    onChange={(event) => setSearch(event.target.value)}
                                    onKeyDown={(event) => {
                                        if (event.key === 'Enter') handleApply();
                                    }}
                                />
                            </div>
                            <small className="rcoa-search-hint">Updates automatically after 400ms, or press Enter to apply immediately.</small>
                        </label>
                        <label className="rcoa-action-filter">
                            <span>Action availability</span>
                            <select
                                value={actionFilter}
                                onChange={(event) => setActionFilter(event.target.value as 'all' | 'editable')}
                            >
                                <option value="all">All rows</option>
                                <option value="editable">Editable only</option>
                            </select>
                        </label>
                        <div className="rcoa-filter-actions">
                            <button type="button" className="rcoa-primary-button compact" onClick={handleApply}>
                                Apply
                            </button>
                            <button type="button" className="rcoa-ghost-button compact" onClick={handleReset}>
                                Reset
                            </button>
                        </div>
                    </div>

                    {notice && (
                        <div className="rcoa-notice" role="status">
                            <FaCheckCircle aria-hidden="true" />
                            <span>{notice}</span>
                        </div>
                    )}
                    {pageError && (
                        <div className="rcoa-error" role="alert">
                            <FaExclamationCircle aria-hidden="true" />
                            <span>{pageError}</span>
                            <button
                                type="button"
                                onClick={() => {
                                    setReloadToken((current) => current + 1);
                                    setMetadataReloadToken((current) => current + 1);
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    <div className="rcoa-table-frame">
                        <table className="rcoa-table">
                            <thead>
                                <tr>
                                    <th className="rcoa-action-heading">Action</th>
                                    {tableColumns.map((column) => (
                                        <th
                                            key={column.key}
                                            className={`${column.numeric ? 'rcoa-number' : ''} ${column.editable ? 'rcoa-editable-heading' : ''}`}
                                            title={column.editable ? `${column.label} is editable; double-click to edit inline` : undefined}
                                        >
                                            <span>{column.label}</span>
                                            {column.editable && <FaEdit aria-label="Editable column" />}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {isPageLoading && (
                                    <tr>
                                        <td colSpan={tableColumns.length + 1} className="rcoa-table-state">
                                            <span className="rcoa-spinner" />
                                            {isMetadataLoading ? 'Loading RCOA metadata...' : `Loading ${definition.label} records...`}
                                        </td>
                                    </tr>
                                )}
                                {!isPageLoading && !pageError && visibleRows.map((row, index) => {
                                    const rowKey = getPendingKey(row);
                                    const pending = pendingChanges.get(rowKey);
                                    const displayRow = pending ? { ...row, ...pending.values } : row;
                                    const isEditing = editingMode === 'inline'
                                        && editingRow !== null
                                        && getPendingKey(editingRow) === rowKey;
                                    const isHighlighted = highlightedRowKey === rowKey;
                                    return (
                                        <tr
                                            key={`${rowKey}-${index}`}
                                            className={[pending ? 'is-pending' : '', isHighlighted ? 'is-highlighted' : ''].filter(Boolean).join(' ')}
                                            onClick={() => setHighlightedRowKey(rowKey)}
                                        >
                                            <td className="rcoa-action-cell">
                                                {renderRowAction(row, pending, isEditing)}
                                            </td>
                                            {tableColumns.map((column) => renderCell(displayRow, column, isEditing))}
                                        </tr>
                                    );
                                })}
                                {!isPageLoading && !pageError && visibleRows.length === 0 && (
                                    <tr>
                                        <td colSpan={tableColumns.length + 1} className="rcoa-table-state">
                                            <strong>
                                                {actionFilter === 'editable'
                                                    ? 'No editable actions are available for this date.'
                                                    : 'No records match these filters.'}
                                            </strong>
                                            <button
                                                type="button"
                                                onClick={() => actionFilter === 'editable' ? setActionFilter('all') : handleReset()}
                                            >
                                                {actionFilter === 'editable' ? 'Show all actions' : 'Reset filters'}
                                            </button>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="rcoa-pagination">
                        <button
                            type="button"
                            className="rcoa-ghost-button compact"
                            disabled={page <= 1 || isPageLoading}
                            onClick={() => setPage((current) => Math.max(1, current - 1))}
                        >
                            <FaChevronLeft /> Prev
                        </button>
                        <span>Page <strong>{page}</strong> of <strong>{totalPages}</strong></span>
                        <button
                            type="button"
                            className="rcoa-ghost-button compact"
                            disabled={page >= totalPages || isPageLoading}
                            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                        >
                            Next <FaChevronRight />
                        </button>
                    </div>
                </section>

                <section className="rcoa-cycle-end">
                    <div>
                        <p className="rcoa-kicker">Reporting cycle</p>
                        <h2>Close the date when the review is complete</h2>
                        <p>End reporting is intentionally kept at the bottom so it remains the final action for this date.</p>
                    </div>
                    <div className="rcoa-reporting-action rcoa-end-action">
                        <button
                            type="button"
                            className="rcoa-end-button"
                            onClick={openEndReportingConfirmation}
                            disabled={!canEndReporting}
                            title={endReportingDisabledReason}
                        >
                            <FaStop />
                            {reportingAction === 'end'
                                ? 'Ending...'
                                : reportingStatus === 'completed'
                                    ? 'Reporting ended'
                                    : reportingStatus === 'failed' && failedReportingAction === 'end'
                                        ? 'Retry end reporting'
                                        : 'End reporting'}
                        </button>
                        <span className="rcoa-action-hint">{endReportingDisabledReason}</span>
                    </div>
                </section>
            </div>

            {isEndConfirmationOpen && (
                <div
                    className="rcoa-modal-backdrop"
                    role="presentation"
                    onMouseDown={() => setIsEndConfirmationOpen(false)}
                >
                    <section
                        className="rcoa-edit-modal rcoa-confirmation-modal"
                        role="alertdialog"
                        aria-modal="true"
                        aria-labelledby="rcoa-end-confirmation-title"
                        aria-describedby="rcoa-end-confirmation-copy"
                        onMouseDown={(event) => event.stopPropagation()}
                    >
                        <div className="rcoa-modal-heading">
                            <div>
                                <p className="rcoa-kicker">Final reporting action</p>
                                <h2 id="rcoa-end-confirmation-title">End reporting?</h2>
                            </div>
                            <button
                                type="button"
                                className="rcoa-modal-close"
                                onClick={() => setIsEndConfirmationOpen(false)}
                                aria-label="Cancel end reporting confirmation"
                            >
                                x
                            </button>
                        </div>
                        <p id="rcoa-end-confirmation-copy" className="rcoa-modal-copy">
                            This will run the end-reporting procedure for the selected date. After it completes, the cycle cannot be edited.
                        </p>
                        <div className="rcoa-confirmation-summary">
                            <div>
                                <span>Selected date</span>
                                <strong>{appliedDate}</strong>
                            </div>
                            <div>
                                <span>Pending changes</span>
                                <strong>{allPendingCount}</strong>
                            </div>
                            <div>
                                <span>Current status</span>
                                <strong>{reportingStatusLabel[reportingStatus]}</strong>
                            </div>
                        </div>
                        <p className="rcoa-confirmation-warning">
                            Confirm only after reviewing all records for this reporting date.
                        </p>
                        <div className="rcoa-modal-actions">
                            <button
                                type="button"
                                className="rcoa-ghost-button"
                                onClick={() => setIsEndConfirmationOpen(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="rcoa-end-button"
                                onClick={() => void handleEndReporting()}
                            >
                                <FaStop />
                                Confirm and end reporting
                            </button>
                        </div>
                    </section>
                </div>
            )}

            {editingMode === 'modal' && editingRow && (
                <div className="rcoa-modal-backdrop" role="presentation" onMouseDown={closeEditor}>
                    <section
                        className="rcoa-edit-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="rcoa-edit-title"
                        onMouseDown={(event) => event.stopPropagation()}
                    >
                        <div className="rcoa-modal-heading">
                            <div>
                                <p className="rcoa-kicker">Controlled edit</p>
                                <h2 id="rcoa-edit-title">Edit {definition.label}</h2>
                            </div>
                            <button type="button" className="rcoa-modal-close" onClick={closeEditor} aria-label="Close edit dialog">
                                x
                            </button>
                        </div>
                        <p className="rcoa-modal-copy">
                            Changes apply to <strong>{appliedDate}</strong> only.
                        </p>
                        <div className="rcoa-edit-grid">{renderEditorFields()}</div>
                        <div className="rcoa-modal-actions">
                            <button type="button" className="rcoa-ghost-button" onClick={closeEditor}>Cancel</button>
                            <button type="button" className="rcoa-primary-button" onClick={handleStageChanges}>
                                Save to pending
                            </button>
                        </div>
                    </section>
                </div>
            )}

            {isInserting && definition.insertFields && (
                <div
                    className="rcoa-modal-backdrop"
                    role="presentation"
                    onMouseDown={() => {
                        if (!isInsertSaving) closeInsertEditor();
                    }}
                >
                    <section
                        className="rcoa-edit-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="rcoa-insert-title"
                        aria-busy={isInsertSaving}
                        onMouseDown={(event) => event.stopPropagation()}
                    >
                        <div className="rcoa-modal-heading">
                            <div>
                                <p className="rcoa-kicker">New row</p>
                                <h2 id="rcoa-insert-title">Insert {definition.label}</h2>
                            </div>
                            <button
                                type="button"
                                className="rcoa-modal-close"
                                onClick={() => closeInsertEditor()}
                                disabled={isInsertSaving}
                                aria-label="Close insert dialog"
                            >
                                x
                            </button>
                        </div>
                        <p className="rcoa-modal-copy">
                            All row fields are required. The date at insertion time will be used as the start date.
                            System metadata will be added by the backend.
                        </p>
                        <div className="rcoa-edit-grid">{renderInsertFields()}</div>
                        {isInsertSaving && (
                            <div className="rcoa-modal-feedback is-progress" role="status">
                                <span className="rcoa-spinner" aria-hidden="true" />
                                <span>Saving this row to Teradata...</span>
                            </div>
                        )}
                        {insertErrorMessage && (
                            <div className="rcoa-modal-feedback is-error" role="alert">
                                <FaExclamationCircle aria-hidden="true" />
                                <span>{insertErrorMessage}</span>
                            </div>
                        )}
                        <div className="rcoa-modal-actions">
                            <button
                                type="button"
                                className="rcoa-ghost-button"
                                onClick={() => closeInsertEditor()}
                                disabled={isInsertSaving}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="rcoa-primary-button"
                                onClick={() => void handleInsert()}
                                disabled={isInsertSaving}
                            >
                                {isInsertSaving ? 'Inserting...' : 'Insert row'}
                            </button>
                        </div>
                    </section>
                </div>
            )}

        </div>
    );
};

export default Rcoa;
