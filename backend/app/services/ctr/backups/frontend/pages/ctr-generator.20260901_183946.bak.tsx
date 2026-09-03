import { useState } from "react";
import {
  FaArrowRight,
  FaCalendarAlt,
  FaCheckCircle,
  FaCloudUploadAlt,
  FaDownload,
  FaFileArchive,
  FaFileCsv,
  FaInfoCircle,
  FaLayerGroup,
  FaShieldAlt,
  FaTimes,
  FaTrashAlt,
} from "react-icons/fa";
import {
  generateCsv,
  generateCsvBatch,
  uploadFileStream,
  uploadFilesStream,
} from "../../services/ctrService";
import "./ctr-generator.scss";

type AccountType = "ENTITY" | "INDIVIDUAL";
type TransactionType = "CR" | "DR";
type CsvMode = "single" | "range";
type WorkspaceMode = "csv" | "xml";

type FileMetadata = {
  accountType?: AccountType;
  transactionType?: TransactionType;
  date?: string;
};

type Result = {
  blob: Blob;
  filename: string;
  title: string;
  detail: string;
};

type ApiError = {
  response?: {
    data?: Blob | { detail?: unknown };
  };
};

const isAccountType = (value: string | undefined): value is AccountType =>
  value === "ENTITY" || value === "INDIVIDUAL";

const isTransactionType = (value: string | undefined): value is TransactionType =>
  value === "CR" || value === "DR";

const fileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`;

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const metadataFromFilename = (filename: string): FileMetadata => {
  const parts = filename.replace(/\.csv$/i, "").split("_");
  const date = filename.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  const accountType = parts.find(isAccountType);
  const transactionType = parts.find(isTransactionType);

  return { accountType, transactionType, date };
};

const batchCategorySummary = (
  files: File[],
  fallbackTransactionType: TransactionType,
  fallbackAccountType: AccountType,
) => {
  const transactionTypes = new Set<TransactionType>();
  const accountTypes = new Set<AccountType>();

  files.forEach((file) => {
    const metadata = metadataFromFilename(file.name);
    transactionTypes.add(metadata.transactionType ?? fallbackTransactionType);
    accountTypes.add(metadata.accountType ?? fallbackAccountType);
  });

  const directions = ["CR", "DR"].filter((flag) => transactionTypes.has(flag as TransactionType));
  const accounts = ["ENTITY", "INDIVIDUAL"].filter((flag) => accountTypes.has(flag as AccountType));

  return {
    directions: directions.join("_") || fallbackTransactionType,
    accounts: accounts.join("_") || fallbackAccountType,
  };
};

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const readApiError = async (error: unknown, fallback: string) => {
  const response = (error as ApiError).response;
  const data = response?.data;

  if (data instanceof Blob) {
    try {
      const text = await data.text();
      if (text) {
        try {
          const parsed = JSON.parse(text) as { detail?: unknown };
          if (typeof parsed.detail === "string") return parsed.detail;
        } catch {
          return text;
        }
      }
    } catch {
      return fallback;
    }
  }

  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }

  return fallback;
};

type CategoryFieldsProps = {
  transactionType: TransactionType;
  accountType: AccountType;
  onTransactionTypeChange: (value: TransactionType) => void;
  onAccountTypeChange: (value: AccountType) => void;
};

const CategoryFields = ({
  transactionType,
  accountType,
  onTransactionTypeChange,
  onAccountTypeChange,
}: CategoryFieldsProps) => (
  <>
    <label className="ctr-field">
      <span className="ctr-field-label">Transaction direction</span>
      <select
        value={transactionType}
        onChange={(event) => onTransactionTypeChange(event.target.value as TransactionType)}
      >
        <option value="DR">Withdrawal (DR)</option>
        <option value="CR">Deposit (CR)</option>
      </select>
      <span className="ctr-field-hint">Choose the movement type in the report.</span>
    </label>
    <label className="ctr-field">
      <span className="ctr-field-label">Account profile</span>
      <select
        value={accountType}
        onChange={(event) => onAccountTypeChange(event.target.value as AccountType)}
      >
        <option value="ENTITY">Entity</option>
        <option value="INDIVIDUAL">Individual</option>
      </select>
      <span className="ctr-field-hint">This controls the report schema and XML blocks.</span>
    </label>
  </>
);

const CtrGenerator = () => {
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("csv");
  const [csvMode, setCsvMode] = useState<CsvMode>("single");
  const [transactionType, setTransactionType] = useState<TransactionType>("DR");
  const [accountType, setAccountType] = useState<AccountType>("ENTITY");
  const [date, setDate] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [uploadDate, setUploadDate] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  const clearFeedback = () => {
    setErrorMessage(null);
    setStatusMessage(null);
    setResult(null);
  };

  const switchWorkspace = (mode: WorkspaceMode) => {
    setWorkspaceMode(mode);
    clearFeedback();
  };

  const applyFileMetadata = (files: File[]) => {
    const metadata = metadataFromFilename(files[0]?.name ?? "");
    if (metadata.accountType) setAccountType(metadata.accountType);
    if (metadata.transactionType) setTransactionType(metadata.transactionType);
    if (metadata.date) setUploadDate(metadata.date);
  };

  const addFiles = (incomingFiles: File[]) => {
    const csvFiles = incomingFiles.filter((file) =>
      file.type === "text/csv" || file.name.toLowerCase().endsWith(".csv"),
    );

    if (!csvFiles.length) {
      setErrorMessage("Select one or more CSV files to continue.");
      return;
    }

    setSelectedFiles((currentFiles) => {
      const filesByKey = new Map(
        [...currentFiles, ...csvFiles].map((file) => [fileKey(file), file]),
      );
      const nextFiles = Array.from(filesByKey.values());
      applyFileMetadata(nextFiles);
      return nextFiles;
    });
    setErrorMessage(null);
    setStatusMessage(`${csvFiles.length} CSV file${csvFiles.length === 1 ? "" : "s"} added.`);
    setResult(null);
  };

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  };

  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setIsDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  };

  const removeFile = (fileToRemove: File) => {
    setSelectedFiles((files) => files.filter((file) => fileKey(file) !== fileKey(fileToRemove)));
    setStatusMessage(null);
    setResult(null);
  };

  const validateCsvRequest = () => {
    if (csvMode === "single" && !date) {
      setErrorMessage("Choose a report date first.");
      return false;
    }
    if (csvMode === "range") {
      if (!fromDate || !toDate) {
        setErrorMessage("Choose both the start and end dates.");
        return false;
      }
      if (fromDate > toDate) {
        setErrorMessage("The start date must be before the end date.");
        return false;
      }
    }
    return true;
  };

  const handleGenerateCsv = async () => {
    clearFeedback();
    if (!validateCsvRequest()) return;

    setIsLoading(true);
    setStatusMessage(csvMode === "single" ? "Preparing your CSV..." : "Preparing the CSV batch...");

    try {
      if (csvMode === "single") {
        const response = await generateCsv({
          transaction_date: date,
          cr_dr_flag: transactionType,
          entity_individual_flag: accountType,
        });
        const filename = `CTR_${accountType}_${transactionType}_${date}.csv`;
        setResult({
          blob: new Blob([response.data], { type: "text/csv" }),
          filename,
          title: "CSV ready",
          detail: `${date} / ${transactionType} / ${accountType}`,
        });
        setStatusMessage("The source CSV is ready to download.");
      } else {
        const response = await generateCsvBatch({
          from_date: fromDate,
          to_date: toDate,
          cr_dr_flag: transactionType,
          entity_individual_flag: accountType,
        });
        const filename = `CTR_${accountType}_${transactionType}_${fromDate}_${toDate}.zip`;
        setResult({
          blob: response.data,
          filename,
          title: "CSV batch ready",
          detail: `${fromDate} to ${toDate} / ${transactionType} / ${accountType}`,
        });
        setStatusMessage("The CSV batch is ready to download.");
      }
    } catch (error) {
      setErrorMessage(await readApiError(error, "CSV generation failed. Please try again."));
      setStatusMessage(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateXml = async () => {
    clearFeedback();
    if (!selectedFiles.length) {
      setErrorMessage("Add at least one CSV file first.");
      return;
    }

    const metadata = metadataFromFilename(selectedFiles[0].name);
    const fallbackDate = metadata.date || uploadDate || null;
    if (!fallbackDate && selectedFiles.length > 1) {
      setErrorMessage("Add a fallback report date when uploaded filenames do not contain dates.");
      return;
    }

    setIsLoading(true);
    setStatusMessage(
      selectedFiles.length === 1
        ? "Building the XML package..."
        : `Building one XML package from ${selectedFiles.length} CSV files...`,
    );

    try {
      const formData = new FormData();
      const metadataPayload = JSON.stringify({
        cr_dr_flag: transactionType,
        transaction_date: fallbackDate,
        entity_individual_flag: accountType,
      });

      if (selectedFiles.length === 1) {
        formData.append("file", selectedFiles[0]);
        formData.append("data", metadataPayload);
        const response = await uploadFileStream(formData);
        const filename = `CTR_XML_${accountType}_${transactionType}.zip`;
        setResult({
          blob: response.data,
          filename,
          title: "XML package ready",
          detail: `${selectedFiles[0].name} converted successfully`,
        });
      } else {
        const categorySummary = batchCategorySummary(
          selectedFiles,
          transactionType,
          accountType,
        );
        selectedFiles.forEach((file) => formData.append("files", file));
        formData.append("data", metadataPayload);
        const response = await uploadFilesStream(formData);
        const filename = `CTR_XML_BATCH_${categorySummary.accounts}_${categorySummary.directions}.zip`;
        setResult({
          blob: response.data,
          filename,
          title: "XML batch ready",
          detail: `${selectedFiles.length} CSV files converted: ${categorySummary.directions}`,
        });
      }
      setStatusMessage("The XML package is ready to download.");
    } catch (error) {
      setErrorMessage(await readApiError(error, "XML generation failed. Please try again."));
      setStatusMessage(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="ctr-page">
      <div className="ctr-shell">
        <header className="ctr-hero">
          <div className="ctr-hero-topline">
            <span className="ctr-kicker">Regulatory reporting workspace</span>
            <span className="ctr-live-pill">
              <span className="ctr-live-dot" /> CTR pipeline
            </span>
          </div>
          <div className="ctr-hero-grid">
            <div>
              <p className="ctr-overline">Cash Transaction Report</p>
              <h1>Prepare clean source data, then ship compliant XML.</h1>
              <p className="ctr-hero-copy">
                Generate daily or range-based CSV packages and convert one or many source files
                into a single downloadable XML archive.
              </p>
            </div>
            <div className="ctr-hero-card">
              <FaShieldAlt size={20} />
              <div>
                <strong>Identifier-safe workflow</strong>
                <span>CNICs and account values remain text through the upload path.</span>
              </div>
            </div>
          </div>
        </header>

        <div className="ctr-workspace">
          <aside className="ctr-guide">
            <div className="ctr-guide-heading">
              <span className="ctr-guide-icon"><FaInfoCircle /></span>
              <div>
                <p className="ctr-overline">A simple handoff</p>
                <h2>Three steps to file-ready output</h2>
              </div>
            </div>
            <ol className="ctr-steps">
              <li>
                <span className="ctr-step-number">01</span>
                <div><strong>Set the category</strong><span>Choose direction and account profile.</span></div>
              </li>
              <li>
                <span className="ctr-step-number">02</span>
                <div><strong>Generate or upload</strong><span>Work with one date, a date range, or a CSV set.</span></div>
              </li>
              <li>
                <span className="ctr-step-number">03</span>
                <div><strong>Download the package</strong><span>Receive a CSV, CSV ZIP, or XML ZIP.</span></div>
              </li>
            </ol>
            <div className="ctr-guide-note">
              <FaLayerGroup />
              <span>Batch downloads include a manifest with skipped dates or files.</span>
            </div>
          </aside>

          <main className="ctr-panel">
            <div className="ctr-panel-heading">
              <div>
                <p className="ctr-overline">CTR command center</p>
                <h2>What do you want to do?</h2>
              </div>
              <span className="ctr-panel-status">Secure session</span>
            </div>

            <div className="ctr-workspace-tabs" role="tablist" aria-label="CTR workflow">
              <button
                type="button"
                className={workspaceMode === "csv" ? "active" : ""}
                onClick={() => switchWorkspace("csv")}
                role="tab"
                aria-selected={workspaceMode === "csv"}
              >
                <FaFileCsv />
                <span><strong>Prepare CSV</strong><small>Generate source files</small></span>
              </button>
              <button
                type="button"
                className={workspaceMode === "xml" ? "active" : ""}
                onClick={() => switchWorkspace("xml")}
                role="tab"
                aria-selected={workspaceMode === "xml"}
              >
                <FaFileArchive />
                <span><strong>Build XML</strong><small>Convert one or many CSVs</small></span>
              </button>
            </div>

            {errorMessage && <div className="ctr-alert error" role="alert">{errorMessage}</div>}
            {statusMessage && !errorMessage && <div className="ctr-alert status"><FaCheckCircle /> {statusMessage}</div>}

            {workspaceMode === "csv" ? (
              <section className="ctr-section" aria-labelledby="csv-heading">
                <div className="ctr-section-heading">
                  <span className="ctr-section-icon blue"><FaFileCsv /></span>
                  <div>
                    <p className="ctr-overline">Source data</p>
                    <h3 id="csv-heading">Generate CSV output</h3>
                    <p>Pull one report day or package a short date range into a ZIP.</p>
                  </div>
                </div>

                <div className="ctr-choice-row" role="group" aria-label="CSV generation mode">
                  <button type="button" className={csvMode === "single" ? "selected" : ""} onClick={() => setCsvMode("single")}>
                    <span className="ctr-choice-mark">01</span>
                    <span><strong>Single date</strong><small>One CSV file</small></span>
                  </button>
                  <button type="button" className={csvMode === "range" ? "selected" : ""} onClick={() => setCsvMode("range")}>
                    <span className="ctr-choice-mark">02</span>
                    <span><strong>Date range</strong><small>Multiple CSVs in a ZIP</small></span>
                  </button>
                </div>

                <div className="ctr-form-grid">
                  {csvMode === "single" ? (
                    <label className="ctr-field">
                      <span className="ctr-field-label"><FaCalendarAlt /> Report date</span>
                      <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
                      <span className="ctr-field-hint">Select the reporting day to query.</span>
                    </label>
                  ) : (
                    <>
                      <label className="ctr-field">
                        <span className="ctr-field-label"><FaCalendarAlt /> Start date</span>
                        <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
                        <span className="ctr-field-hint">The first day in the package.</span>
                      </label>
                      <label className="ctr-field">
                        <span className="ctr-field-label"><FaCalendarAlt /> End date</span>
                        <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
                        <span className="ctr-field-hint">Maximum range: 31 days.</span>
                      </label>
                    </>
                  )}
                  <CategoryFields
                    transactionType={transactionType}
                    accountType={accountType}
                    onTransactionTypeChange={setTransactionType}
                    onAccountTypeChange={setAccountType}
                  />
                </div>

                <div className="ctr-action-row">
                  <div><strong>{csvMode === "single" ? "One source file" : "Range package"}</strong><span>{csvMode === "single" ? "Ready when you are." : "Each day is returned as its own CSV."}</span></div>
                  <button type="button" className="ctr-primary-button" onClick={handleGenerateCsv} disabled={isLoading}>
                    {isLoading ? "Working..." : csvMode === "single" ? "Generate CSV" : "Generate CSV batch"}
                    {!isLoading && <FaArrowRight />}
                  </button>
                </div>
              </section>
            ) : (
              <section className="ctr-section" aria-labelledby="xml-heading">
                <div className="ctr-section-heading">
                  <span className="ctr-section-icon violet"><FaFileArchive /></span>
                  <div>
                    <p className="ctr-overline">XML conversion</p>
                    <h3 id="xml-heading">Upload source CSVs</h3>
                    <p>Drop one file for the existing flow, or select a complete date-range batch.</p>
                  </div>
                </div>

                <label
                  className={`ctr-dropzone ${isDragging ? "dragging" : ""}`}
                  onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                >
                  <input type="file" accept=".csv,text/csv" multiple onChange={handleFileSelection} />
                  <span className="ctr-upload-icon"><FaCloudUploadAlt /></span>
                  <strong>Drop CSV files here</strong>
                  <span>or browse from your computer</span>
                  <small>Filenames with dates are detected automatically.</small>
                </label>

                {selectedFiles.length > 0 && (
                  <div className="ctr-file-list" aria-label="Selected CSV files">
                    <div className="ctr-file-list-heading"><span>{selectedFiles.length} file{selectedFiles.length === 1 ? "" : "s"} selected</span><button type="button" onClick={() => setSelectedFiles([])}>Clear all</button></div>
                    {selectedFiles.map((file) => {
                      const metadata = metadataFromFilename(file.name);
                      return (
                        <div className="ctr-file-row" key={fileKey(file)}>
                          <span className="ctr-file-symbol"><FaFileCsv /></span>
                          <span className="ctr-file-details"><strong>{file.name}</strong><small>{formatBytes(file.size)}{metadata.date ? ` / ${metadata.date}` : " / date from fallback"}</small></span>
                          <span className="ctr-file-tags" aria-label="Detected category">
                            <span className={`ctr-file-tag ${metadata.transactionType === "CR" ? "credit" : "debit"}`}>{metadata.transactionType ?? transactionType}</span>
                            <span className="ctr-file-tag account">{metadata.accountType ?? accountType}</span>
                          </span>
                          <button type="button" className="ctr-remove-file" onClick={() => removeFile(file)} aria-label={`Remove ${file.name}`}><FaTrashAlt /></button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="ctr-form-grid upload-fields">
                  <CategoryFields
                    transactionType={transactionType}
                    accountType={accountType}
                    onTransactionTypeChange={setTransactionType}
                    onAccountTypeChange={setAccountType}
                  />
                  <label className="ctr-field">
                    <span className="ctr-field-label"><FaCalendarAlt /> Fallback report date <em>optional</em></span>
                    <input type="date" value={uploadDate} onChange={(event) => setUploadDate(event.target.value)} />
                    <span className="ctr-field-hint">Used only when a CSV filename has no date.</span>
                  </label>
                </div>

                <div className="ctr-action-row">
                  <div><strong>{selectedFiles.length > 1 ? "Batch XML conversion" : "Single XML conversion"}</strong><span>{selectedFiles.length > 1 ? "All valid files will be combined into one ZIP." : "The original single-file endpoint remains unchanged."}</span></div>
                  <button type="button" className="ctr-primary-button violet-button" onClick={handleGenerateXml} disabled={isLoading || !selectedFiles.length}>
                    {isLoading ? "Working..." : selectedFiles.length > 1 ? "Build XML batch" : "Build XML"}
                    {!isLoading && <FaArrowRight />}
                  </button>
                </div>
              </section>
            )}

            {result && (
              <section className="ctr-result" aria-live="polite">
                <span className="ctr-result-icon"><FaCheckCircle /></span>
                <div><p className="ctr-overline">Ready for download</p><h3>{result.title}</h3><span>{result.detail}</span></div>
                <button type="button" className="ctr-download-button" onClick={() => downloadBlob(result.blob, result.filename)}><FaDownload /> Download</button>
              </section>
            )}
          </main>
        </div>

        <footer className="ctr-footer"><span><FaShieldAlt /> Identifier-aware processing</span><span><FaTimes /> No source files are stored by the browser</span></footer>
      </div>
    </div>
  );
};

export default CtrGenerator;
