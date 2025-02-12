"use client";

import React, { useState } from "react";
import { AppBar, Toolbar, Menu, MenuItem } from "@mui/material";
import ThemeToggle from "./ThemeToggle";
import LanguageIcon from "./LanguageIcon";
import { useThemeContext } from "../context/ThemeContext";

interface AppBarComponentProps {
  onSearchPatient: (term: string) => void; // Function to handle patient search
}

const AppBarComponent: React.FC<AppBarComponentProps> = ({
  onSearchPatient,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null); // State to manage the anchor element for the menu
  const [patientInfo, setPatientInfo] = useState<any>(null); // State to hold patient information
  const { isDarkMode } = useThemeContext(); // Get the current theme mode from context
  const [error, setError] = useState<string | null>(null); // State to manage error messages
  const [loading, setLoading] = useState<boolean>(false); // State to manage loading state

  // Determine the AppBar background color based on the theme mode
  const appBarBackgroundColor = isDarkMode ? "#121212" : "#03acab";

  return (
    <AppBar
      position="static"
      style={{ backgroundColor: appBarBackgroundColor }} // Apply the background color
    >
      <Toolbar>
        {/* Display the OptiFox logo, with different versions based on the theme */}
        <img
          src={isDarkMode ? "/optifoxdark.png" : "/optifoxlight.png"}
          alt="OptiFox Logo"
          style={{
            cursor: "pointer",
            height: "60px",
            width: "auto",
            marginLeft: "-20px",
          }}
        />
        <div style={{ flexGrow: 1 }} />{" "}
        {/* Spacer to push icons to the right */}
        <LanguageIcon /> {/* Language selection icon */}
        <ThemeToggle /> {/* Theme toggle switch */}
        {/* Placeholder for additional elements like search, if needed */}
      </Toolbar>
    </AppBar>
  );
};

export default AppBarComponent;
