
import { useState } from "react";

import ProcedureSearch from "./components/ProcedureSearch";
import { getProcedure } from "./api/procedures";

import type {
  ProcedureResponse,
  ProcedureSearchParams,
} from "./types/procedure";

import ProcedureResults from "./components/ProcedureResults";

import "./App.css";

export default function App() {
  const [results, setResults] =
    useState<ProcedureResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(params: ProcedureSearchParams) {
    setLoading(true);
    setError("");
    setResults(null);

    try {
      const data = await getProcedure(params);
      setResults(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to retrieve procedure data."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Medicare PFS Explorer</h1>

      <ProcedureSearch
        onSearch={handleSearch}
        loading={loading}
      />

      {error && <p role="alert">{error}</p>}

      {results && <ProcedureResults data={results} />}
    </main>
  );
}
