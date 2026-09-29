/**
 * The 14 calculation archetypes the 35 R&D workbooks reduce to.
 *
 * This list is presentation metadata only — the backend accepts any archetype
 * string and uses it solely to scope the generated template code
 * (`TPL-<ARCHETYPE>-XXXX`). Keeping it here rather than as a backend enum means
 * a new archetype can be piloted without a deployment; the engine does not care.
 *
 * Every archetype here is now seeded and selectable; nothing is deferred. A7 and
 * A12 were the last two, held back on the belief that f1/f2 was absent from its
 * source sheet and that the roll-ups normalised twice. Both turned out to be
 * readable from the workbooks: A7's arithmetic is off to the right of the printed
 * area, and A12's "double normalisation" was a two-cell reference slip.
 *
 * Labels here must match the archetype table in design.md — this list is what an
 * author picks from, so a wrong label sends a template to the wrong family and
 * the mistake is only visible once someone opens the workbook it was meant for.
 */
export interface Archetype {
  code: string;
  label: string;
  deferred?: boolean;
}

export const ARCHETYPES: Archetype[] = [
  { code: 'A1', label: 'Assay / potency vs external standard' },
  { code: 'A2', label: 'Multi-analyte content' },
  { code: 'A3', label: 'Saturation solubility' },
  { code: 'A4', label: 'Related substances vs standard' },
  { code: 'A5', label: 'Related substances by area normalisation' },
  { code: 'A6a', label: 'Dissolution — without replacement' },
  { code: 'A6b', label: 'Dissolution — with replacement' },
  { code: 'A6c', label: 'Dissolution — bottle rotating, per-unit weight' },
  { code: 'A6d', label: 'In-vitro release — Franz diffusion cell' },
  { code: 'A7', label: 'Dissolution profile comparison (f1/f2)' },
  { code: 'A8', label: 'Content uniformity' },
  { code: 'A9', label: 'Titrimetry' },
  { code: 'A10', label: 'Gravimetric / loss on drying' },
  { code: 'A11', label: 'Microbial cylinder-plate bioassay' },
  { code: 'A12', label: 'Derived roll-ups (consume other tests)' },
  { code: 'A13', label: 'Trace / nitrosamine impurities' },
  { code: 'A14', label: 'Linearity qualification' },
];

/**
 * Pre-filled skeleton for a new template.
 *
 * Deliberately a complete, *valid, runnable* single-standard assay rather than
 * an empty shell: it passes validation as-is, so an author starts from something
 * that computes and edits towards their sheet instead of debugging a blank
 * definition into life.
 */
export const STARTER_DEFINITION = {
  resultRef: 'sample.result',
  context: [
    { key: 'batch', kind: 'context', type: 'text', label: 'Batch', source: 'trf.batch_number' },
    { key: 'product', kind: 'context', type: 'text', label: 'Product', source: 'product.name' },
    { key: 'analyst', kind: 'context', type: 'text', label: 'Analyst', source: 'session.analyst' },
  ],
  groups: [
    {
      key: 'standard',
      kind: 'table',
      label: 'Standard injections',
      rows: { min: 1, max: 6, default: 5 },
      fields: [
        { key: 'area', kind: 'area', label: 'Peak area', unit: 'µV·s' },
      ],
    },
    {
      key: 'sample',
      kind: 'singleton',
      label: 'Sample',
      fields: [
        { key: 'std_weight_mg', kind: 'input', label: 'Standard weight', unit: 'mg' },
        { key: 'std_potency', kind: 'input', label: 'Standard potency', unit: '%', default: 100 },
        { key: 'sample_weight_mg', kind: 'input', label: 'Sample weight', unit: 'mg' },
        { key: 'label_claim_mg', kind: 'input', label: 'Label claim', unit: 'mg' },
        { key: 'area', kind: 'area', label: 'Peak area', unit: 'µV·s' },
        {
          key: 'result',
          kind: 'calculated',
          label: 'Assay',
          unit: '%',
          expression:
            'area / mean(standard.area) * (std_weight_mg * std_potency / 100) / sample_weight_mg * label_claim_mg / label_claim_mg * 100',
          rounding: { mode: 'round', digits: 2 },
        },
      ],
    },
  ],
  criteria: [
    {
      key: 'std_rsd',
      label: 'Standard area %RSD',
      target: 'rsd(standard.area)',
      operator: 'lte',
      limit: 2.0,
      limitText: 'NMT 2.0%',
      severity: 'blocking',
    },
  ],
};
