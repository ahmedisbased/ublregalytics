import { useState } from 'react';
import { FaDownload, FaFileArchive, FaInfoCircle } from 'react-icons/fa';
import { generateCsv , generateXml, uploadFileStream} from '../../services/ctrService';

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isFileUploaded, setisFileUploaded] = useState(false); // Track if a CSV file has been uploaded
  const validate = () => {
    if (date === '' && !isFileUploaded) {
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
 

  


  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {

      const file = event.target.files?.[0] || null;

      if (file) {
         // validate file type
         if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
          setSelectedFile(file);
          setisFileUploaded(true);
          setErrorMessage(null);
         } else {
          setErrorMessage('Please select a valid csv file');
          setSelectedFile(null);
          setisFileUploaded(false);
         }
      }
  };
  type AccountType = "ENTITY" | "INDIVIDUAL"
  type TransactionType = "CR" | "DR"

  const isAccountType = (value : string | undefined): value is AccountType => {
    return value ==='ENTITY' || value === "INDIVIDUAL"
  }
  
  const isTransactionType = (value : string | undefined): value is TransactionType => {
    return value ==='CR' || value === 'DR'
  }
  const handleGenerate = async () => {
    setErrorMessage(null);
    setZipBlob(null);
    setCsvBlob(null);
    setGeneratedDate(null);
    console.log("trying to generate with file upload")

    
    if (!validate()) return;



    setIsLoading(true);
    console.log("set loading to true")
    console.log(`the zip blob is ${zipBlob}`)
    console.log(`the CSV blob is ${csvBlob}`)
    
    try {
      // create formdata to send file and other data
      const formData = new FormData();
      let entity_individual_flag = selectedFile?.name.split("_")[1] 
      let cr_dr_flag = selectedFile?.name.split("_")[2]
      let transaction_date = selectedFile?.name.split("_")[3].split(".")[0]

      if (isAccountType(entity_individual_flag)){ 
      setAccountType(entity_individual_flag)
      }
      if (isTransactionType(cr_dr_flag)){ 
        setTransactionType(cr_dr_flag)
        }
      // setTransactionType(cr_dr_flag)
      console.log(`file is this inside handleGenerate ${selectedFile!.stream()}`)
      console.log(`file is this inside handleGenerate ${selectedFile!.name}`)
      console.log(`AFTER SPLITTING THE VALUES ARE ${cr_dr_flag}, ${entity_individual_flag}, ${transaction_date}`)
      
      formData.append('file', selectedFile!);
      formData.append('data', JSON.stringify({cr_dr_flag : cr_dr_flag,
        transaction_date : transaction_date ,
        entity_individual_flag : entity_individual_flag}))

      console.log(`Form data is ${formData}}`)
      console.log(`Form data is ${formData.get('file')}`)
      console.log(`THE TYPE OF THE FILE IS ${typeof(selectedFile)}`)
      
      
      // make the call
      // const response = await generateXml (formData);

      const response = await uploadFileStream( 
       formData
      );

      



      // handle response based on the backend

      const contentType = response.headers['content-type'] || 'application/octet-stream';
      console.log('CTR generation response:', response);
      let xml =response.data
      console.log(
        "xml is ", xml
      )

      const blob = new Blob([response.data], { type: contentType });
      console.log(`INSIDE HANDLE GENERATE AND THE BLOB IS LIKE ${blob}`)
      setZipBlob(blob);
      console.log(`INSIDE HANDLE GENERATE and date is ${transaction_date}`)
      console.log(`THE DATA INSIDE Handle generate in the  THE ZIPBLOB IS ${zipBlob}`)
      setGeneratedDate(transaction_date!);
    } catch (error){
      console.error(`Generation error`, error)
      setErrorMessage('CTR generation failed. Please try again later.');
    } finally {
      setIsLoading(false);
      console.log(`the data inside the csv blob is ${zipBlob}`)

      
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
    console.log("INSIDE HANDLE DOWNLOAD ")
    if (!zipBlob) {
      console.log(` I CANNOT FIND THE ZIP BLOB`)
      console.log(`the zipblob is ${zipBlob}`) 
      return;
    }
    console.log(` zipblob data is ${zipBlob.text}`)
    console.log(`Transaction Type is ${transactionType}`)
    console.log(`CTR_${accountType}_${transactionType}_${generatedDate}.xml`)
    const url = URL.createObjectURL(zipBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `CTR_${accountType}_${transactionType}_${generatedDate}.zip`;
    anchor.click();
    URL.revokeObjectURL(url);

  };
  const handleUploadCsv = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;

    if (file) {
      console.log(`FILE UPLOADED AND FILE IS ${file}`)
      console.log(`FILE UPLOADED AND FILE NAME IS ${file?.name}`)
      console.log(`FILE UPLOADED AND FILE type IS ${file?.type}`)
      console.log(`FILE UPLOADED AND FILE size IS ${Math.ceil(file?.size/1024 / 1024)}MB `)

   
      if (file.type === 'text/csv' || file.name.endsWith('.csv')){
        setSelectedFile(file)
        setisFileUploaded(true)
      console.log(`Set is file uploaded to true`)

        setErrorMessage('')
      }
      else {
        setErrorMessage('Please select a valid csv file')
        setisFileUploaded(false)
        setSelectedFile(null)
      }
    }

    }

    

  const handleDownloadCsv = () => {
    if (!csvBlob || !generatedDate) return;

    const url = URL.createObjectURL(csvBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `CTR_${accountType}_${transactionType}_${generatedDate}.csv`;
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
  onClick={(isFileUploaded ? handleGenerate : handleGenerateCsv) as React.MouseEventHandler<HTMLButtonElement>}
  disabled = {(!(date === '') && isFileUploaded) || (date === '' && !isFileUploaded)}
>
  {isLoading ? (
    <>
      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
      Generating...
    </>
  ) : isFileUploaded ? (
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
                        CTR CSV Created For Date: <span className="text-primary">{generatedDate}</span>
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
              )
              }

{zipBlob && (
                <>
                  <hr className="my-4" />
                  <div className="text-center xml-result-section">
                    <div className="d-flex align-items-center justify-content-center gap-2 mb-3">
                      <FaFileArchive className="text-primary" />
                      <span className="fw-semibold">
                        CTR XML Created For Date: <span className="text-primary">{generatedDate}</span>
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary xml-download-btn d-inline-flex align-items-center gap-2"
                      onClick={handleDownload}
                    >
                      <FaDownload />
                      <span>Download XML</span>
                    </button>
                  </div>
                </>
              )
              }
            </div>
            
          </div>
        </div>
      </div>  
    </div>
  );
};

export default CtrGenerator;