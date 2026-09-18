import React from "react";
import { Alert } from "@mui/material";
import { useLabReadiness } from "../../LabReadiness";

/** Banner + optional disable wrapper for direct hardware control pages. */
export default function LabNotReadyGate({ children }) {
  const { labReady, labReadyLabel } = useLabReadiness();
  return (
    <>
      {!labReady && (
        <Alert severity="warning" sx={{ m: 2, mb: 0 }}>
          Waiting for lab devices… ({labReadyLabel}). Direct control is disabled until
          the lab is ready.
        </Alert>
      )}
      <div
        style={{
          opacity: labReady ? 1 : 0.55,
          pointerEvents: labReady ? "auto" : "none",
        }}
      >
        {children}
      </div>
    </>
  );
}
