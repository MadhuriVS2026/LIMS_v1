/**
 * Worksheet indicator for a TRF test line.
 *
 * Exists because the worksheet was previously only reachable by clicking a row
 * expander with nothing to suggest there was anything behind it. A calculation
 * sheet is the substance of the test, not an optional extra, so the line has to
 * say whether one exists, whether it is finished, and whether one is available
 * but unused.
 */
import { Tag } from 'primereact/tag';
import type { Worksheet } from '../models/testTemplate.types';

interface WorksheetStatusCellProps {
  worksheet: Worksheet | undefined;
  /** How many Active templates exist for this line's Test. */
  availableTemplates: number;
}

export const WorksheetStatusCell = ({
  worksheet,
  availableTemplates,
}: WorksheetStatusCellProps) => {
  if (worksheet) {
    const confirmed = worksheet.status === 'Confirmed';
    return (
      <div className="flex flex-column gap-1" style={{ lineHeight: 1.3 }}>
        <Tag
          value={confirmed ? 'Calculated' : 'Worksheet open'}
          severity={confirmed ? 'success' : 'info'}
        />
        <span className="text-xs text-500 font-mono">
          {worksheet.template_code} v{worksheet.template_version}
        </span>
      </div>
    );
  }

  if (availableTemplates > 0) {
    return (
      <Tag
        value={
          availableTemplates === 1
            ? 'Template available'
            : `${availableTemplates} templates available`
        }
        severity="warning"
      />
    );
  }

  //  No template for this Test — the line uses the free-text result path, which
  //  is a legitimate outcome rather than something missing.
  return <span className="text-xs text-500">Free text</span>;
};
