
import type { ProcedureSearchParams } from "../types/procedure";

export interface PaymentEstimate {
  hcpcs: string;
  year: number;
  modifier: string | null;
  setting: string;
  locality: string;
  locality_name: string;
  price_indicator: string | null;
  work_rvu: string;
  pe_rvu: string;
  mp_rvu: string;
  work_gpci: string;
  pe_gpci: string;
  mp_gpci: string;
  conversion_factor: string;
  adjusted_rvu: string;
  estimated_payment: string;
}

export interface PricingResponse {
  hcpcs: string;
  year: number;
  setting: string;
  source: "cms" | "mongodb";
  locality: {
    locality: string;
    loc_description: string;
    gpci_work: string;
    gpci_pe: string;
    gpci_mp: string;
  };
  estimates: PaymentEstimate[];
}

export async function getPricingEstimate(
  params: ProcedureSearchParams
): Promise<PricingResponse> {
  const query = new URLSearchParams({
    hcpcs: params.hcpcs,
    year: String(params.year),
    locality: params.locality,
    setting: params.setting,
  });

  if (params.modifier) {
    query.set("modifier", params.modifier);
  }

  const response = await fetch(
    `/api/v1/pricing/estimate?${query}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : `Pricing request failed (${response.status})`
    );
  }

  return response.json();
}
