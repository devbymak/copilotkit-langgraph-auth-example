
import { type InputProps } from '@copilotkit/react-ui';
import {
    useState,
    useEffect,
    useRef,
    type KeyboardEvent,
} from 'react';

export type FileUpload = {
    fileId: string;
    name: string;
    pageCount?: number;
    sheetCount?: number;
    totalRows?: number;
    extractedText: string;
    fileType: 'pdf' | 'excel';
};

type CopilotInputWithCallbackProps = InputProps & {
    uploadedFiles?: FileUpload[];
    fetchUploadedFiles?: () => Promise<void>;
    threadId?: string;
};

export const CopilotInput = ({ onSend, inProgress, uploadedFiles = [], fetchUploadedFiles, threadId }: CopilotInputWithCallbackProps) => {
    const [text, setText] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            const scrollHeight = textarea.scrollHeight;
            textarea.style.height = `${scrollHeight}px`;
        }
    }, [text]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        // Filter supported files (PDF and Excel)
        const supportedFiles = Array.from(files).filter(file => 
            file.type === 'application/pdf' || 
            file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
            file.type === 'application/vnd.ms-excel'
        );
        
        if (supportedFiles.length === 0) {
            alert('Please upload PDF or Excel files only');
            return;
        }

        if (supportedFiles.length !== files.length) {
            alert(`Only PDF and Excel files will be uploaded. ${files.length - supportedFiles.length} unsupported file(s) skipped.`);
        }

        setIsUploading(true);
        const newFiles: FileUpload[] = [];

        try {
            // Upload all files sequentially
            for (const file of supportedFiles) {
                const base64Content = await fileToBase64(file);
                const isPDF = file.type === 'application/pdf';
                const endpoint = isPDF ? '/process-pdf' : '/process-excel';

                const response = await fetch(`http://localhost:8000${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: file.name,
                        content: base64Content,
                        thread_id: threadId,
                    }),
                });

                if (!response.ok) {
                    throw new Error(`Failed to upload ${file.name}`);
                }

                const data = await response.json();
                newFiles.push({
                    fileId: data.file_id,
                    name: data.filename,
                    pageCount: data.page_count,
                    sheetCount: data.sheet_count,
                    totalRows: data.total_rows,
                    extractedText: data.extracted_text,
                    fileType: data.file_type,
                });
            }
            
            if (fetchUploadedFiles) {
                await fetchUploadedFiles();
            }
        } catch (error) {
            console.error('Error uploading files:', error);
            alert('Failed to upload one or more files. Please try again.');
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const fileToBase64 = (file: File): Promise<string> => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64String = reader.result as string;
                const base64Data = base64String.split(',')[1];
                resolve(base64Data);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    };

    const handleRemoveFile = async (fileId: string) => {
        if (!threadId) return;
        try {
            const response = await fetch(`http://localhost:8000/file/${threadId}/${fileId}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                if (fetchUploadedFiles) {
                    await fetchUploadedFiles();
                }
            } else {
                console.error('Failed to delete file');
                alert('Failed to remove the file. Please try again.');
            }
        } catch (error) {
            console.error('Error deleting file:', error);
            alert('An error occurred while removing the file.');
        }
    };

    const handleSend = async () => {
        if (!text.trim()) return;

        onSend(text);
        setText('');
        // Don't clear uploadedFiles - keep them for future messages
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleContainerClick = () => {
        textareaRef.current?.focus();
    };

    return (
        <div className="copilotKitInputContainer">
            {isUploading && (
                <div className="px-3 py-2 bg-gray-100 rounded-lg mb-2 flex items-center gap-2">
                    <span className="text-sm text-gray-700">Uploading file(s)...</span>
                </div>
            )}
            {uploadedFiles.length > 0 && (
                <div className="flex flex-col gap-2 mb-2">
                    {uploadedFiles.map((file) => (
                        <div 
                            key={file.fileId}
                            className="px-3 py-2 bg-gray-100 rounded-lg flex items-center justify-between"
                        >
                            <div className="flex items-center gap-2">
                                {file.fileType === 'pdf' ? (
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        strokeWidth="1.5"
                                        stroke="currentColor"
                                        className="w-5 h-5 text-red-500"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                                        />
                                    </svg>
                                ) : (
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        strokeWidth="1.5"
                                        stroke="currentColor"
                                        className="w-5 h-5 text-green-600"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 1.5v-1.5m0 0c0-.621.504-1.125 1.125-1.125m0 0h7.5"
                                        />
                                    </svg>
                                )}
                                <div>
                                    <div className="text-sm text-gray-700 font-medium">{file.name}</div>
                                    <div className="text-xs text-gray-500">
                                        {file.fileType === 'pdf' 
                                            ? `${file.pageCount} pages · PDF` 
                                            : `${file.sheetCount} sheets, ${file.totalRows} rows · Excel`
                                        } · In context
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => handleRemoveFile(file.fileId)}
                                className="bg-transparent border-none cursor-pointer p-1 flex items-center hover:bg-gray-200 rounded transition-colors"
                                aria-label={`Remove ${file.name}`}
                                tabIndex={0}
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth="1.5"
                                    stroke="currentColor"
                                    className="w-5 h-5 text-gray-500"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>
            )}
            <div className="copilotKitInput" onClick={handleContainerClick}>
                <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={uploadedFiles.length > 0 ? `Ask questions about ${uploadedFiles.length} uploaded file${uploadedFiles.length > 1 ? 's' : ''}...` : "Create survey questions or upload files (PDF/Excel)..."}
                    className="overflow-auto resize-none"
                    rows={1}
                    disabled={inProgress}
                />
                <div className="copilotKitInputControls">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/pdf,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                        onChange={handleFileUpload}
                        className="hidden"
                        disabled={inProgress}
                        multiple
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={inProgress || isUploading}
                        className="copilotKitInputControlButton mr-2"
                        aria-label="Upload Files"
                        title="Upload files: PDF, Excel (multiple files supported)"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth="1.5"
                            stroke="currentColor"
                            width="24"
                            height="24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"
                            />
                        </svg>
                    </button>
                    <div className="grow"></div>
                    <button
                        onClick={handleSend}
                        disabled={inProgress || !text.trim()}
                        data-copilotkit-in-progress={inProgress}
                        className="copilotKitInputControlButton"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth="1.5"
                            stroke="currentColor"
                            width="24"
                            height="24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M12 19V5m0 0l-7 7m7-7l7 7"
                            ></path>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
};
