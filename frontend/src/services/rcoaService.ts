import api from './api';

export type RcoaMode =
    | 'gl-sl-mapping'
    | 'term-deposits'
    | 'loan-type'
    | 'sl-roca'
    | 'tfcs-sukus'
    | 'rcoa-manual-data'
    | 'adjustment';
export type RcoaRow = Record<string, unknown>;

export interface RcoaPagination {
    currentPage: number;
    pageSize: number;
    totalRecords: number;
    totalPages: number;
}

export interface RcoaPageResponse {
    data: RcoaRow[];
    pagination: RcoaPagination;
}

export interface RcoaBatchChange {
    mode: RcoaMode;
    change: Record<string, unknown>;
}

export interface RcoaBatchUpdateResponse {
    status: string;
    updated: number;
    data: RcoaRow[];
}

export interface RcoaMutationResponse {
    status: string;
    message: string;
    data: RcoaRow[];
}

export interface CurrentUserResponse {
    sub: string;
}

const viewEndpoints: Record<RcoaMode, string> = {
    'gl-sl-mapping': '/view-gl-sl-mapping',
    'term-deposits': '/view-term-deposits',
    'loan-type': '/view-loan-type',
    'sl-roca': '/view-sl-rcoa',
    'tfcs-sukus': '/view-tfcs-sukus',
    'rcoa-manual-data': '/view-rcoa-manual-data',
    adjustment: '/view-adjustments-format',
};

const updateEndpoints: Record<RcoaMode, string> = {
    'gl-sl-mapping': '/update-gl-sl-mapping',
    'term-deposits': '/update-term-deposits',
    'loan-type': '/update-loan-type',
    'sl-roca': '/update-sl-rcoa',
    'tfcs-sukus': '/update-tfcs-sukus',
    'rcoa-manual-data': '/update-rcoa-manual-data',
    adjustment: '/update-adjustments-format',
};

const insertEndpoints: Partial<Record<RcoaMode, string>> = {
    adjustment: '/insert-adjustments-format',
    'rcoa-manual-data': '/insert-rcoa-manual-data',
    'tfcs-sukus': '/insert-tfcs-sukus',
};

export const fetchRcoaPage = async (
    mode: RcoaMode,
    date: string,
    page: number,
    search = '',
) => {
    const normalizedSearch = search.trim();
    const { data } = await api.post<RcoaPageResponse>(viewEndpoints[mode], {
        date,
        page,
        search: normalizedSearch && !['none', 'null'].includes(normalizedSearch.toLowerCase())
            ? normalizedSearch
            : undefined,
    });
    return data;
};

export const updateRcoaRow = async (mode: RcoaMode, payload: Record<string, unknown>) => {
    const { data } = await api.post(updateEndpoints[mode], payload);
    return data;
};

export const insertRcoaRow = async (mode: RcoaMode, payload: Record<string, unknown>) => {
    const endpoint = insertEndpoints[mode];
    if (!endpoint) throw new Error(`Insert is not supported for ${mode}.`);
    const { data } = await api.post<RcoaMutationResponse>(endpoint, payload);
    return data;
};

export const batchUpdateRcoa = async (
    mode: RcoaMode,
    changes: Record<string, unknown>[],
) => {
    const { data } = await api.post<RcoaBatchUpdateResponse>('/batch-update-rcoa', { mode, changes });
    return data;
};

export const batchUpdateAllRcoa = async (changes: RcoaBatchChange[]) => {
    const { data } = await api.post<RcoaBatchUpdateResponse>('/batch-update-rcoa-all', { changes });
    return data;
};

export const startRcoaReporting = async (date: string, userId: number) => {
    const { data } = await api.post<number>('/start-reporting', {
        date,
        user_id: userId,
    });
    return data;
};

export const endRcoaReporting = async (date: string, userId: number) => {
    const { data } = await api.post<number>('/end-reporting', {
        date,
        user_id: userId,
    });
    return data;
};

export const getCurrentUser = async () => {
    const { data } = await api.get<CurrentUserResponse>('/me');
    return data;
};
