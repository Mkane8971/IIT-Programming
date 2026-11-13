
import type { ProcedureResponse } from "../types/procedure";

interface Props {
  data: ProcedureResponse;
}

export default function ProcedureResults({ data }: Props) {
  const { records, setting, source } = data;

  return (
    <section>
      <h2>Procedure Results</h2>

      <p>Data source: {source === "mongodb" ? "Cached" : "CMS"}</p>

      <table>
        <thead>
          <tr>
            <th>HCPCS</th>
            <th>Description</th>
            <th>Category</th>
            <th>Work RVU</th>
            <th>PE RVU</th>
            <th>MP RVU</th>
            <th>Conversion Factor</th>
          </tr>
        </thead>

        <tbody>
          {records.map((record, index) => {
            const peRvu =
              setting === "facility"
                ? record.full_fac_pe || record.fac_pe
                : record.full_nfac_pe || record.nfac_pe;

            const category =
              record.price_ind === "1"
                ? "QP"
                : record.price_ind === "9"
                  ? "Standard"
                  : "Unspecified";

            return (
              <tr key={`${record.hcpc}-${record.price_ind ?? index}`}>
                <td>{record.hcpc}</td>
                <td>{record.sdesc}</td>
                <td>{category}</td>
                <td>{record.rvu_work}</td>
                <td>{peRvu ?? "N/A"}</td>
                <td>{record.rvu_mp}</td>
                <td>{record.conv_fact ?? "N/A"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
