/**
 * Derives a human-readable summary of a template definition.
 *
 * Kept out of the page component so it can be reused by the worksheet form's
 * header and, later, the COA. It reads a definition defensively: an author is
 * editing raw JSON, so it must tolerate a partially-written or malformed shape
 * without throwing and blanking the page.
 */
import type { TemplateDefinition } from './testTemplate.types';

export interface DefinitionSummary {
  contextCount: number;
  groupCount: number;
  inputCount: number;
  areaCount: number;
  calculatedCount: number;
  criteriaCount: number;
  blockingCriteriaCount: number;
  resultRef: string | null;
  /** `group.field` refs for every area field — what the Waters import will fill. */
  areaRefs: string[];
}

export function describeDefinition(
  definition: TemplateDefinition | null | undefined,
): DefinitionSummary {
  const groups = Array.isArray(definition?.groups) ? definition.groups : [];
  const criteria = Array.isArray(definition?.criteria) ? definition.criteria : [];
  const context = Array.isArray(definition?.context) ? definition.context : [];

  let inputCount = 0;
  let areaCount = 0;
  let calculatedCount = 0;
  const areaRefs: string[] = [];

  for (const group of groups) {
    for (const field of Array.isArray(group?.fields) ? group.fields : []) {
      if (field?.kind === 'input') inputCount += 1;
      else if (field?.kind === 'area') {
        areaCount += 1;
        areaRefs.push(`${group.key}.${field.key}`);
      } else if (field?.kind === 'calculated') calculatedCount += 1;
    }
  }

  return {
    contextCount: context.length,
    groupCount: groups.length,
    inputCount,
    areaCount,
    calculatedCount,
    criteriaCount: criteria.length,
    blockingCriteriaCount: criteria.filter((c) => (c?.severity ?? 'blocking') === 'blocking').length,
    resultRef: definition?.resultRef ?? null,
    areaRefs,
  };
}

/** Renders a criterion's limit for display when the template gives no `limitText`. */
export function formatLimit(operator: string, limit: number[]): string {
  const [low, high] = limit;
  switch (operator) {
    case 'lte':
      return `NMT ${low}`;
    case 'gte':
      return `NLT ${low}`;
    case 'between':
      return `${low} – ${high}`;
    case 'eq':
      return `= ${low}`;
    default:
      return limit.join(', ');
  }
}
