import { useState, useEffect } from 'react';

export function useResults<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetch(`/data/${path}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to fetch /data/${path}: ${res.status} ${res.statusText}`);
        }
        return res.json();
      })
      .then((json) => {
        if (isMounted) {
          setData(json as T);
          setLoading(false);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [path]);

  return { data, loading, error };
}
