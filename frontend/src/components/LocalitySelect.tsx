import { useEffect, useState } from "react";

import {
  getLocalities,
  type CMSLocality,
} from "../api/localities";

interface Props {
  year: number;
  value: string;
  onChange: (locality: string) => void;
}

export default function LocalitySelect({
  year,
  value,
  onChange,
}: Props) {
  const [localities, setLocalities] = useState<CMSLocality[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadLocalities() {
      setLoading(true);
      setError("");
      setLocalities([]);

      try {
        const response = await getLocalities(year);

        if (!active) return;

        const sorted = response.localities.sort(
          (a, b) =>
            a.loc_description.localeCompare(
              b.loc_description
            )
        );

        setLocalities(sorted);
      } catch {
        if (active) {
          setError("Unable to load Medicare localities.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadLocalities();

    return () => {
      active = false;
    };
  }, [year]);

  return (
    <div className="form-field">
      <label htmlFor="locality">
        Medicare Payment Locality
      </label>

      <select
        id="locality"
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        disabled={loading || !!error}
        required
      >
        <option value="">
          {loading
            ? "Loading localities..."
            : "Select a locality"}
        </option>

        {localities.map((item) => (
          <option
            key={item.locality}
            value={item.locality}
          >
            {item.loc_description}
          </option>
        ))}
      </select>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  );
}
