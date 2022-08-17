import { Typography } from "@mui/material";
import { useState, useRef, useEffect } from "react";

function useHover() {
    const [value, setValue] = useState(false);
    const ref = useRef(null);
    const handleMouseOver = () => setValue(true);
    const handleMouseOut = () => setValue(false);
    useEffect(
        () => {
            const node = ref.current;
            if (node) {
                node.addEventListener("mouseover", handleMouseOver);
                node.addEventListener("mouseout", handleMouseOut);
                return () => {
                    node.removeEventListener("mouseover", handleMouseOver);
                    node.removeEventListener("mouseout", handleMouseOut);
                };
            }
        },
        [ref.current] // Recall only if ref changes
    );
}
// export function HoverText({ defaultText, hoverText, variant = "body1" }) {
//     const [hoveredRef, isHovered] = useHover();


//     return (
//         <div ref={hoveredRef}>
//             <Typography
//                 variant={variant}
//             // onMouseEnter={() => setHovered(true)}
//             // onMouseLeave={() => setHovered(false)}>
//             >
//                 {isHovered ? hoverText : defaultText}
//                 {/* {defaultText} */}
//             </Typography >
//         </div >
//     );
// }

export function HoverText({ defaultText, hoverText, variant = "body1", active = true }) {
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