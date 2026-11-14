
import { useState } from "react";

import ProcedureSearch from "./components/ProcedureSearch";
import ProcedureResults from "./components/ProcedureResults";
import PricingResults from "./components/PricingResults";
import SearchGuide from "./components/SearchGuide";

import { getProcedure } from "./api/procedures";
import { getPricingEstimate } from "./api/pricing";

import type {
  ProcedureResponse,
  ProcedureSearchParams,
} from "./types/procedure";

import type { PricingResponse } from "./api/pricing";

import "./App.css";

export default function App() {
  const [results, setResults] =
    useState<ProcedureResponse | null>(null);

  const [pricing, setPricing] =
    useState<PricingResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(
    params: ProcedureSearchParams
  ) {
    setLoading(true);
    setError("");
    setResults(null);
    setPricing(null);

    try {
      const [procedureData, pricingData] =
        await Promise.all([
          getProcedure(params),
          getPricingEstimate(params),
        ]);

      setResults(procedureData);
      setPricing(pricingData);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to retrieve Medicare data."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Medicare PFS Explorer</h1>

      <SearchGuide />

      <ProcedureSearch
        onSearch={handleSearch}
        loading={loading}
      />

      {error && (
        <p role="alert">{error}</p>
      )}

      {results && (
        <ProcedureResults data={results} />
      )}

      {pricing && (
        <PricingResults data={pricing} />
      )}
    </main>
  );
}
