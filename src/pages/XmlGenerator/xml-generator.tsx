import { useState } from 'react';
import { FaFileCode, FaDownload, FaInfoCircle } from 'react-icons/fa';
import { generateXml } from '../../services/xmlService';
import './xml-generator.scss';

const XmlGenerator = () => {
    const [accountNumber, setAccountNumber] = useState('');
    const [transactionId, setTransactionId] = useState('');
    const [fromDate, setFromDate] = useState('');
    const [toDate, setToDate] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [xmlBlob, setXmlBlob] = useState<Blob | null>(null);
    const [generatedAccount, setGeneratedAccount] = useState<string | null>(null);

    const validate = () => {
        if (!accountNumber.trim()) {
            setErrorMessage('Account Number is required.');
            return false;
        }
        if (fromDate && !/^\d{4}-\d{2}-\d{2}$/.test(fromDate)) {
            setErrorMessage('From Date must be in YYYY-MM-DD format.');
            return false;
        }
        if (toDate && !/^\d{4}-\d{2}-\d{2}$/.test(toDate)) {
            setErrorMessage('To Date must be in YYYY-MM-DD format.');
            return false;
        }
        return true;
    };

    const handleGenerate = async () => {
        setErrorMessage(null);
        setXmlBlob(null);
        setGeneratedAccount(null);

        if (!validate()) return;

        setIsLoading(true);
        try {
            const response = await generateXml({
                account_number: accountNumber.trim(),
                transaction_id: transactionId.trim() || null,
                from_date: fromDate || null,
                to_date: toDate || null,
            });
            const xmlString = response.data.xml;
            const blob = new Blob([xmlString], { type: 'application/xml' });
            setXmlBlob(blob);
            setGeneratedAccount(accountNumber.trim());
        } catch {
            setErrorMessage('Failed to generate XML. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

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
                            <p className="text-muted mb-4 small">
                                Enter an account number to query the backend, generate an XML report, and download it.
                            </p>

                            {errorMessage && (
                                <div className="alert alert-danger" role="alert">
                                    {errorMessage}
                                </div>
                            )}

                            {/* Form Fields */}
                            <div className="mb-3">
                                <label htmlFor="accountNumber" className="form-label fw-medium">
                                    Account Number <span className="text-danger">*</span>
                                </label>
                                <input
                                    id="accountNumber"
                                    type="text"
                                    className="form-control bg-light"
                                    placeholder="e.g., 326247471"
                                    value={accountNumber}
                                    onChange={(e) => setAccountNumber(e.target.value)}
                                />
                            </div>

                            <div className="mb-3">
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
                                    onChange={(e) => setTransactionId(e.target.value)}
                                />
                                <div className="form-text">
                                    Single transaction ID or multiple IDs separated by commas.
                                </div>
                            </div>

                            <div className="mb-3">
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

                            <div className="mb-4">
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
