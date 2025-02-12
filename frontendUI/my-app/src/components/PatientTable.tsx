import React, { useEffect, useState } from "react";
import { Grid, Typography, Paper } from "@mui/material";
import GradientLegend from "./GradientLegend"; // Ensure this import path is correct

interface PatientTableProps {
  readmissionLikelihood: number;
  lengthOfStay: number;
  stayId: string;
}

const PatientTable: React.FC<PatientTableProps> = ({
  readmissionLikelihood,
  lengthOfStay,
  stayId,
}) => {
  const [patientData, setPatientData] = useState<
    {
      date: string;
      readmissionLikelihood: number;
      mortalityLikelihood: number;
    }[]
  >([]);

  useEffect(() => {
    // Generate new random likelihoods when stayId changes
    const newPatientData = Array.from({ length: 6 }, (_, index) => ({
      date: subtractDays(index),
      readmissionLikelihood: Math.floor(Math.random() * 11),
      mortalityLikelihood: Math.floor(Math.random() * 11),
    }));
    setPatientData(newPatientData);
  }, [stayId]);

  const subtractDays = (days: number) => {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
  };

  // Generate SVG gradient stops as HTML string for readmission
  const generateGradientStopsReadmission = () => {
    return patientData
      .map((data, index) => {
        const offset = (index / (patientData.length - 1)) * 100;
        const hue = 120 * (1 - data.readmissionLikelihood / 10); // 120 (green) to 0 (red)
        return `<stop offset="${offset}%" stop-color="hsl(${hue}, 100%, 50%)" />`;
      })
      .join("");
  };

  // Generate SVG gradient stops as HTML string for mortality
  const generateGradientStopsMortality = () => {
    return patientData
      .map((data, index) => {
        const offset = (index / (patientData.length - 1)) * 100;
        const hue = 120 * (1 - data.mortalityLikelihood / 10); // 120 (green) to 0 (red)
        return `<stop offset="${offset}%" stop-color="hsl(${hue}, 100%, 50%)" />`;
      })
      .join("");
  };

  const gradientHtmlReadmission = `<linearGradient id="gradReadmission">${generateGradientStopsReadmission()}</linearGradient>`;
  const gradientHtmlMortality = `<linearGradient id="gradMortality">${generateGradientStopsMortality()}</linearGradient>`;

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Paper
          style={{
            marginTop: "20px",
            padding: "20px",
            backgroundColor: "#E4D1CE",
          }}
        >
          <Typography
            variant="h6"
            gutterBottom
            style={{ color: "#333333" }}
          ></Typography>
          <Typography variant="subtitle1" style={{ color: "#333" }}>
            Readmission Likelihood
          </Typography>
          <svg width="100%" height="50">
            <defs
              dangerouslySetInnerHTML={{ __html: gradientHtmlReadmission }}
            />
            <rect width="100%" height="50" fill="url(#gradReadmission)" />
          </svg>
          <Typography
            variant="subtitle1"
            style={{ color: "#333", marginTop: "20px" }}
          >
            Mortality Likelihood
          </Typography>
          <svg width="100%" height="50">
            <defs dangerouslySetInnerHTML={{ __html: gradientHtmlMortality }} />
            <rect width="100%" height="50" fill="url(#gradMortality)" />
          </svg>
        </Paper>
      </Grid>
      {/* GradientLegend outside the Paper but still within the grid */}
      <Grid item xs={12} style={{ marginTop: "20px" }}>
        <GradientLegend />
      </Grid>
    </Grid>
  );
};

export default PatientTable;
