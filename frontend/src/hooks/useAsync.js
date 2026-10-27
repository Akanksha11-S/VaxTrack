import { useCallback, useEffect, useRef, useState } from "react";

/** Runs an async loader on mount (and when deps change). Returns { data, loading, error, reload, setData }. */
export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const alive = useRef(true);
  const run = useCallback(async (silent = false) => {
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await loader();
      if (alive.current) setState({ data, loading: false, error: null });
    } catch (error) {
      if (alive.current) setState((s) => ({ data: silent ? s.data : null, loading: false, error }));
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { alive.current = true; run(); return () => { alive.current = false; }; }, [run]);
  return { ...state, reload: () => run(true), retry: () => run(false), setData: (data) => setState((s) => ({ ...s, data })) };
}
