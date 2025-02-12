"use client";

import React, { useState } from "react";
import { Line } from "react-chartjs-2";
import { useThemeContext } from "../../context/ThemeContext";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";

// Register the necessary Chart.js components
ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend
);

// Utility function to determine header color based on the theme
const getHeaderColorClass = (isDarkMode: boolean): string => {
  return isDarkMode ? "bg-gray text-white" : "bg-blue-200 text-black";
};

// Utility function to determine row color based on the theme
const getRowColorClass = (isDarkMode: boolean): string => {
  return isDarkMode
    ? "bg-gray text-white border-white"
    : "bg-white text-black border-black";
};

// Props interface for the chart component
interface ChartComponentProps {
  data: number[];
  labels: string[];
  title: string;
}

// Props interface for individual accordion items
interface AccordionItemProps {
  title: string;
  data: number[];
  labels: string[];
  isOpen: boolean;
  onClick: () => void;
}

// Props interface for the accordion component
interface AccordionProps {
  details: Record<string, Record<string, number | null>>;
}

// Accordion component to display multiple features with charts
const Accordion: React.FC<AccordionProps> = ({ details }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const { isDarkMode } = useThemeContext();

  // Handle clicks on accordion items to toggle their open state
  const handleAccordionClick = (index: number) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div
        className={`mb-4 font-bold ${isDarkMode ? "text-white" : "text-black"}`}
        style={{ position: "sticky", top: 0, zIndex: 1 }}
      >
        Influencing Features
      </div>
      <div style={{ overflowY: "auto", flex: 1 }}>
        {/* Render each feature as an accordion item */}
        {Object.keys(details).map((feature, index) => {
          const chartData = Object.values(details[feature]).map((value) =>
            value === null ? 0 : value
          );
          const chartLabels = Array.from({ length: 24 }, (_, i) =>
            (i + 1).toString()
          );
          return (
            <AccordionItem
              key={feature}
              title={feature}
              data={chartData}
              labels={chartLabels}
              isOpen={activeIndex === index}
              onClick={() => handleAccordionClick(index)}
            />
          );
        })}
      </div>
    </div>
  );
};

// AccordionItem component to handle the individual items within the accordion
const AccordionItem: React.FC<AccordionItemProps> = ({
  title,
  data,
  labels,
  isOpen,
  onClick,
}) => {
  const { isDarkMode } = useThemeContext();

  return (
    <div
      onClick={onClick}
      className={`mb-2 border rounded-md ${getRowColorClass(isDarkMode)}`}
    >
      <div className="p-3 cursor-pointer">{title}</div>
      {/* Conditionally render the chart based on the open state */}
      <div
        className={`overflow-hidden transition-all duration-250 ease-in-out ${
          isOpen ? "max-h-[400px] pt-4" : "max-h-0 pt-0"
        }`}
      >
        <div
          style={{
            height: isOpen ? "300px" : "0px",
            transition: "height 0.4s ease-in-out",
          }}
        >
          <ChartComponent data={data} labels={labels} title={title} />
        </div>
      </div>
    </div>
  );
};

// ChartComponent to render a line chart using the provided data
const ChartComponent: React.FC<ChartComponentProps> = ({
  data,
  labels,
  title,
}) => {
  const { isDarkMode } = useThemeContext();

  // Prepare the chart data and configuration
  const chartData = {
    labels: labels,
    datasets: [
      {
        label: title,
        data: data,
        backgroundColor: "rgba(75,192,192,0.4)",
        borderColor: "rgba(75,192,192,1)",
        pointBorderColor: "rgba(75,192,192,1)",
        fill: true,
      },
    ],
  };

  const options: any = {
    maintainAspectRatio: false, // Allows chart to resize correctly
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Hour",
          color: isDarkMode ? "white" : "black",
        },
        ticks: {
          color: isDarkMode ? "white" : "black",
        },
      },
      y: {
        title: {
          display: true,
          text: "Value",
          color: isDarkMode ? "white" : "black",
        },
        ticks: {
          stepSize: 1,
          beginAtZero: true,
          suggestedMax: 120, // Adjust to ensure data fits within the chart
          color: isDarkMode ? "white" : "black",
        },
      },
    },
  };

  return <Line data={chartData} options={options} />;
};

export default Accordion;
