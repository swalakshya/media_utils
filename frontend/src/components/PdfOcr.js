import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import './PdfOcr.css';

// Helper function to format seconds into readable time
const formatTime = (seconds) => {
    if (!seconds || seconds < 0) return '--';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
};

// Helper function to format completion time
const formatCompletionTime = (isoString) => {
    if (!isoString) return '--';

    try {
        const date = new Date(isoString);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    } catch {
        return '--';
    }
};

const PdfOcr = () => {
    const [file, setFile] = useState(null);
    const [language, setLanguage] = useState('hin');
    const [startPage, setStartPage] = useState('');
    const [endPage, setEndPage] = useState('');
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    // Progress tracking
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(null);
    const [warnings, setWarnings] = useState([]);
    const [jobId, setJobId] = useState(null);
    const [cancelling, setCancelling] = useState(false);
    const eventSourceRef = useRef(null);

    const languages = [
        { code: 'hin', name: 'Hindi' },
        { code: 'guj', name: 'Gujarati' },
        { code: 'eng', name: 'English' },
        { code: 'mar', name: 'Marathi' },
        { code: 'tam', name: 'Tamil' },
        { code: 'tel', name: 'Telugu' },
    ];

    // Clean up event source on unmount
    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
        };
    }, []);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (selectedFile.type === 'application/pdf') {
                setFile(selectedFile);
                setError(null);
                setSuccess(false);
                setProgress(null);
                setWarnings([]);
            } else {
                setError('Please select a PDF file');
                setFile(null);
            }
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!file) {
            setError('Please select a PDF file');
            return;
        }

        // Validate page range if provided
        if (startPage && endPage) {
            const start = parseInt(startPage);
            const end = parseInt(endPage);
            if (start > end) {
                setError('Start page must be less than or equal to end page');
                return;
            }
            if (start < 1 || end < 1) {
                setError('Page numbers must be greater than 0');
                return;
            }
        }

        setProcessing(true);
        setUploading(true);
        setError(null);
        setSuccess(false);
        setProgress(null);
        setWarnings([]);
        setUploadProgress(0);

        try {
            const startPageNum = startPage ? parseInt(startPage) : null;
            const endPageNum = endPage ? parseInt(endPage) : null;

            // Start async processing with upload progress tracking
            const currentJobId = await api.ocrPdfAsync(file, language, startPageNum, endPageNum, (percent) => {
                setUploadProgress(percent);
            });

            // Store job ID for cancellation
            setJobId(currentJobId);

            setUploading(false);
            setUploadProgress(100);

            // Connect to SSE stream for progress updates
            eventSourceRef.current = api.streamOcrProgress(
                currentJobId,
                // onProgress
                (data) => {
                    if (data.type === 'progress') {
                        setProgress(data);
                    } else if (data.type === 'warning') {
                        setWarnings(prev => [...prev, data.message]);
                    }
                },
                // onComplete
                async (data) => {
                    setProgress({
                        type: 'progress',
                        step_number: 7,
                        total_steps: 7,
                        step_name: 'Complete',
                        percentage: 100,
                        message: 'Processing complete! Downloading...'
                    });

                    // Download the file
                    try {
                        const blob = await api.downloadPdf(currentJobId);
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = file.name.replace('.pdf', '_searchable.pdf');
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);

                        setSuccess(true);
                        setProcessing(false);
                        setFile(null);
                        setProgress(null);
                        // Reset form
                        document.getElementById('pdf-file-input').value = '';
                    } catch (err) {
                        setError('Failed to download processed PDF');
                        setProcessing(false);
                    }
                },
                // onError
                (err) => {
                    setError(err.message || 'Processing failed. Please try again.');
                    setProcessing(false);
                    setProgress(null);
                    setCancelling(false);
                }
            );

        } catch (err) {
            setError(err.message || 'Failed to start processing. Please try again.');
            setProcessing(false);
            setProgress(null);
        }
    };

    const handleCancel = async () => {
        if (!jobId || cancelling) return;

        setCancelling(true);
        try {
            await api.cancelOcrJob(jobId);
            // SSE will handle the cancelled event
        } catch (err) {
            setError(`Failed to cancel job: ${err.message}`);
            setCancelling(false);
        }
    };

    const handleReset = () => {
        // Close event source if open
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }

        setFile(null);
        setLanguage('hin');
        setStartPage('');
        setEndPage('');
        setError(null);
        setSuccess(false);
        setProcessing(false);
        setUploading(false);
        setUploadProgress(0);
        setProgress(null);
        setWarnings([]);
        setJobId(null);
        setCancelling(false);
        document.getElementById('pdf-file-input').value = '';
    };

    return (
        <div className="pdf-ocr-container">
            <div className="pdf-ocr-card">
                <h2>PDF OCR - Make PDFs Searchable</h2>
                <p className="description">
                    Upload a scanned PDF to convert it into a searchable PDF using OCR (Optical Character Recognition).
                </p>

                <form onSubmit={handleSubmit} className="pdf-ocr-form">
                    {/* File Upload */}
                    <div className="form-group">
                        <label htmlFor="pdf-file-input">Select PDF File *</label>
                        <input
                            id="pdf-file-input"
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            disabled={processing}
                        />
                        {file && (
                            <div className="file-info">
                                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </div>
                        )}
                    </div>

                    {/* Language Selection */}
                    <div className="form-group">
                        <label htmlFor="language-select">OCR Language *</label>
                        <select
                            id="language-select"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            disabled={processing}
                        >
                            {languages.map((lang) => (
                                <option key={lang.code} value={lang.code}>
                                    {lang.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Page Range (Optional) */}
                    <div className="form-group">
                        <label>Page Range (Optional)</label>
                        <div className="page-range-inputs">
                            <input
                                type="number"
                                placeholder="Start page"
                                value={startPage}
                                onChange={(e) => setStartPage(e.target.value)}
                                disabled={processing}
                                min="1"
                            />
                            <span>to</span>
                            <input
                                type="number"
                                placeholder="End page"
                                value={endPage}
                                onChange={(e) => setEndPage(e.target.value)}
                                disabled={processing}
                                min="1"
                            />
                        </div>
                        <small>Leave empty to process entire PDF</small>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="message error-message">
                            ✗ {error}
                        </div>
                    )}

                    {/* Success Message */}
                    {success && (
                        <div className="message success-message">
                            ✓ PDF processed successfully! Your download should start automatically.
                        </div>
                    )}

                    {/* Upload Progress Display */}
                    {uploading && (
                        <div className="progress-container">
                            <div className="progress-header">
                                <span className="progress-step">
                                    Step 1: Uploading to Server
                                </span>
                                <span className="progress-percentage">
                                    {uploadProgress}%
                                </span>
                            </div>

                            <div className="progress-bar-container">
                                <div
                                    className="progress-bar-fill"
                                    style={{ width: `${uploadProgress}%` }}
                                ></div>
                            </div>

                            <div className="progress-message">
                                Uploading PDF to server... ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </div>
                        </div>
                    )}

                    {/* Processing Progress Display */}
                    {processing && !uploading && progress && (
                        <div className="progress-container">
                            <div className="progress-header">
                                <span className="progress-step">
                                    Step {(progress.step_number || 0) + 1} of 8: {progress.step_name || 'Processing'}
                                </span>
                                <span className="progress-percentage">
                                    {progress.percentage || 0}%
                                </span>
                            </div>

                            <div className="progress-bar-container">
                                <div
                                    className="progress-bar-fill"
                                    style={{ width: `${progress.percentage || 0}%` }}
                                ></div>
                            </div>

                            {/* Progress details with ETA */}
                            {progress.current && progress.total && (
                                <div className="progress-details">
                                    <div className="progress-info-row">
                                        <span className="progress-label">Pages:</span>
                                        <span className="progress-value">
                                            {progress.current} of {progress.total}
                                        </span>
                                    </div>

                                    {progress.elapsed_seconds !== undefined && (
                                        <div className="progress-info-row">
                                            <span className="progress-label">Elapsed:</span>
                                            <span className="progress-value">
                                                {formatTime(progress.elapsed_seconds)}
                                            </span>
                                        </div>
                                    )}

                                    {progress.eta_seconds !== undefined && progress.eta_seconds !== null && (
                                        <div className="progress-info-row">
                                            <span className="progress-label">Time Remaining:</span>
                                            <span className="progress-value progress-eta">
                                                {formatTime(progress.eta_seconds)}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Warnings */}
                            {warnings.length > 0 && (
                                <details className="warnings-section">
                                    <summary>⚠ Warnings ({warnings.length})</summary>
                                    <ul className="warnings-list">
                                        {warnings.map((warning, idx) => (
                                            <li key={idx}>{warning}</li>
                                        ))}
                                    </ul>
                                </details>
                            )}
                        </div>
                    )}

                    {/* Buttons */}
                    <div className="button-group">
                        {processing && jobId ? (
                            <button
                                type="button"
                                className="btn btn-danger"
                                onClick={handleCancel}
                                disabled={cancelling}
                            >
                                {cancelling ? 'Cancelling...' : 'Cancel'}
                            </button>
                        ) : (
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={processing || !file}
                            >
                                {processing ? 'Processing...' : 'Process PDF'}
                            </button>
                        )}
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleReset}
                            disabled={processing}
                        >
                            Reset
                        </button>
                    </div>

                    {processing && !progress && !uploading && (
                        <div className="processing-info">
                            <div className="spinner"></div>
                            <p>Waiting for server response...</p>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
};

export default PdfOcr;