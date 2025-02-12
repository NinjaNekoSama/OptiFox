"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useThemeContext } from "../context/ThemeContext";
import { Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from "chart.js";
import SearchBar from "./SearchBar";

// Register necessary Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

// Determine the header color class based on the current theme
const getHeaderColorClass = (isDarkMode: boolean): string => {
  return isDarkMode ? "bg-gray-700 text-white" : "bg-blue-200 text-black";
};

// Determine the row color class based on the current theme
const getRowColorClass = (isDarkMode: boolean): string => {
  return isDarkMode ? "bg-gray-800 text-white" : "bg-white text-black";
};

// Determine the box color class based on readmission status
const getBoxColorClass = (willBeReadmitted: boolean): string => {
  return willBeReadmitted ? "bg-green-300" : "bg-red-900";
};

const PatientDetail = ({ patients }: any) => {
  const { isDarkMode } = useThemeContext(); // Get the current theme mode
  const router = useRouter(); // Get the router instance for navigation

  // Variables for bed availability and patient status
  const totalBeds = 20;
  const availableBeds = 10;
  const occupiedBeds = totalBeds - availableBeds;

  const totalPatients = 10;
  const criticalPatients = 9;
  const stablePatients = totalPatients - criticalPatients;

  // Data for the beds availability doughnut chart
  const doughnutDataBeds: ChartData<"doughnut"> = {
    labels: ["Available Beds", "Occupied Beds"],
    datasets: [
      {
        label: "# of Beds",
        data: [availableBeds, occupiedBeds],
        backgroundColor: ["rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)"],
        borderColor: ["rgba(54, 162, 235, 1)", "rgba(255, 99, 132, 1)"],
        borderWidth: 1,
      },
    ],
  };

  // Options for the beds availability doughnut chart
  const doughnutOptionsBeds: ChartOptions<"doughnut"> = {
    cutout: "70%",
    plugins: {
      legend: {
        display: true,
        position: "top",
      },
      tooltip: {
        callbacks: {
          label: function (tooltipItem) {
            return `${tooltipItem.label}: ${tooltipItem.raw}`;
          },
        },
      },
    },
    layout: {
      padding: {
        left: 20,
      },
    },
    responsive: true,
    maintainAspectRatio: false,
  };

  // Data for the patient status doughnut chart
  const doughnutDataPatients: ChartData<"doughnut"> = {
    labels: ["Critical Patients", "Stable Patients"],
    datasets: [
      {
        label: "# of Patients",
        data: [criticalPatients, stablePatients],
        backgroundColor: ["rgba(255, 99, 132, 0.6)", "rgba(54, 162, 235, 0.6)"],
        borderColor: ["rgba(255, 99, 132, 1)", "rgba(54, 162, 235, 1)"],
        borderWidth: 1,
      },
    ],
  };

  // Options for the patient status doughnut chart
  const doughnutOptionsPatients: ChartOptions<"doughnut"> = {
    cutout: "70%",
    plugins: {
      legend: {
        display: true,
        position: "top",
      },
      tooltip: {
        callbacks: {
          label: function (tooltipItem) {
            return `${tooltipItem.label}: ${tooltipItem.raw}`;
          },
        },
      },
    },
    layout: {
      padding: {
        left: 20,
      },
    },
    responsive: true,
    maintainAspectRatio: false,
  };

  // Handle search query and navigate to the corresponding patient page
  const handleSearch = (query: string) => {
    router.push(`/patients/${query}`);
  };

  return (
    <div className="flex flex-wrap justify-center gap-0">
      {/* Search Bar */}
      <div className="w-full flex justify-start">
        <div
          style={{
            width: "1000px",
            height: "50px",
            paddingBottom: "0px",
            paddingTop: "20px",
            paddingLeft: "20px",
          }}
        >
          <SearchBar onSearch={handleSearch} />
        </div>
      </div>

      {/* Available Beds Doughnut Chart */}
      <div className="mb-4">
        <div
          style={{
            width: "200px",
            height: "150px",
            paddingBottom: "0px",
            paddingTop: "0px",
            paddingLeft: "0px",
            paddingRight: "0px",
            marginRight: "0px",
            marginLeft: "0px",
          }}
        >
          <Doughnut data={doughnutDataBeds} options={doughnutOptionsBeds} />
        </div>
      </div>

      {/* Critical Patients Doughnut Chart */}
      <div className="mb-4">
        <div
          style={{
            width: "200px",
            height: "150px",
            paddingBottom: "0px",
            paddingTop: "0px",
            paddingLeft: "0px",
            paddingRight: "0px",
            marginLeft: "0px",
          }}
        >
          <Doughnut
            data={doughnutDataPatients}
            options={doughnutOptionsPatients}
          />
        </div>
      </div>

      {/* Patients Table */}
      <table
        className={`w-full text-sm text-left ${
          isDarkMode ? "text-gray-400" : "text-gray-500"
        } mt-4`}
      >
        <thead
          className={`text-xs uppercase ${getHeaderColorClass(isDarkMode)}`}
        >
          <tr>
            <th scope="col" className="px-6 py-3">
              Stay id
            </th>
            <th scope="col" className="px-6 py-3">
              Subject id
            </th>
            <th scope="col" className="px-6 py-3">
              First Care Unit
            </th>
            <th scope="col" className="px-6 py-3">
              Admission id
            </th>
            <th scope="col" className="px-6 py-3">
              Readmission Status
            </th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient: any) => (
            <tr
              key={patient.stay_id}
              onClick={() => router.push(`/patients/${patient.stay_id}`)}
              className={`${getRowColorClass(
                isDarkMode
              )} border-b dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer`}
            >
              <td
                className={`px-6 py-4 font-medium ${
                  isDarkMode ? "text-white" : "text-gray-900"
                } whitespace-nowrap`}
              >
                {patient.stay_id}
              </td>
              <td className="px-6 py-4">{patient.subject_id}</td>
              <td className="px-6 py-4">{patient.first_care_unit}</td>
              <td className="px-6 py-4">{patient.hadm_id}</td>
              <td className="px-6 py-4">
                <div
                  className={`w-4 h-4 ${getBoxColorClass(
                    patient.will_be_readmitted
                  )} rounded-full`}
                ></div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PatientDetail;
