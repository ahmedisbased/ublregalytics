import { useState } from 'react';
import { FaFileCode, FaDownload, FaInfoCircle } from 'react-icons/fa';
import {
    generateXmlStream,
    type StrErrorDetail,
    type StrStreamEvent,
} from '../../services/xmlService';
import './xml-generator.scss';

type ErrorLike = {
    response?: {
        status?: number;
        data?: unknown;
    };
    message?: string;
};

type ProgressStatus = {
    stage: string;
    message: string;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null;

const readStrError = (error: unknown) => {
    const response = (error as ErrorLike).response;
    const data = response?.data;
    const detail = isRecord(data) ? data.detail : undefined;

    if (isRecord(detail)) {
        return {
            status: response?.status,
            detail: detail as StrErrorDetail,
        };
    }

    if (typeof detail === 'string') {
        return {
            status: response?.status,
            detail: { message: detail } as StrErrorDetail,
        };
    }

    return { status: response?.status, detail: null as StrErrorDetail | null };
};

const categoryLabel = (category: string | undefined) => {
    if (!category) return 'STR ERROR';
    if (category === 'TERADATA') return 'TERADATA ERROR';
    if (category === 'NO_DATA') return 'NO DATA';
    return `${category.replaceAll('_', ' ')} ERROR`;
};

const formatStrError = (
    detail: StrErrorDetail | null,
    status: number | undefined,
    fallback: string,
) => {
    if (detail?.message) {
        if (detail.category === 'TERADATA' || detail.category === 'NO_DATA') {
            return detail.message;
        }
        const category = categoryLabel(detail.category);
        const stage = detail.stage ? ` Stage: ${detail.stage}.` : '';
        return `${category}: ${detail.message}${stage}`;
    }
    if (status === 504) return 'TIMEOUT ERROR: The STR request exceeded the server time limit.';
    return fallback;
};

const progressSteps = [
    { key: 'connecting', label: 'Connect to Teradata' },
    { key: 'running_query', label: 'Run query' },
    { key: 'building_xml', label: 'Build XML' },
    { key: 'complete', label: 'Ready' },
];

const progressRank = (stage: string) => {
    if (stage === 'starting' || stage === 'connecting') return 0;
    if (stage === 'connected' || stage === 'running_query') return 1;
    if (stage === 'building_xml') return 2;
    if (stage === 'complete') return 3;
    return -1;
};

const XmlGenerator = () => {
    const [accountNumber, setAccountNumber] = useState('');
    const [transactionId, setTransactionId] = useState('');
    const [fromDate, setFromDate] = useState('');
    const [toDate, setToDate] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [xmlBlob, setXmlBlob] = useState<Blob | null>(null);
    const [generatedAccount, setGeneratedAccount] = useState<string | null>(null);
    const [requestId, setRequestId] = useState<string | null>(null);
    const [progressStatus, setProgressStatus] = useState<ProgressStatus | null>(null);

    const reportValidationError = (message: string) => {
        setErrorMessage(message);
        setProgressStatus({ stage: 'error', message });
    };

    const validate = () => {
        if (!accountNumber.trim()) {
            reportValidationError('Account Number is required.');
            return false;
        }
        if (transactionId.trim()){
            if (!/^\d+(?:\s*,\s*\d+)*$/.test(transactionId.trim())) {
                reportValidationError('Transaction ID must be numbers separated by commas (e.g., 6576766566,6576765588) ');
                return false;
            }
        }
        
        if (fromDate && !/^\d{4}-\d{2}-\d{2}$/.test(fromDate)) {
            reportValidationError('From Date must be in YYYY-MM-DD format.');
            return false;
        }
        if (toDate && !/^\d{4}-\d{2}-\d{2}$/.test(toDate)) {
            reportValidationError('To Date must be in YYYY-MM-DD format.');
            return false;
        }
        return true;
    };

    const handleGenerate = async () => {
        setErrorMessage(null);
        setXmlBlob(null);
        setGeneratedAccount(null);
        setRequestId(null);
        setProgressStatus({
            stage: 'starting',
            message: 'Starting STR XML generation...',
        });

        if (!validate()) return;

        setIsLoading(true);
        try {
            const handleStreamEvent = (event: StrStreamEvent) => {
                setRequestId(event.request_id);
                if (event.type === 'status') {
                    setProgressStatus({ stage: event.stage, message: event.message });
                    return;
                }

                if (event.type === 'complete') {
                    const blob = new Blob([event.xml], { type: 'application/xml' });
                    setXmlBlob(blob);
                    setGeneratedAccount(accountNumber.trim());
                    setProgressStatus({
                        stage: 'complete',
                        message: 'XML generation completed successfully.',
                    });
                    return;
                }

                const message = formatStrError(event.error, undefined, 'STR generation failed.');
                setErrorMessage(message);
                setProgressStatus({ stage: 'error', message });
            };

            await generateXmlStream(
                {
                    main_account: accountNumber.trim(),
                    transaction_number: transactionId.trim() || '',
                    from_date: fromDate || null,
                    to_date: toDate || null,
                },
                handleStreamEvent,
            );
        } catch (err) {
            const parsedError = readStrError(err);
            const errorLike = err as ErrorLike;
            const message = !errorLike.response
                ? `NETWORK ERROR: Could not reach the STR backend. ${errorLike.message ?? 'Check the API connection and try again.'}`
                : formatStrError(
                    parsedError.detail,
                    parsedError.status,
                    `STR ERROR: The backend returned HTTP ${parsedError.status ?? 'an unknown error'}.`,
                );

            setRequestId(parsedError.detail?.request_id ?? null);
            setErrorMessage(message);
            setProgressStatus({ stage: 'error', message });
        } finally {
            setIsLoading(false);
        }
    };

    const handleNumericChange = (e : React.ChangeEvent<HTMLInputElement>,
        setter : (value : string) => void ) => {
        const value = e.target.value;

        const cleaned = value.replace(/\D/g, "")

        setter(cleaned);
    }


    const handleDownload = () => {
        if (!xmlBlob || !generatedAccount) return;
        const url = URL.createObjectURL(xmlBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${generatedAccount}.xml`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="xml-generator-page container">
            <div className="row g-4">

                {/* Instructions Sidebar */}
                <div className="col-12 col-md-3">
                    <div className="card border border-secondary shadow-sm xml-instructions-panel">
                        <div className="card-body">
                            <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2 text-primary">
                                <FaInfoCircle />
                                Instructions
                            </h2>
                            <ol className="mb-0">
                                <li>Enter a valid account number.</li>
                                <li>Click <strong className="text-primary">Generate XML</strong>.</li>
                                <li>The system will query the backend and generate an XML report.</li>
                                <li>Once ready, download the XML file.</li>
                            </ol>
                        </div>
                    </div>
                </div>

                {/* Form Panel */}
                <div className="col-12 col-md-9">
                    <div className="card border border-secondary shadow-sm">
                        <div className="card-body p-4">

                            {/* Header */}
                            <div className="d-flex align-items-center gap-3 mb-2">
                                <div className="bg-primary d-flex align-items-center justify-content-center rounded-circle text-white" style={{ width: '42px', height: '42px', flexShrink: 0 }}>
                                    <FaFileCode size={20} />
                                </div>
                                <h1 className="h3 fw-bold mb-0">Account XML Generator</h1>
                            </div>

                            {errorMessage && (
                                <div className="alert alert-danger" role="alert">
                                    <strong className="d-block mb-1">STR generation failed</strong>
                                    <span>{errorMessage}</span>
                                </div>
                            )}

                            {progressStatus && (
                                <section
                                    className={`str-progress-panel ${progressStatus.stage === 'error' ? 'error' : ''}`}
                                    aria-live="polite"
                                >
                                    <div className="str-progress-heading">
                                        <div className="d-flex align-items-start gap-2">
                                            <span className="str-progress-dot" />
                                            <div>
                                                <p className="str-progress-kicker">STR generation status</p>
                                                <strong>{progressStatus.message}</strong>
                                            </div>
                                        </div>
                                        {requestId && <small>Request ID: {requestId}</small>}
                                    </div>
                                    <ol className="str-progress-steps">
                                        {progressSteps.map((step, index) => {
                                            const rank = progressRank(progressStatus.stage);
                                            const stepState = progressStatus.stage === 'error'
                                                ? 'pending'
                                                : rank > index
                                                    ? 'complete'
                                                    : rank === index
                                                        ? 'active'
                                                        : 'pending';
                                            return (
                                                <li className={stepState} key={step.key}>
                                                    <span>{index + 1}</span>
                                                    <small>{step.label}</small>
                                                </li>
                                            );
                                        })}
                                    </ol>
                                </section>
                            )}

                            {/* Form Fields */}
                            
                            
                            <div className="row g-3 mb-4">
                                <div className='col-md-6'>
                                    <label htmlFor="accountNumber" className="form-label fw-medium">
                                        Account Number <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        id="accountNumber"
                                        type="text"
                                        className="form-control bg-light"
                                        placeholder="e.g., 326247471"
                                        value={accountNumber}
                                        onChange={(e) => handleNumericChange(e, setAccountNumber)}
                                    />     
                                </div>
        
                            <div className='col-md-6'>
                                <label htmlFor="transactionId" className="form-label fw-medium">
                                    Transaction ID{' '}
                                    <span className="text-muted fw-normal small">(optional)</span>
                                </label>
                                <input
                                    id="transactionId"
                                    type="text"
                                    className="form-control bg-light"
                                    placeholder="e.g., 3743324313"
                                    value={transactionId}
                                    onChange={(e) => {
                                        const filtered = e.target.value.replace(/[^0-9, ]/g, '');
                                        setTransactionId(filtered);
                                    }}
                                />
                                <div className="form-text">
                                    Single transaction ID or multiple IDs separated by commas.
                                </div>
                            </div>
                            </div>
                            
                            
                            
                            <div className="row g-3 mb-4">
                                <div className='col-md-6'>
                                    <label htmlFor="fromDate" className="form-label fw-medium">
                                        From Date{' '}
                                        <span className="text-muted fw-normal small">(optional)</span>
                                    </label>
                                    <input
                                        id="fromDate"
                                        type="date"
                                        className="form-control bg-light"
                                        value={fromDate}
                                        onChange={(e) => setFromDate(e.target.value)}
                                    />     
                                </div>
        
                            <div className='col-md-6'>
                                <label htmlFor="toDate" className="form-label fw-medium">
                                        To Date{' '}
                                        <span className="text-muted fw-normal small">(optional)</span>
                                    </label>
                                    <input
                                        id="toDate"
                                        type="date"
                                        className="form-control bg-light"
                                        value={toDate}
                                        onChange={(e) => setToDate(e.target.value)}
                                    />
                            </div>
                            </div>
                            
                            <div className="d-flex justify-content-end">
                                <button
                                    type="button"
                                    className="btn btn-primary btn-sm xml-generate-btn"
                                    onClick={handleGenerate}
                                    disabled={isLoading || !accountNumber.trim()}
                                >
                                    {isLoading ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                                            Generating...
                                        </>
                                    ) : (
                                        <span className="xml-generate-btn-text">Generate XML</span>
                                    )}
                                </button>
                            </div>

                            {/* Result Section */}
                            {xmlBlob && generatedAccount && (
                                <>
                                    <hr className="my-4" />
                                    <div className="text-center xml-result-section">
                                        <div className="d-flex align-items-center justify-content-center gap-2 mb-3">
                                            <FaFileCode className="text-primary" />
                                            <span className="fw-semibold">
                                                XML Created For Account: <span className="text-primary">{generatedAccount}</span>
                                            </span>
                                        </div>
                                        <button
                                            type="button"
                                            className="btn btn-primary xml-download-btn d-inline-flex align-items-center gap-2"
                                            onClick={handleDownload}
                                        >
                                            <FaDownload />
                                            <span>Download XML File</span>
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default XmlGenerator;
