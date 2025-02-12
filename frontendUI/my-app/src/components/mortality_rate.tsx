import React from "react";
import { useThemeContext } from "../context/ThemeContext"; // Correct path confirmed

interface MortalityValue {
  date: string;
  mortalityRate: number;
}

interface MortalityValueProps {
  data: MortalityValue[];
}

const getColorClass = (isDarkMode: boolean): string => {
  return isDarkMode ? "bg-blue-950 text-white" : "bg-blue-200 text-black";
};

const getBorderColorClass = (isDarkMode: boolean): string => {
  return isDarkMode ? "border-blue-950" : "border-blue-200";
};

const MortalityComponent: React.FC<MortalityValueProps> = ({ data }) => {
  const { isDarkMode } = useThemeContext(); // Using theme state directly from context

  const getBackgroundColor = (rate: number) => {
    if (rate > 11) {
      return "bg-red-600"; // High mortality rate
    } else if (rate > 6) {
      return "bg-yellow-500"; // Medium mortality rate
    } else {
      return "bg-green-600"; // Low mortality rate
    }
  };

  return (
    <div className={`pl-5 ${getColorClass(isDarkMode)}`}>
      <p className="font-sans font-normal text-xl">Mortality Rate</p>
      <table>
        <tbody className="font-sans sans-serif">
          {data.map((item, index) => (
            <tr
              key={index}
              className={`${
                index === 0
                  ? `text-5xl h-16 font-bold indent-3 border-b-8 ${getBorderColorClass(
                      isDarkMode
                    )}`
                  : `indent-3 text-2xl font-bold border-b-8 ${getBorderColorClass(
                      isDarkMode
                    )}`
              } ${getBackgroundColor(item.mortalityRate)}`}
            >
              <td>{item.mortalityRate}</td>
              <td className="px-14 pt-2 text-xs">{item.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default MortalityComponent;
