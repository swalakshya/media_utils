// --- API SERVICE ---
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';
const SSE_BASE_URL = process.env.REACT_APP_SSE_BASE_URL || 'http://localhost:8000/api';

// Debug logging (only in development)
const DEBUG = process.env.NODE_ENV === 'development';
const log = DEBUG ? console.log : () => {};
const logError = console.error;  // Always log errors

export const api = {
    /**
     * OCR a PDF file to make it searchable (synchronous - no progress updates)
     * @param {File} file - PDF file to process
     * @param {string} language - OCR language code (hin, guj, eng, etc.)
     * @param {number|null} startPage - Starting page number (1-indexed, optional)
     * @param {number|null} endPage - Ending page number (1-indexed, optional)
     * @returns {Promise<Blob>} - Searchable PDF file
     */
    ocrPdf: async (file, language = 'hin', startPage = null, endPage = null) => {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('language', language);
            if (startPage !== null) formData.append('start_page', startPage);
            if (endPage !== null) formData.append('end_page', endPage);

            const response = await fetch(`${API_BASE_URL}/pdf/ocr`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            // Return the blob for download
            const blob = await response.blob();
            return blob;
        } catch (error) {
            logError("API Error: Could not process PDF OCR", error);
            throw error;
        }
    },

    /**
     * Start async PDF OCR processing with progress tracking
     * @param {File} file - PDF file to process
     * @param {string} language - OCR language code (hin, guj, eng, etc.)
     * @param {number|null} startPage - Starting page number (1-indexed, optional)
     * @param {number|null} endPage - Ending page number (1-indexed, optional)
     * @param {Function} onUploadProgress - Callback for upload progress (0-100)
     * @returns {Promise<string>} - Job ID for tracking progress
     */
    ocrPdfAsync: async (file, language = 'hin', startPage = null, endPage = null, onUploadProgress = null) => {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('language', language);
            if (startPage !== null) formData.append('start_page', startPage);
            if (endPage !== null) formData.append('end_page', endPage);

            const xhr = new XMLHttpRequest();

            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onUploadProgress) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    onUploadProgress(percentComplete);
                }
            });

            // Handle completion
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        resolve(data.job_id);
                    } catch (error) {
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    try {
                        const errorData = JSON.parse(xhr.responseText);
                        reject(new Error(errorData.detail || `HTTP error! status: ${xhr.status}`));
                    } catch {
                        reject(new Error(`HTTP error! status: ${xhr.status}`));
                    }
                }
            });

            // Handle errors
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                reject(new Error('Upload aborted'));
            });

            // Send request
            xhr.open('POST', `${API_BASE_URL}/pdf/ocr/async`);
            xhr.send(formData);
        });
    },

    /**
     * Connect to SSE stream for progress updates
     * @param {string} jobId - Job ID to monitor
     * @param {Function} onProgress - Callback for progress updates
     * @param {Function} onComplete - Callback when job completes
     * @param {Function} onError - Callback for errors
     * @returns {EventSource} - EventSource object for closing connection
     */
    streamOcrProgress: (jobId, onProgress, onComplete, onError) => {
        log(`[SSE] Opening connection to: ${SSE_BASE_URL}/pdf/ocr/stream/${jobId}`);
        const eventSource = new EventSource(`${SSE_BASE_URL}/pdf/ocr/stream/${jobId}`);

        eventSource.onopen = (event) => {
            log('[SSE] Connection opened:', event);
        };

        eventSource.onmessage = (event) => {
            log('[SSE] Raw message received:', event.data);
            try {
                const data = JSON.parse(event.data);
                log('[SSE] Parsed data:', data);

                switch (data.type) {
                    case 'connected':
                        log('[SSE] Connected to progress stream:', data.job_id);
                        break;
                    case 'progress':
                        log('[SSE] Progress event:', data);
                        if (onProgress) {
                            log('[SSE] Calling onProgress callback');
                            onProgress(data);
                        }
                        break;
                    case 'warning':
                    case 'info':
                        log('[SSE] Warning/Info event:', data);
                        if (onProgress) onProgress(data);
                        break;
                    case 'complete':
                        log('[SSE] Complete event:', data);
                        if (onComplete) onComplete(data);
                        eventSource.close();
                        break;
                    case 'cancelled':
                        log('[SSE] Cancelled event:', data);
                        if (onError) onError(new Error(data.message || 'Job cancelled'));
                        eventSource.close();
                        break;
                    case 'error':
                        logError('[SSE] Error event:', data);
                        if (onError) onError(new Error(data.message));
                        eventSource.close();
                        break;
                    default:
                        log('[SSE] Unknown event type:', data.type, data);
                }
            } catch (error) {
                logError('[SSE] Error parsing SSE data:', error, event.data);
            }
        };

        eventSource.onerror = (error) => {
            logError('[SSE] Connection error:', error);
            log('[SSE] EventSource readyState:', eventSource.readyState);
            if (eventSource.readyState === EventSource.CLOSED) {
                log('[SSE] Connection closed');
            }
            if (onError) onError(new Error('Connection to server lost'));
            eventSource.close();
        };

        return eventSource;
    },

    /**
     * Cancel a running OCR job
     * @param {string} jobId - Job ID to cancel
     * @returns {Promise<Object>} - Cancellation response
     */
    cancelOcrJob: async (jobId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/pdf/ocr/cancel/${jobId}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            logError("API Error: Could not cancel job", error);
            throw error;
        }
    },

    /**
     * Download processed PDF
     * @param {string} jobId - Job ID
     * @returns {Promise<Blob>} - PDF file blob
     */
    downloadPdf: async (jobId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/pdf/download/${jobId}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            return await response.blob();
        } catch (error) {
            logError("API Error: Could not download PDF", error);
            throw error;
        }
    },

    /**
     * Health check endpoint
     */
    healthCheck: async () => {
        try {
            const response = await fetch('/');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            logError("API Error: Health check failed", error);
            throw error;
        }
    }
};