import { useState, useEffect } from "react";

export function useAPI<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetcher()
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? e.message ?? "Error"))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
