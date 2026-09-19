import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { get_status } from "./api_routes";

const LabReadinessContext = createContext({
  labReady: true,
  labReadyLabel: "Lab ready",
  deviceRpc: null,
});

export function LabReadinessProvider({ children }) {
  const [labReady, setLabReady] = useState(true);
  const [labReadyLabel, setLabReadyLabel] = useState("Lab ready");
  const [deviceRpc, setDeviceRpc] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      get_status()
        .then((status) => {
          if (cancelled || !status) {
            return;
          }
          if (typeof status.lab_ready === "boolean") {
            setLabReady(status.lab_ready);
            setLabReadyLabel(status.lab_ready_label || (status.lab_ready ? "Lab ready" : "Lab starting..."));
            setDeviceRpc(status.device_rpc || null);
          }
        })
        .catch(() => {});
    };
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const value = useMemo(
    () => ({ labReady, labReadyLabel, deviceRpc }),
    [labReady, labReadyLabel, deviceRpc]
  );

  return (
    <LabReadinessContext.Provider value={value}>
      {children}
    </LabReadinessContext.Provider>
  );
}

export function useLabReadiness() {
  return useContext(LabReadinessContext);
}
