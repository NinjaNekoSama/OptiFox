FrontendUI - OptiFox Project

This repository contains the frontend component of the OptiFox project, built using Next.js.
Getting Started

Prerequisites

    •	Node.js (v18 or higher)
    •	npm (bundled with Node.js)

Installation

    1.	Install Node.js and npm if they are not already installed:
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
    2.	Navigate to the project directory:
        cd frontendUI/my-app
    3.	Install the required npm packages:
        npm install     

Running the Development Server

    To start the development server, use:
        npm run dev
    Then open http://localhost:3000 in your browser to view the application. The server will automatically reload whenever you make changes to the source files.

Docker Setup

    This project includes a Dockerfile for containerization.
    Building and Running the Docker Container
        To build and run the Docker container, use:
            docker build -t optifox-frontend .
            docker run -p 3000:3000 optifox-frontend
        Your application will be available at http://localhost:3000.

Project Structure

    frontendUI/
    │
    ├── my-app/
    │   ├── .next/                # Next.js build output (auto-generated)
    │   ├── node_modules/         # Node.js packages (auto-generated)
    │   ├── public/               # Static assets (e.g., images, icons)
    │   ├── src/
    │   │   ├── app/
    │   │   │   ├── patients/
    │   │   │   │   ├── [stayId]/ # Dynamic routes for patient details
    │   │   │   │   │   └── page.tsx
    │   │   │   │   └── page.tsx  # Main patient page
    │   │   │   ├── favicon.ico   # Favicon for the app
    │   │   │   ├── globals.css   # Global CSS styles
    │   │   │   ├── layout.tsx    # Layout component for the application
    │   │   │   ├── LoginPage.css # Login page specific styles
    │   │   │   ├── LoginPage.tsx # Login page component
    │   │   │   └── page.tsx      # This is the login page
    │   │   ├── components/       # Reusable React components
    │   │   │   ├── FC/
    │   │   │   │   ├── Accordion.tsx        # Accordion component
    │   │   │   │   ├── FeatureCard.tsx      # Feature card component
    │   │   │   ├── AppBarComponent.tsx      # Top navigation bar
    │   │   │   ├── GradientLegend.tsx       # Gradient legend for visualizations
    │   │   │   ├── LanguageIcon.tsx         # Language switch icon
    │   │   │   ├── mortality_rate.tsx       # Component to display mortality rate
    │   │   │   ├── PatientDetail.tsx        # Detailed view of patient data
    │   │   │   ├── PatientPage.tsx          # Main patient page
    │   │   │   ├── PatientTable.tsx         # Table to display patient data
    │   │   │   ├── Predictions.tsx          # Predictions component
    │   │   │   ├── SearchBar.tsx            # Search bar component
    │   │   │   └── ThemeToggle.tsx          # Theme toggle switch
    │   │   ├── context/          # Context API for global state management
    │   ├── .eslintc.json         # ESLint configuration file
    │   ├── .gitignore            # Git ignore file
    │   ├── next-env.d.ts         # Next.js environment types for TypeScript
    │   ├── next.config.mjs       # Next.js configuration file
    │   ├── package.json          # Project dependencies and scripts
    │   ├── package-lock.json     # Locked versions of npm dependencies
    │   ├── postcss.config.mjs    # PostCSS configuration for Tailwind CSS
    │   ├── README.md             # This documentation file
    │   ├── tailwind.config.ts    # Tailwind CSS configuration file
    │   └── tsconfig.json         # TypeScript configuration file
    ├── node_modules/            # Node.js packages (auto-generated, root level)
    ├── .gitignore               # Git ignore file (root level)
    ├── package.json             # Project dependencies and scripts (root level)
    ├── package-lock.json        # Locked versions of npm dependencies (root level)

Learn More
    For further information about Next.js, explore the following resources:
    •	Next.js Documentation - Comprehensive guides and API reference.
	•	Learn Next.js - Interactive tutorial for Next.js.

