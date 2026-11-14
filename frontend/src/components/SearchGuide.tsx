
export default function SearchGuide() {
  return (
    <details className="search-guide">
      <summary>How to Use This Explorer</summary>

      <p>
        Enter a procedure code, select a calendar year,
        choose a care setting and Medicare payment locality,
        then click Search.
      </p>

      <p>
        <strong>Try an example:</strong> CPT 27447
        (total knee arthroplasty), year 2026,
        Facility setting, Arizona locality.
        Leave the modifier blank.
      </p>

      <h4>Understanding the Results</h4>

      <p>
        Results include relative value units (RVUs),
        geographic practice cost indices (GPCIs),
        and conversion factors used to estimate Medicare
        reimbursement.
      </p>

      <p>
        Multiple records may appear when CMS provides
        different conversion factors, including qualifying
        APM participant (QP) and standard rates.
        Historical data may identify a specific
        fee schedule release.
      </p>

      <small>
        Estimates are educational and may differ from
        actual reimbursement due to Medicare payment policies.
      </small>
    </details>
  );
}
