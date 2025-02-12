"use client";

import React from "react";
import { Switch } from "@mui/material";
import { useThemeContext } from "../context/ThemeContext";

const ThemeToggle: React.FC = () => {
  const { toggleTheme, isDarkMode } = useThemeContext();

  return <Switch checked={isDarkMode} onChange={toggleTheme} />;
};

export default ThemeToggle;
