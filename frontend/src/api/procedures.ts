
import type {
  ProcedureSearchParams,
  ProcedureResponse,
} from "../types/procedure";

export async function getProcedure(
  params: ProcedureSearchParams
): Promise<ProcedureResponse> {
  const query = new URLSearchParams({
    year: String(params.year),
    setting: params.setting,
  });

  if (params.modifier) {
    query.set("modifier", params.modifier);
  }

  const response = await fetch(
    `/api/v1/procedures/${encodeURIComponent(params.hcpcs)}?${query}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : `Request failed with status ${response.status}`
    );
  }

  return response.json();
}
