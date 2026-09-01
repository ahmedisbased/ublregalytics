import { useState } from 'react';
import { FaDownload, FaFileArchive, FaInfoCircle } from 'react-icons/fa';
import { generateCsv } from '../../services/ctrService';
import '../XmlGenerator/xml-generator.scss';

const CtrGenerator = () => {
  const [date, setDate] = useState('');
  const [transactionType, setTransactionType] = useState<'DR' | 'CR'>('DR');
  const [accountType, setAccountType] = useState<'ENTITY' | 'INDIVIDUAL'>('ENTITY');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [zipBlob, setZipBlob] = useState<Blob | null>(null);
  const [csvBlob, setCsvBlob] = useState<Blob | null>(null);
  const [generatedDate, setGeneratedDate] = useState<string | null>(null);
  const [isCsvUploaded, setIsCsvUploaded] = useState(false); // Track if a CSV file has been uploaded
  const hasdate = date !== ''
  const validate = () => {
    if (date === '' && !isCsvUploaded) {
      setErrorMessage('Date is required.');
      return false;
    }

    if (!(date === '')){

   
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      setErrorMessage('Date must be in YYYY-MM-DD format.');
      return false;
    }
  }

    return true;
  };
  const file = localStorage.getItem('csv')

  console.log(`file is ${file}`)
  const handleGenerate = async () => {
    setErrorMessage(null);
    setZipBlob(null);
    setGeneratedDate(null);
    console.log("trying to generate xml")


    if (!validate()) return;
    if (!file) return;

    setIsLoading(true);
    console.log("set loading to true")
    
    try {
      const response = await generateCsv ({
        transaction_date: date.trim(),
        cr_dr_flag: transactionType,
        entity_individual_flag: accountType,
      
      })
      console.log(
        "response is ", response
      )
      const contentType = response.headers['content-type'] || 'application/zip';
      console.log('CTR generation response:', response);
      const blob = new Blob([response.data], { type: contentType });
      setZipBlob(blob);
      setGeneratedDate(date.trim());
    } catch {
      setErrorMessage('CTR generation failed. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateCsv = async () => {
    setErrorMessage(null);
    setCsvBlob(null);
    setGeneratedDate(null);

    if (!validate()) return;

    setIsLoading(true);
    try {
      const response = await generateCsv({
        transaction_date: date.trim(),
        cr_dr_flag: transactionType,
        entity_individual_flag: accountType,
      });

      const contentType = response.headers['content-type'] || 'text/csv';
      console.log('CTR generation response:', response);
      const blob = new Blob([response.data], { type: contentType });
      console.log(`INSIDE HANDLE GENERATE AND THE BLOB IS LIKE ${blob}`)
      setCsvBlob(blob);
      setGeneratedDate(date.trim());
    } catch {
      setErrorMessage('CTR generation failed. Please try again later.');
    } finally {
      console.log(`the data inside the csv blob is ${csvBlob}`)
      setIsLoading(false);
    }
  };
  const handleDownload = () => {
    if (!zipBlob || !generatedDate) return;

    const url = URL.createObjectURL(zipBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `CTR_${generatedDate}.zip`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const handleUploadCsv = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
  
    // Check if the file is a spreadsheet or CSV
    if (!['application/vnd.ms-excel', 'text/csv'].includes(file.type)) {
      setErrorMessage('Uploaded file must be an Excel (.xls or .xlsx) or CSV file.');
      setIsCsvUploaded(false);
      localStorage.removeItem('csv'); // Remove existing CSV file if any
      return;
    }
  
    // Read the file as a base64 string
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target && e.target.result) {
        const csvContent = e.target.result.toString();
        localStorage.setItem('csv', csvContent);
        setIsCsvUploaded(true); // Set state to true when a valid CSV is uploaded
      }
    };
    reader.readAsDataURL(file);
  
    setErrorMessage(null);
  };
  

  const handleDownloadCsv = () => {
    if (!csvBlob || !generatedDate) return;

    const url = URL.createObjectURL(csvBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `CTR_${generatedDate}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="xml-generator-page container">
      <div className="row g-4">
        <div className="col-12 col-md-3">
          <div className="card border border-secondary shadow-sm xml-instructions-panel">
            <div className="card-body">
              <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2 text-primary">
                <FaInfoCircle />
                Instructions
              </h2>
              <ol className="mb-0">
                <li>Choose a valid report date.</li>
                <li>Select the transaction and account types.</li>
                <li>Click <strong className="text-primary">Generate CTR</strong>.</li>
                <li>Download the generated ZIP file.</li>
              </ol>
            </div>
          </div>
        </div>

        <div className="col-12 col-md-9">
          <div className="card border border-secondary shadow-sm">
            <div className="card-body p-4">
              <div className="d-flex align-items-center gap-3 mb-2">
                <div className="bg-primary d-flex align-items-center justify-content-center rounded-circle text-white" style={{ width: '42px', height: '42px', flexShrink: 0 }}>
                  <FaFileArchive size={20} />
                </div>
                <h1 className="h3 fw-bold mb-0">CTR Generator</h1>
              </div>
              <p className="text-muted mb-4 small">
                Generate a CTR ZIP file for the selected date, transaction type, and account type.
              </p>

              {errorMessage && (
                <div className="alert alert-danger" role="alert">
                  {errorMessage}
                </div>
              )}

              <div className="mb-3">
                <label htmlFor="ctrDate" className="form-label fw-medium">
                  Date <span className="text-danger">*</span>
                </label>
                <input
                  id="ctrDate"
                  type="date"
                  className="form-control bg-light"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>

              <div className="mb-3">
                <label htmlFor="transactionType" className="form-label fw-medium">
                  Transaction Type <span className="text-danger">*</span>
                </label>
                <select
                  id="transactionType"
                  className="form-select bg-light"
                  value={transactionType}
                  onChange={(e) => setTransactionType(e.target.value as 'DR' | 'CR')}
                >
                  <option value="DR">Withdrawl</option>
                  <option value="CR">Deposit</option>
                </select>
              </div>

              <div className="mb-4">
                <label htmlFor="accountType" className="form-label fw-medium">
                  Account Type <span className="text-danger">*</span>
                </label>
                <select
                  id="accountType"
                  className="form-select bg-light"
                  value={accountType}
                  onChange={(e) => setAccountType(e.target.value as 'ENTITY' | 'INDIVIDUAL')}
                >
                  <option value="ENTITY">Entity</option>
                  <option value="INDIVIDUAL">Individual</option>
                </select>
              </div>

              <div style = {{display: "flex", flexDirection : "row",  justifyContent : "space-between"}}>
              <input type="file" onChange={handleUploadCsv}/>
  

{/*                     
{ 
                <button
                  type="button"
                  style={{ width: "auto", flexShrink: 0 }}
                  className="btn btn-primary btn-sm xml-generate-btn"
                  onClick={handleUploadCsv} 
                  disabled={isLoading || !date.trim()}
                >
                  {isLoading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                      Uploading...
                    </>
                  ) : (
                    <span className="xml-generate-btn-text">Upload CSV</span>
                  )}
                </button> } */}

              
                <button
  type="button"
  className="btn btn-primary btn-sm"
  style={{ width: "auto", flexShrink: 0 }}
  onClick={(isCsvUploaded ? handleGenerate : handleGenerateCsv) as React.MouseEventHandler<HTMLButtonElement>}
  disabled = {(!(date === '') && isCsvUploaded) || (date === '' && !isCsvUploaded)}
>
  {isLoading ? (
    <>
      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
      Generating...
    </>
  ) : isCsvUploaded ? (
    <span className="xml-generate-btn-text">Generate CTR</span>
  ) : (
    <span className="xml-generate-btn-text">Generate CSV</span>
  )}
</button>
  
              </div>
             
              
              
              {csvBlob && generatedDate && (
                <>
                  <hr className="my-4" />
                  <div className="text-center xml-result-section">
                    <div className="d-flex align-items-center justify-content-center gap-2 mb-3">
                      <FaFileArchive className="text-primary" />
                      <span className="fw-semibold">
                        CTR ZIP Created For Date: <span className="text-primary">{generatedDate}</span>
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary xml-download-btn d-inline-flex align-items-center gap-2"
                      onClick={handleDownloadCsv}
                    >
                      <FaDownload />
                      <span>Download CSV File</span>
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

export default CtrGenerator;