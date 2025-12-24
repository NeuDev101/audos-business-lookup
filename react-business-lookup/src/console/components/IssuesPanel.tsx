import { PrimaryButton } from './PrimaryButton';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

interface IssuesPanelProps {
  issues: string[];
  isUploading?: boolean;
}

export function IssuesPanel({ issues, isUploading = false }: IssuesPanelProps) {
  const { language } = useLanguage();
  const hasIssues = issues.length > 0;

  return (
    <div className="bg-dark-panel rounded-lg p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">{t('console.detectedIssues', language)}</h3>
        {hasIssues ? (
          <ul className="space-y-3">
            {issues.map((issue, index) => (
              <li key={`${issue}-${index}`} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="w-2 h-2 rounded-full bg-error mt-1.5 flex-shrink-0" />
                <span>{issue}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">{t('console.noIssuesBatch', language)}</p>
        )}
      </div>

      <div>
        <h3 className="text-lg font-semibold text-white mb-4">{t('console.suggestedFixes', language)}</h3>
        {hasIssues ? (
          <ul className="space-y-3">
            {issues.map((issue, index) => (
              <li key={`fix-${issue}-${index}`} className="flex items-start gap-2 text-sm text-gray-400">
                <input type="radio" name="fix" className="mt-1 accent-gray-500" />
                <span>{t('console.reviewIssue', language)} {issue}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">{t('console.allSet', language)}</p>
        )}
      </div>

      <PrimaryButton className="w-full" disabled={!hasIssues || isUploading}>
        {hasIssues ? t('console.applyFixes', language) : t('console.waitingForIssues', language)}
      </PrimaryButton>
    </div>
  );
}
