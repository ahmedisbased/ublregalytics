import { useRef, useState, type ChangeEvent } from 'react';
import { IoClose } from 'react-icons/io5';
import { uploadImagesForExcel } from '../../services/imageService';
import './upload-image-modal.scss';

interface UploadImageModalProps {
    onClose: () => void;
}

const DEFAULT_FILENAME = 'processed-images.xlsx';

const getFileNameFromHeaders = (headers: Record<string, string | undefined>) => {
    const rawDisposition = headers['content-disposition'] ?? '';
    const match = rawDisposition.match(/filename\*?=(?:UTF-8''|")?([^;"\n]+)"?/i);
    if (match?.[1]) {
        try {
            return decodeURIComponent(match[1]);
        } catch {
            return match[1];
        }
    }
    return DEFAULT_FILENAME;
};

const UploadImageModal = ({ onClose }: UploadImageModalProps) => {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);

    const clearFileInput = () => {
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleFileSelection = async (event: ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files ?? []);
        clearFileInput();

        if (!files.length) {
            return;
        }

        const acceptedFiles = files.filter((file) => file.type.startsWith('image/'));
        const rejectedFiles = files.filter((file) => !file.type.startsWith('image/'));

        if (rejectedFiles.length) {
            setErrorMessage(`Unsupported files skipped: ${rejectedFiles.map((file) => file.name).join(', ')}`);
        } else {
            setErrorMessage(null);
        }

        if (!acceptedFiles.length) {
            setSelectedFiles([]);
            setStatusMessage(null);
            setErrorMessage('Please select valid image files.');
            return;
        }

        setSelectedFiles(acceptedFiles);
        setStatusMessage('Uploading images and generating Excel file...');
        setIsUploading(true);

        const formData = new FormData();
        acceptedFiles.forEach((file) => formData.append('files', file));

        try {
            const response = await uploadImagesForExcel(formData);
            const fileName = getFileNameFromHeaders(
                (response.headers ?? {}) as Record<string, string | undefined>
            );
            const blob = response.data as Blob;
            const downloadUrl = window.URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(downloadUrl);

            setStatusMessage('Your Excel file is ready and has started downloading.');
        } catch (error) {
            console.error('Failed to upload images', error);
            setStatusMessage(null);
            setErrorMessage('Failed to generate Excel file. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    const openFileDialog = () => {
        if (!isUploading) {
            fileInputRef.current?.click();
        }
    };

    return (
        <div className="upload-image-modal-backdrop" role="presentation">
            <div className="upload-image-modal" role="dialog" aria-modal="true" aria-label="Upload images">
                <button type="button" className="upload-image-modal__close" onClick={onClose} aria-label="Close">
                    <IoClose size={20} />
                </button>
                <div className="upload-image-modal__content">
                    <h2>Upload Images</h2>
                    <p>Select one or more images. We will generate an Excel file and download it for you.</p>
                </div>

                <div className="upload-image-modal__body">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        className="upload-image-modal__input"
                        onChange={handleFileSelection}
                        disabled={isUploading}
                    />
                    <button
                        type="button"
                        className="upload-image-modal__button"
                        onClick={openFileDialog}
                        disabled={isUploading}
                    >
                        {isUploading ? 'Processing...' : 'Choose Images'}
                    </button>

                    {selectedFiles.length > 0 && (
                        <div className="upload-image-modal__file-list">
                            {selectedFiles.map((file, index) => (
                                <span key={`${file.name}-${index}`}>{file.name}</span>
                            ))}
                        </div>
                    )}

                    {statusMessage && <div className="upload-image-modal__status">{statusMessage}</div>}
                    {errorMessage && <div className="upload-image-modal__error">{errorMessage}</div>}
                </div>
            </div>
        </div>
    );
};

export default UploadImageModal;
