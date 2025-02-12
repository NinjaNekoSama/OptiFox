import React from "react";
import { IconButton } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";

// Component to handle language selection (currently a placeholder)
const LanguageIconComponent: React.FC = () => {
  
  // Placeholder function for handling language change
  const handleLanguageChange = () => {};

  return (
    // IconButton to trigger language change when clicked
    <IconButton color="inherit" onClick={handleLanguageChange}>
      <LanguageIcon /> {/* Language icon displayed inside the button */}
    </IconButton>
  );
};

export default LanguageIconComponent;