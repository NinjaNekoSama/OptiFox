import React from "react";
import { ThemeContextProvider } from "../context/ThemeContext";
import "./globals.css";
import AppBarComponent from "@/components/AppBarComponent";

type LayoutProps = {
  children: React.ReactNode;
};

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <html lang="en">
      <head>
        {/* Meta tags for character set and responsive design */}
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        {/* Page title */}
        <title>OptiFox</title>
      </head>
      <body>
        {/* Wrap the content with ThemeContextProvider for theme management */}
        <ThemeContextProvider>
          {/* App bar component displayed at the top of the page */}
          <AppBarComponent />
          {/* Render the children components passed to the layout */}
          {children}
        </ThemeContextProvider>
      </body>
    </html>
  );
};

export default Layout;
