import { useCallback } from 'react';
import type { DragEvent } from 'react';
import { Upload } from 'lucide-react';
import { PrimaryButton } from './PrimaryButton';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  isUploading?: boolean;
}

export function FileDropzone({ onFilesSelected, isUploading = false }: FileDropzoneProps) {
  const { language } = useLanguage();

  const emitFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || isUploading) {
        return;
      }
      onFilesSelected(Array.from(fileList));
    },
    [onFilesSelected, isUploading],
  );

  const handleFileSelect = useCallback(() => {
    if (isUploading) {
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.pdf,.jpg,.jpeg,.png';
    input.onchange = (event) => {
      emitFiles((event.target as HTMLInputElement).files);
    };
    input.click();
  }, [emitFiles, isUploading]);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      emitFiles(event.dataTransfer.files);
    },
    [emitFiles],
  );

  return (
    <div
      className={`border-2 border-dashed border-primary rounded-lg p-12 flex flex-col items-center justify-center gap-4 bg-dark-panel/50 transition-opacity ${isUploading ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer'}`}
      aria-label={t('console.uploadArea', language)}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleFileSelect();
        }
      }}
    >
      <Upload size={48} className="text-primary" />
      <h3 className="text-2xl font-semibold text-white">{t('console.dragDropInvoices', language)}</h3>
      <PrimaryButton onClick={handleFileSelect} disabled={isUploading}>
        {isUploading ? t('console.uploading', language) : t('bulk.browseFiles', language)}
      </PrimaryButton>
      <p className="text-sm text-gray-400 text-center">
        {t('console.acceptedFormats', language)}
        <br />
        {t('console.maxFiles', language)}
      </p>
    </div>
  );
}
