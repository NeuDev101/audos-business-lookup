import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileDropzone } from '../components/FileDropzone';
import { LanguageProvider } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

describe('FileDropzone', () => {
  it('renders file dropzone with helper text', () => {
    const onFileSelect = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} />
      </LanguageProvider>,
    );

    expect(screen.getByText(t('bulk.heroTitle', 'ja'))).toBeInTheDocument();
    expect(screen.getByText(t('bulk.helperText', 'ja'))).toBeInTheDocument();
  });

  it('calls onFileSelect when valid CSV file is selected', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    const file = new File(['business_id\n1234567890123\n'], 'test.csv', {
      type: 'text/csv',
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(input);

    await waitFor(() => {
      expect(onFileSelect).toHaveBeenCalledWith(file);
    });
    // onError is called with empty string to clear any previous errors
    expect(onError).toHaveBeenCalledWith('');
  });

  it('calls onError and does not call onFileSelect when non-CSV file is selected', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    const file = new File(['content'], 'test.txt', {
      type: 'text/plain',
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(input);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(t('bulk.onlyCsv', 'ja'));
    });
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('calls onError and does not call onFileSelect when file exceeds 5MB', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    // Create a file larger than 5MB (5 * 1024 * 1024 + 1 bytes)
    const largeContent = new Array(5 * 1024 * 1024 + 1).fill('a').join('');
    const file = new File([largeContent], 'test.csv', {
      type: 'text/csv',
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(input);

    const expectedMessage = t('bulk.fileSizeExceeded', 'ja').replace('{limit}', '5');
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(expectedMessage);
    });
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('calls onError and does not call onFileSelect when file is dropped with wrong extension', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    const file = new File(['content'], 'test.pdf', {
      type: 'application/pdf',
    });

    const dropzone = screen.getByLabelText(t('bulk.aria.upload', 'ja'));
    
    const dataTransfer = {
      files: [file],
    };
    
    fireEvent.dragOver(dropzone);
    fireEvent.drop(dropzone, {
      dataTransfer: dataTransfer as any,
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(t('bulk.onlyCsv', 'ja'));
    });
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('calls onFileSelect when valid CSV file is dropped', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    const file = new File(['business_id\n1234567890123\n'], 'test.csv', {
      type: 'text/csv',
    });

    const dropzone = screen.getByLabelText(t('bulk.aria.upload', 'ja'));
    
    const dataTransfer = {
      files: [file],
    };
    
    fireEvent.dragOver(dropzone);
    fireEvent.drop(dropzone, {
      dataTransfer: dataTransfer as any,
    });

    await waitFor(() => {
      expect(onFileSelect).toHaveBeenCalledWith(file);
    });
    // onError is called with empty string to clear any previous errors
    expect(onError).toHaveBeenCalledWith('');
  });

  it('clears error when valid file is selected after invalid file', async () => {
    const onFileSelect = vi.fn();
    const onError = vi.fn();
    const { rerender } = render(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    // First, select invalid file
    const invalidFile = new File(['content'], 'test.txt', {
      type: 'text/plain',
    });
    
    Object.defineProperty(input, 'files', {
      value: [invalidFile],
      writable: false,
      configurable: true,
    });

    fireEvent.change(input);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(t('bulk.onlyCsv', 'ja'));
    });

    // Reset mocks and rerender to get a fresh input
    onFileSelect.mockClear();
    onError.mockClear();
    rerender(
      <LanguageProvider>
        <FileDropzone onFileSelect={onFileSelect} onError={onError} />
      </LanguageProvider>,
    );
    
    const newInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    // Then, select valid file
    const validFile = new File(['business_id\n1234567890123\n'], 'test.csv', {
      type: 'text/csv',
    });
    
    Object.defineProperty(newInput, 'files', {
      value: [validFile],
      writable: false,
      configurable: true,
    });

    fireEvent.change(newInput);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(''); // Error cleared
      expect(onFileSelect).toHaveBeenCalledWith(validFile);
    });
  });
});
