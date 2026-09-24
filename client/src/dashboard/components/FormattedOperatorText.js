import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";

const TRACEBACK_HEADER = "Traceback (most recent call last):";
const FIELD_RE = /^-\s+(What|Where|In project code|Stage|Task|Samples|Cause):\s*(.*)$/i;
const ACTION_RE = /^\((\d+)\)\s+(.*)$/;

export function parseOperatorText(text) {
  const raw = String(text || "").replace(/\r\n/g, "\n");
  const tbIndex = raw.indexOf(TRACEBACK_HEADER);
  const summary = tbIndex === -1 ? raw : raw.slice(0, tbIndex);
  const traceback = tbIndex === -1 ? "" : raw.slice(tbIndex).trim();

  const intro = [];
  const actions = [];
  const fields = [];
  let title = "";

  const lines = summary.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const trimmed = lines[i].trim();
    if (!trimmed) {
      continue;
    }

    const actionMatch = trimmed.match(ACTION_RE);
    if (actionMatch) {
      actions.push({ n: actionMatch[1], text: actionMatch[2] });
      continue;
    }

    const fieldMatch = trimmed.match(FIELD_RE);
    if (fieldMatch) {
      let value = fieldMatch[2];
      const extras = [];
      while (i + 1 < lines.length && /^\s{2,}\S/.test(lines[i + 1])) {
        i += 1;
        extras.push(lines[i].trim());
      }
      if (extras.length) {
        value = value ? `${value}\n${extras.join("\n")}` : extras.join("\n");
      }
      fields.push({ label: fieldMatch[1], value });
      continue;
    }

    if (trimmed.startsWith("ERROR:")) {
      title = trimmed.replace(/^ERROR:\s*/, "");
      continue;
    }

    if (/^what to do:?$/i.test(trimmed)) {
      continue;
    }

    intro.push(trimmed);
  }

  return { intro, title, actions, fields, traceback };
}

export default function FormattedOperatorText({ text }) {
  const [showTrace, setShowTrace] = React.useState(false);
  const parsed = React.useMemo(() => parseOperatorText(text), [text]);

  if (!text) {
    return null;
  }

  const hasStructure = Boolean(
    parsed.title || parsed.actions.length || parsed.fields.length || parsed.traceback
  );
  if (!hasStructure) {
    return (
      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {text}
      </Typography>
    );
  }

  return (
    <Box sx={{ textAlign: "left" }}>
      {parsed.intro.map((line) => (
        <Typography key={line} variant="body2" sx={{ mb: 0.75, fontWeight: 600 }}>
          {line}
        </Typography>
      ))}
      {parsed.actions.length > 0 && (
        <Box component="ol" sx={{ m: 0, mb: 1.5, pl: 2.5 }}>
          {parsed.actions.map((action) => (
            <Typography key={`${action.n}-${action.text}`} component="li" variant="body2" sx={{ mb: 0.5 }}>
              {action.text}
            </Typography>
          ))}
        </Box>
      )}
      {parsed.title ? (
        <Typography variant="body2" sx={{ mb: 1, color: "error.main", fontWeight: 600 }}>
          {parsed.title}
        </Typography>
      ) : null}
      {parsed.fields.length > 0 && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            columnGap: 1.5,
            rowGap: 0.75,
            mb: parsed.traceback ? 1 : 0,
          }}
        >
          {parsed.fields.map((field) => (
            <React.Fragment key={`${field.label}-${field.value}`}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: "text.secondary" }}>
                {field.label}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {field.value}
              </Typography>
            </React.Fragment>
          ))}
        </Box>
      )}
      {parsed.traceback ? (
        <>
          <Button
            size="small"
            onClick={() => setShowTrace((value) => !value)}
            sx={{ px: 0, minWidth: 0, textTransform: "none" }}
          >
            {showTrace ? "Hide traceback" : "Show traceback"}
          </Button>
          <Collapse in={showTrace}>
            <Box
              component="pre"
              sx={{
                m: 0,
                mt: 1,
                p: 1,
                bgcolor: "grey.100",
                borderRadius: 1,
                overflow: "auto",
                maxHeight: 280,
                fontFamily: "Source Code Pro, ui-monospace, monospace",
                fontSize: "0.75rem",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {parsed.traceback}
            </Box>
          </Collapse>
        </>
      ) : null}
    </Box>
  );
}
