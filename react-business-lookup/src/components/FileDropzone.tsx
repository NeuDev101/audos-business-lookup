import { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { PrimaryButton } from './PrimaryButton';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  onError?: (message: string) => void;
}

export function FileDropzone({ onFileSelect, onError }: FileDropzoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { language } = useLanguage();

  const validateFile = (file: File): string | null => {
    // Check file extension
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return t('bulk.onlyCsv', language);
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return t('bulk.fileSizeExceeded', language).replace(
        '{limit}',
        String(MAX_FILE_SIZE / (1024 * 1024)),
      );
    }

    return null;
  };

  const handleFile = (file: File) => {
    const error = validateFile(file);
    if (error) {
      if (onError) {
        onError(error);
      }
      return;
    }

    // Clear any previous errors
    if (onError) {
      onError('');
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="bg-(--color-bg-card) rounded-lg p-8 border border-(--color-border)">
      <h2 className="text-2xl font-semibold text-white mb-6">{t('bulk.heroTitle', language)}</h2>
      <p className="text-(--color-text-secondary) mb-6">
        {t('bulk.heroSubtitle', language)}
      </p>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          isDragging
            ? 'border-(--color-primary) bg-(--color-primary)/5'
            : 'border-(--color-border) bg-(--color-bg-dark)'
        }`}
        aria-label={t('bulk.aria.upload', language)}
      >
        <Upload className="mx-auto mb-4 text-(--color-text-muted)" size={48} />
        <p className="text-xl text-(--color-text-primary) mb-4">{t('bulk.dragDrop', language)}</p>
        
        <PrimaryButton onClick={handleBrowseClick} type="button">
          {t('bulk.browseFiles', language)}
        </PrimaryButton>

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      <p className="text-sm text-(--color-text-muted) mt-4">
        {t('bulk.helperText', language)}
      </p>
    </div>
  );
}
