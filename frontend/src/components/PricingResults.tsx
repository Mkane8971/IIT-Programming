
import type { PricingResponse } from "../api/pricing";

interface Props {
  data: PricingResponse;
}

export default function PricingResults({ data }: Props) {
  const currency = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });

  return (
    <section className="pricing-results">
      <h2>Estimated Medicare Payment</h2>

      <p>
        <strong>Locality:</strong>{" "}
        {data.locality.loc_description}
      </p>

      <p>
        <strong>Setting:</strong> {data.setting}
      </p>

      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Adjusted RVU</th>
            <th>Conversion Factor</th>
            <th>Estimated Payment</th>
          </tr>
        </thead>

        <tbody>
          {data.estimates.map((estimate, index) => {
            const category =
              estimate.price_indicator === "1"
                ? "QP"
                : estimate.price_indicator === "9"
                  ? "Standard"
                  : "Unspecified";

            return (
              <tr key={index}>
                <td>{category}</td>

                <td>{estimate.adjusted_rvu}</td>

                <td>
                  {currency.format(
                    Number(estimate.conversion_factor)
                  )}
                </td>

                <td className="payment-amount">
                  {currency.format(
                    Number(estimate.estimated_payment)
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="pricing-disclaimer">
        Estimates are based on Medicare Physician Fee
        Schedule RVUs, geographic adjustments, and
        conversion factors. Additional Medicare payment
        policies may affect actual reimbursement.
      </p>
    </section>
  );
}
