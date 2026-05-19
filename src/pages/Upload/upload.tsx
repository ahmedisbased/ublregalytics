import { type ChangeEvent, useEffect, useRef, useState } from 'react';
import { getJobStatus, uploadDocuments } from '../../services/documentService';
import './upload.scss';

const allowedExtensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx'];

const Upload = () => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [sentFiles, setSentFiles] = useState<string[]>([]);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);
    const [uploadResponseMessage, setUploadResponseMessage] = useState<string | null>(null);
    const [jobResultMessage, setJobResultMessage] = useState<string | null>(null);
    const [jobStatusLabel, setJobStatusLabel] = useState<string | null>(null);
    const [isCheckingJobStatus, setIsCheckingJobStatus] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isSending, setIsSending] = useState(false);
    const [isFileInputDisabled, setIsFileInputDisabled] = useState(false);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const jobStatusIntervalRef = useRef<number | null>(null);
    const jobStatusInFlightRef = useRef(false);

    const stopJobStatusPolling = () => {
        if (jobStatusIntervalRef.current !== null) {
            window.clearInterval(jobStatusIntervalRef.current);
            jobStatusIntervalRef.current = null;
        }
        jobStatusInFlightRef.current = false;
        setIsCheckingJobStatus(false);
    };

    useEffect(() => {
        return () => {
            stopJobStatusPolling();
        };
    }, []);

    const openFileDialog = () => {
        if (isFileInputDisabled) {
            return;
        }
        fileInputRef.current?.click();
    };

    const clearFileInput = () => {
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleFileSelection = (event: ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files ?? []);
        clearFileInput();

        if (!files.length) {
            return;
        }

        const acceptedFiles: File[] = [];
        const rejectedFiles: string[] = [];

        files.forEach((file) => {
            const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
            if (allowedExtensions.includes(extension)) {
                acceptedFiles.push(file);
            } else {
                rejectedFiles.push(file.name);
            }
        });

        if (rejectedFiles.length) {
            setErrorMessage(`Unsupported files skipped: ${rejectedFiles.join(', ')}`);
        } else {
            setErrorMessage(null);
        }

        if (!acceptedFiles.length) {
            setSelectedFiles([]);
            setIsFileInputDisabled(false);
            setStatusMessage(null);
            setSentFiles([]);
            setErrorMessage('Only Word, Excel, or PDF documents are allowed.');
            return;
        }

        setSelectedFiles(acceptedFiles);
        setStatusMessage(null);
        setSentFiles([]);
        setIsFileInputDisabled(true);
    };

    const removeFile = (index: number) => {
        setSelectedFiles((files) => {
            const updated = files.filter((_, idx) => idx !== index);
            if (!updated.length) {
                setIsFileInputDisabled(false);
            }
            return updated;
        });
    };

    const handleSendDocuments = async () => {
        if (!selectedFiles.length) {
            return;
        }

        const usernameFromStorage = localStorage.getItem('userName')?.trim() || 'user';
        const fileNames = selectedFiles.map((file) => file.name);
        const formData = new FormData();
        selectedFiles.forEach((file) => {
            formData.append('files', file);
        });

        setIsSending(true);
        setUploadResponseMessage(null);
        setJobResultMessage(null);
        setJobStatusLabel(null);
        setErrorMessage(null);

        try {
            const response = await uploadDocuments(formData, usernameFromStorage);
            const responseMessage = response?.data?.message as string | undefined;
            const jobId = response?.data?.job_id as string | undefined;

            setUploadResponseMessage(responseMessage ?? null);
            setStatusMessage(`The following documents have been sent by ${usernameFromStorage}:`);
            setSentFiles(fileNames);
            setSelectedFiles([]);

            if (jobId) {
                stopJobStatusPolling();
                setIsCheckingJobStatus(true);
                setJobResultMessage(null);
                setJobStatusLabel(null);

                const capitalizeFirstLetter = (value: string) =>
                    value ? value.charAt(0).toUpperCase() + value.slice(1) : value;

                const deriveResultMessage = (statusData: unknown) => {
                    if (statusData && typeof statusData === 'object') {
                        const record = statusData as Record<string, unknown>;
                        const result = record.result as Record<string, unknown> | undefined;
                        const message = result?.message as string | undefined;
                        const error = result?.error as string | undefined;
                        return message ?? error ?? null;
                    }
                    return null;
                };

                const deriveStatusLabel = (statusData: unknown) => {
                    if (statusData && typeof statusData === 'object') {
                        const record = statusData as Record<string, unknown>;
                        const status = record.status as string | undefined;
                        return status ? capitalizeFirstLetter(status) : null;
                    }
                    if (typeof statusData === 'string') {
                        return capitalizeFirstLetter(statusData);
                    }
                    return null;
                };

                const isCompletedStatus = (statusData: unknown) => {
                    if (typeof statusData === 'string') {
                        return statusData.toLowerCase().includes('completed');
                    }
                    if (statusData && typeof statusData === 'object') {
                        const record = statusData as Record<string, unknown>;
                        const status = (record.status as string | undefined)?.toLowerCase();
                        return status === 'completed' || status?.includes('completed');
                    }
                    return false;
                };

                const pollJobStatus = async () => {
                    if (jobStatusInFlightRef.current) {
                        return false;
                    }
                    jobStatusInFlightRef.current = true;
                    try {
                        const jobStatusResponse = await getJobStatus(jobId);
                        const statusData = jobStatusResponse?.data;
                        const derivedMessage = deriveResultMessage(statusData);
                        const derivedStatusLabel = deriveStatusLabel(statusData);
                        setJobResultMessage(derivedMessage ?? null);
                        setJobStatusLabel(derivedStatusLabel ?? null);

                        if (isCompletedStatus(statusData)) {
                            stopJobStatusPolling();
                            return true;
                        }
                    } catch (jobStatusError) {
                        console.error('Failed to fetch job status', jobStatusError);
                        setJobResultMessage('Failed to fetch job status.');
                        setJobStatusLabel(null);
                        stopJobStatusPolling();
                        return true;
                    } finally {
                        jobStatusInFlightRef.current = false;
                    }
                    return false;
                };

                const completed = await pollJobStatus();
                if (!completed && !jobStatusIntervalRef.current) {
                    jobStatusIntervalRef.current = window.setInterval(pollJobStatus, 5000);
                }
            }
        } catch (error) {
            console.error('Failed to send documents', error);
            setErrorMessage('Failed to send documents. Please try again.');
            setUploadResponseMessage(null);
        } finally {
            setIsSending(false);
            setIsFileInputDisabled(false);
        }
    };

    return (
        <div className='document-upload-page container'>
            <h1 className='page-title'>Document Upload</h1>

            <div className='button-row'>
                <input
                    ref={fileInputRef}
                    type='file'
                    accept='.pdf,.doc,.docx,.xls,.xlsx'
                    multiple
                    onChange={handleFileSelection}
                    className='hidden-file-input'
                />

                <button
                    type='button'
                    className='btn btn-primary'
                    onClick={openFileDialog}
                    disabled={isFileInputDisabled || isSending}
                >
                    Upload Documents
                </button>

                <button
                    type='button'
                    className='btn btn-outline-primary'
                    onClick={handleSendDocuments}
                    disabled={!selectedFiles.length || isSending}
                >
                    {isSending ? 'Sending...' : 'Send To Backend'}
                </button>
            </div>

            <p className='helper-text'>Allowed formats: Word (.doc, .docx), Excel (.xls, .xlsx), PDF (.pdf)</p>

            {errorMessage && <div className='alert alert-danger' role='alert'>{errorMessage}</div>}
            {statusMessage && (
                <div className='alert alert-success' role='alert'>
                    <p className='mb-1'>{statusMessage}</p>
                    <ul className='mb-0'>
                        {sentFiles.map((name) => (
                            <li key={name}>{name}</li>
                        ))}
                    </ul>
                </div>
            )}

            {uploadResponseMessage && (
                <div className='alert alert-info mt-2' role='alert'>
                    {uploadResponseMessage}
                </div>
            )}

            {jobResultMessage && (
                <div className='alert alert-secondary mt-2' role='alert'>
                    {jobStatusLabel && <div className='fw-semibold'>{jobStatusLabel}</div>}
                    <div>{jobResultMessage}</div>
                </div>
            )}

            {isCheckingJobStatus && (
                <div className='job-status-loader mt-2' aria-label='Checking job status'>
                    <span className='spinner' />
                    <span className='ms-2'>Checking job status...</span>
                </div>
            )}

            <div className='file-list card'>
                <div className='card-body'>
                    <h2 className='file-list-title'>Selected Documents</h2>
                    {selectedFiles.length ? (
                        <ul className='list-group list-group-flush'>
                            {selectedFiles.map((file, index) => (
                                <li key={file.name + index} className='list-group-item d-flex justify-content-between align-items-center'>
                                    <span>{file.name}</span>
                                    <button type='button' className='btn btn-link' onClick={() => removeFile(index)}>
                                        Remove
                                    </button>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className='text-muted mb-0'>No documents selected.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Upload;
