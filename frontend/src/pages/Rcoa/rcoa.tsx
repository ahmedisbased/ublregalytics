import { useEffect, useState, type KeyboardEvent, type ReactNode } from 'react';
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
    fetchRcoaPage,
    getCurrentUser,
    insertRcoaRow,
    startRcoaReporting,
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

const getEditorInputType = (field: EditorField) => field.type === 'number' ? 'text' : field.type ?? 'text';

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

const getTableColumns = (rows: RcoaRow[], definition: RcoaModeDefinition) => {
    const configuredKeys = new Set(
        definition.columns.flatMap((column) => [column.key, ...(column.keys ?? [])])
            .map(normalizeColumnKey),
    );
    const returnedKeys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    const additionalColumns = returnedKeys
        .filter((key) => !configuredKeys.has(normalizeColumnKey(key)))
        .map((key): RcoaColumn => ({
            key,
            label: formatColumnLabel(key),
            code: /(_CODE|_ID|_NO)$/i.test(key),
        }));

    return [...definition.columns, ...additionalColumns];
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
        icon: <FaLink />,
        columns: [
            { key: 'SL_CODE', label: 'SL code', code: true },
            { key: 'RCOA_CODE', label: 'RCOA code', code: true, numeric: true, editable: true },
            { key: 'DESCRIPTION', label: 'Description', editable: true },
            { key: 'TIER', label: 'Tier' },
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
        buildInsertPayload: (draft, date) => ({
            start_date: date,
            loan_no: requiredDraftValue(draft, 'loan_no', 'Loan number'),
            cust_name: requiredDraftValue(draft, 'cust_name', 'Customer name'),
            rcoa_code: requiredDraftValue(draft, 'rcoa_code', 'RCOA code'),
        }),
        getRowKey: (row) => getRowKey(row, ['LOAN_NO', 'START_DATE']),
        buildPayload: (row, draft, date) => {
            const custName = draft.cust_name?.trim() ?? '';
            const rcoaCode = draft.rcoa_code?.trim() ?? '';
            if (!custName && !rcoaCode) {
                throw new Error('Enter a customer name or RCOA code before saving.');
            }
            return {
                loan_no: readRowValue(row, 'LOAN_NO'),
                cust_name: custName,
                rcoa_code: rcoaCode,
                start_date: date,
            };
        },
    },
    'rcoa-manual-data': {
        label: 'Manual RCOA data',
        description: 'Maintain manually supplied RCOA amounts, domains, and tiers.',
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
        const detailRecord = detail as { message?: unknown; error?: unknown };
        const message = typeof detailRecord.message === 'string' ? detailRecord.message : '';
        const databaseError = typeof detailRecord.error === 'string' ? detailRecord.error : '';
        if (message && databaseError && databaseError !== message) {
            return `${message} (${databaseError})`;
        }
        if (message) return message;
        if (databaseError) return databaseError;
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
    const [notice, setNotice] = useState<string | null>(null);
    const [reloadToken, setReloadToken] = useState(0);
    const [userId, setUserId] = useState<number | null>(null);
    const [reportingStarted, setReportingStarted] = useState(false);
    const [reportingEnded, setReportingEnded] = useState(false);
    const [reportingAction, setReportingAction] = useState<'start' | 'end' | null>(null);
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

    const definition = modeLabels[mode];
    const appliedDateTimestamp = toLocalDateTimestamp(appliedDate);
    const isDateEditable = Number.isFinite(appliedDateTimestamp)
        && appliedDateTimestamp >= editWindowStartTimestamp
        && appliedDateTimestamp <= todayTimestamp;
    const canEditRows = isDateEditable && !reportingEnded && !isSaving;
    const editBlockReason = !isDateEditable
        ? 'selected date is outside the inclusive one-month editing window'
        : reportingEnded
            ? 'reporting has ended'
            : isSaving
                ? 'another save is in progress'
                : 'editable';
    const totalPages = Math.max(1, pagination.totalPages || 1);
    const allPendingCount = pendingChanges.size;
    const pendingCount = allPendingCount;
    const visibleRows = actionFilter === 'editable' && !canEditRows ? [] : rows;
    const tableColumns = getTableColumns(rows, definition);

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
            reportingStarted,
            reportingEnded,
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
            reportingStarted,
            reportingEnded,
            isSaving,
            canEditRows,
            reason: editBlockReason,
        });
    }, [appliedDate, appliedDateTimestamp, appliedSearch, canEditRows, editBlockReason, isDateEditable, isSaving, mode, page, reportingEnded, reportingStarted]);

    const resetReportingState = () => {
        setReportingStarted(false);
        setReportingEnded(false);
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
        if (reportingStarted || reportingEnded) return;
        if (userId === null) {
            setErrorMessage('Your numeric user ID could not be resolved for reporting.');
            return;
        }

        setReportingAction('start');
        setErrorMessage(null);
        try {
            await startRcoaReporting(appliedDate, userId);
            setReportingStarted(true);
            setNotice(`Start reporting procedure completed successfully for ${appliedDate}.`);
        } catch (error: unknown) {
            setErrorMessage(getErrorMessage(error, 'Could not start reporting for this date.'));
        } finally {
            setReportingAction(null);
        }
    };

    const handleEndReporting = async () => {
        if (!reportingStarted || reportingEnded || userId === null) return;

        setReportingAction('end');
        setErrorMessage(null);
        try {
            await endRcoaReporting(appliedDate, userId);
            setReportingEnded(true);
            setNotice(`End reporting procedure completed successfully for ${appliedDate}.`);
        } catch (error: unknown) {
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
        if (!isNumericDraftValue(field, value, true)) return;
        updateDraft(field.key, value);
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

    const handleEditorKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
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
        if (!isNumericDraftValue(field, value, true)) return;
        setInsertDraft((current) => ({ ...current, [field.key]: value }));
    };

    const handleInsert = async () => {
        if (isInsertSaving || !definition.insertFields || !definition.buildInsertPayload) return;

        setInsertErrorMessage(null);
        try {
            definition.insertFields.forEach((field) => {
                const value = insertDraft[field.key]?.trim() ?? '';
                if (!value) throw new Error(`${field.label} is required.`);
                if (!isNumericDraftValue(field, value)) throw new Error(`${field.label} must be numeric.`);
            });

            const payload = definition.buildInsertPayload(insertDraft, appliedDate);
            setIsInsertSaving(true);
            await insertRcoaRow(mode, payload);
            closeInsertEditor(true);
            setNotice(`${definition.label} row inserted successfully. The list is refreshing.`);
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

    const handleInsertKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
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
            content = (
                <input
                    className="rcoa-inline-input"
                    type={getEditorInputType(editorField)}
                    inputMode={editorField.type === 'number' ? editorField.step === '1' ? 'numeric' : 'decimal' : undefined}
                    step={editorField.step}
                    value={draft[editorField.key] ?? value}
                    aria-label={`Edit ${column.label}`}
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

    const renderEditorFields = () => definition.fields.map((field) => (
        <label className="rcoa-field" key={field.key}>
            <span>{field.label}</span>
            <input
                type={getEditorInputType(field)}
                inputMode={field.type === 'number' ? field.step === '1' ? 'numeric' : 'decimal' : undefined}
                step={field.step}
                value={draft[field.key] ?? ''}
                onChange={(event) => updateEditorDraft(field, event.target.value)}
                onKeyDown={handleEditorKeyDown}
            />
        </label>
    ));

    const renderInsertFields = () => definition.insertFields?.map((field) => (
        <label className="rcoa-field" key={field.key}>
            <span>{field.label}</span>
            <input
                type={getEditorInputType(field)}
                inputMode={field.type === 'number' ? field.step === '1' ? 'numeric' : 'decimal' : undefined}
                step={field.step}
                value={insertDraft[field.key] ?? ''}
                disabled={isInsertSaving}
                onChange={(event) => updateInsertDraft(field, event.target.value)}
                onKeyDown={handleInsertKeyDown}
            />
        </label>
    ));

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
                        <button
                            type="button"
                            className="rcoa-primary-button"
                            onClick={handleStartReporting}
                            disabled={reportingStarted || reportingEnded || reportingAction !== null}
                        >
                            <FaPlay />
                            {reportingAction === 'start' ? 'Starting...' : reportingStarted ? 'Reporting started' : 'Start reporting'}
                        </button>
                    </div>
                </section>

                <section className="rcoa-status-strip" aria-live="polite">
                    <div className="rcoa-status-item">
                        <span className={`rcoa-status-dot ${reportingStarted ? 'is-live' : ''}`} />
                        <span>{reportingEnded ? 'Cycle closed' : reportingStarted ? 'Cycle in progress' : 'Cycle not started'}</span>
                    </div>
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
                    {errorMessage && (
                        <div className="rcoa-error" role="alert">
                            <FaExclamationCircle aria-hidden="true" />
                            <span>{errorMessage}</span>
                            <button type="button" onClick={() => setReloadToken((current) => current + 1)}>
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
                                {isLoading && (
                                    <tr>
                                        <td colSpan={tableColumns.length + 1} className="rcoa-table-state">
                                            <span className="rcoa-spinner" /> Loading {definition.label} records...
                                        </td>
                                    </tr>
                                )}
                                {!isLoading && !errorMessage && visibleRows.map((row, index) => {
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
                                {!isLoading && !errorMessage && visibleRows.length === 0 && (
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
                            disabled={page <= 1 || isLoading}
                            onClick={() => setPage((current) => Math.max(1, current - 1))}
                        >
                            <FaChevronLeft /> Prev
                        </button>
                        <span>Page <strong>{page}</strong> of <strong>{totalPages}</strong></span>
                        <button
                            type="button"
                            className="rcoa-ghost-button compact"
                            disabled={page >= totalPages || isLoading}
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
                    <button
                        type="button"
                        className="rcoa-end-button"
                        onClick={handleEndReporting}
                        disabled={!reportingStarted || reportingEnded || reportingAction !== null || allPendingCount > 0}
                        title={allPendingCount > 0 ? 'Save pending changes before ending reporting' : undefined}
                    >
                        <FaStop />
                        {reportingAction === 'end' ? 'Ending...' : reportingEnded ? 'Reporting ended' : 'End reporting'}
                    </button>
                </section>
            </div>

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
                            All row fields are required. The selected report date and system metadata will be added by the backend.
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
