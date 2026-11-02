/**
 * Renders the COMPLETE, verbatim content of an ADS exp-template sheet.
 *
 * The template's `content` field is a JSON string produced by the ADS seeder:
 *   { source_form, document_no, header_category, sections_index[], blocks[] }
 * where `blocks` is the document in order — each block is either
 *   { type: 'para', text }  or  { type: 'table', grid: string[][] }.
 *
 * Nothing is standardised or summarised here: every paragraph and every table
 * cell from the original sheet is shown as-is. Cell text keeps the source line
 * breaks (the extractor joined wrapped lines with " / ").
 */
import { Tag } from 'primereact/tag';

interface Block {
  type: 'para' | 'table';
  text?: string;
  grid?: string[][];
}

interface SheetContent {
  source_form?: string;
  document_no?: string;
  header_category?: string;
  sections_index?: { num: number; title: string }[];
  blocks?: Block[];
}

const renderCell = (cell: string) =>
  (cell ?? '').split(' / ').map((line, i) => (
    <div key={i} style={{ whiteSpace: 'pre-wrap' }}>
      {line}
    </div>
  ));

export const ADSSheetViewer = ({ content }: { content?: string | null }) => {
  if (!content) {
    return <p className="text-500 text-sm m-0">No stored content for this template.</p>;
  }

  let parsed: SheetContent;
  try {
    parsed = JSON.parse(content) as SheetContent;
  } catch {
    // Not JSON — show the raw content so nothing is hidden from the user.
    return (
      <pre className="text-sm" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {content}
      </pre>
    );
  }

  const blocks = parsed.blocks ?? [];

  return (
    <div className="flex flex-column gap-3">
      <div className="flex flex-wrap align-items-center gap-2">
        {parsed.source_form && <Tag value={parsed.source_form} severity="info" />}
        {parsed.document_no && <Tag value={parsed.document_no} />}
        {parsed.header_category && <Tag value={parsed.header_category} severity="success" />}
      </div>

      {parsed.sections_index && parsed.sections_index.length > 0 && (
        <div className="bg-blue-50 border-round p-2">
          <div className="text-xs font-semibold text-700 mb-1">Sections in this sheet</div>
          <div className="flex flex-column gap-1">
            {parsed.sections_index.map((s) => (
              <div key={`${s.num}-${s.title}`} className="text-sm">
                <span className="font-medium">{String(s.num).padStart(2, '0')}.</span> {s.title}
              </div>
            ))}
          </div>
        </div>
      )}

      {blocks.map((b, i) =>
        b.type === 'para' ? (
          <p key={i} className="text-sm m-0" style={{ whiteSpace: 'pre-wrap' }}>
            {b.text}
          </p>
        ) : (
          <div key={i} className="overflow-x-auto">
            <table
              className="w-full text-sm"
              style={{ borderCollapse: 'collapse', tableLayout: 'fixed' }}
            >
              <tbody>
                {(b.grid ?? []).map((row, r) => (
                  <tr key={r}>
                    {row.map((cell, c) => (
                      <td
                        key={c}
                        className="border-1 border-300 p-2 align-top"
                        style={{ verticalAlign: 'top', wordBreak: 'break-word' }}
                      >
                        {renderCell(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      )}
    </div>
  );
};
