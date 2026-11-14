
import { useState, type FormEvent } from "react";

import LocalitySelect from "./LocalitySelect";

import type {
  ProcedureSearchParams,
  Setting,
} from "../types/procedure";

interface Props {
  onSearch: (params: ProcedureSearchParams) => void;
  loading: boolean;
}

export default function ProcedureSearch({
  onSearch,
  loading,
}: Props) {
  const [hcpcs, setHcpcs] = useState("27447");
  const [year, setYear] = useState(2026);
  const [modifier, setModifier] = useState("");
  const [setting, setSetting] =
    useState<Setting>("facility");
  const [locality, setLocality] = useState("");

  function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!locality) return;

    onSearch({
      hcpcs: hcpcs.trim().toUpperCase(),
      year,
      modifier:
        modifier.trim().toUpperCase() || undefined,
      setting,
      locality,
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Procedure Search</h2>

      <div className="form-field">
        <label htmlFor="hcpcs">
          HCPCS / CPT Code
        </label>

        <input
          id="hcpcs"
          value={hcpcs}
          onChange={(event) =>
            setHcpcs(event.target.value)
          }
          minLength={5}
          maxLength={5}
          pattern="[A-Za-z0-9]{5}"
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="year">
          Calendar Year
        </label>

        <input
          id="year"
          type="number"
          min={2000}
          max={2100}
          value={year}
          onChange={(event) => {
            setYear(Number(event.target.value));
            setLocality("");
          }}
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="modifier">
          Modifier (Optional)
        </label>

        <input
          id="modifier"
          value={modifier}
          onChange={(event) =>
            setModifier(event.target.value)
          }
          maxLength={2}
          pattern="[A-Za-z0-9]{2}"
          placeholder="26, TC, etc."
        />
      </div>

      <div className="form-field">
        <label htmlFor="setting">
          Setting
        </label>

        <select
          id="setting"
          value={setting}
          onChange={(event) =>
            setSetting(
              event.target.value as Setting
            )
          }
        >
          <option value="facility">
            Facility
          </option>

          <option value="nonfacility">
            Non-facility
          </option>
        </select>
      </div>

      <LocalitySelect
        year={year}
        value={locality}
        onChange={setLocality}
      />

      <button type="submit" disabled={loading}>
        {loading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
