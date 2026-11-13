
export type Setting = "facility" | "nonfacility";

export interface ProcedureSearchParams {
  hcpcs: string;
  year: number;
  modifier?: string;
  setting: Setting;
}

export interface CMSProcedure {
  year: string;
  hcpc: string;
  modifier: string | null;
  sdesc: string;
  rvu_work: string;
  rvu_mp: string;
  full_fac_pe?: string;
  full_nfac_pe?: string;
  fac_pe?: string;
  nfac_pe?: string;
  conv_fact?: string;
  price_ind?: string;
}

export interface ProcedureResponse {
  source: "cms" | "mongodb";
  setting: Setting;
  records: CMSProcedure[];
}
