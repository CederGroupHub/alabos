import { Typography } from "@mui/material";
import { useState } from "react";


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