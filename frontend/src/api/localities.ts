
export interface CMSLocality {
  year: string;
  locality: string;
  loc_description: string;
  mac: string;
  mac_description: string;
  gpci_work: string;
  gpci_pe: string;
  gpci_mp: string;
}

export interface LocalitiesResponse {
  year: number;
  count: number;
  localities: CMSLocality[];
}

export async function getLocalities(
  year: number
): Promise<LocalitiesResponse> {
  const response = await fetch(
    `/api/v1/localities?year=${year}`
  );

  if (!response.ok) {
    throw new Error(
      `Unable to retrieve Medicare localities (${response.status})`
    );
  }

  return response.json();
}
