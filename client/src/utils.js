import { Typography } from "@mui/material";
import { useState } from "react";

/** Must match alab_management.utils.time.CUTOVER_UTC_ISO */
export const TIMESTAMP_CUTOVER_UTC_ISO = "2026-11-03T01:30:00.000Z";

/**
 * Format a persisted AlabOS timestamp for operators (California wall clock).
 *
 * Pre-cutover Mongo values were Pacific wall clock stored as naive/UTC-looking
 * datetimes; keep the legacy offset correction so remembered times stay stable.
 * Post-cutover values are real UTC — normal locale formatting is enough on lab PCs.
 */
export function timestampInLocale(timestamp_string) {
  if (!timestamp_string) {
    return "";
  }
  const parsed = new Date(timestamp_string);
  if (Number.isNaN(parsed.getTime())) {
    return String(timestamp_string);
  }
  const cutover = new Date(TIMESTAMP_CUTOVER_UTC_ISO).getTime();
  if (parsed.getTime() < cutover) {
    const localTime = new Date(timestamp_string);
    localTime.setMinutes(localTime.getMinutes() + localTime.getTimezoneOffset());
    return localTime.toLocaleString();
  }
  return parsed.toLocaleString();
}


export function HoverText({ defaultText = "", hoverText = "", variant = "body1", active = true }) {
    const [isHovered, setHovered] = useState(false);

    if (active) {
        return (
            <Typography
                variant={variant}
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
            >
                {isHovered ? hoverText : defaultText}
            </Typography>
        )
    } else {
        return (
            <Typography
                variant={variant}
            >
                {defaultText}
            </Typography>
        )
    }


}