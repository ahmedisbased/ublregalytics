import api from "./api";

export interface XmlGeneratorParams {
  main_account: string;
  transaction_number: string | null;
  from_date: string | null;
  to_date: string | null;
}

export type StrLog = {
  timestamp: string;
  level: string;
  stage: string;
  message: string;
  details?: Record<string, unknown>;
};

export type StrGenerationResponse = {
  xml: string;
  request_id: string;
  logs: StrLog[];
};

export type StrErrorDetail = {
  code?: string;
  category?: string;
  stage?: string;
  message?: string;
  error_type?: string;
  request_id?: string;
  logs?: StrLog[];
};

export type StrStreamStatusEvent = {
  type: 'status';
  request_id: string;
  stage: string;
  message: string;
  timestamp?: string;
};

export type StrStreamCompleteEvent = {
  type: 'complete';
  request_id: string;
  xml: string;
};

export type StrStreamErrorEvent = {
  type: 'error';
  request_id: string;
  error: StrErrorDetail;
};

export type StrStreamEvent =
  | StrStreamStatusEvent
  | StrStreamCompleteEvent
  | StrStreamErrorEvent;

export const generateXml = async (params: XmlGeneratorParams) => {
  return api.post<StrGenerationResponse>("/generate-xml", params);
};

export const generateXmlStream = async (
  params: XmlGeneratorParams,
  onEvent: (event: StrStreamEvent) => void,
): Promise<StrStreamEvent> => {
  const baseUrl = (api.defaults.baseURL || `${window.location.origin}/`).replace(/\/?$/, '/');
  const token = localStorage.getItem('token');
  const response = await fetch(`${baseUrl}generate-xml/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = undefined;
    }
    const error = new Error(`STR stream request failed with HTTP ${response.status}`) as Error & {
      response?: { status: number; data?: unknown };
    };
    error.response = { status: response.status, data };
    throw error;
  }

  if (!response.body) {
    throw new Error('The STR progress stream did not return a readable body.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalEvent: StrStreamEvent | null = null;

  const consumeBlock = (block: string) => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!data) return;

    const event = JSON.parse(data) as StrStreamEvent;
    onEvent(event);
    if (event.type === 'complete' || event.type === 'error') {
      finalEvent = event;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    let separatorIndex = buffer.indexOf('\n\n');
    while (separatorIndex >= 0) {
      consumeBlock(buffer.slice(0, separatorIndex));
      buffer = buffer.slice(separatorIndex + 2);
      separatorIndex = buffer.indexOf('\n\n');
    }

    if (done) break;
  }

  if (buffer.trim()) consumeBlock(buffer);
  if (!finalEvent) throw new Error('The STR progress stream ended before a final result.');
  return finalEvent;
};
