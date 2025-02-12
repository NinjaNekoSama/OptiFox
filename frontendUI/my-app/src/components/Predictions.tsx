import React from "react";
import { Grid, Typography, Paper } from "@mui/material";

interface ReadmissionStatusProps {
  will_be_readmitted: number;
  mortality_rate: number;
}

const ReadmissionStatus: React.FC<ReadmissionStatusProps> = ({
  will_be_readmitted,
  mortality_rate,
}) => {
  // Function to calculate color based on mortality rate
  const getColorForMortality = (rate: number) => {
    const hue = ((100 - rate) * 120) / 100; // Calculate hue from green (120) to red (0)
    return `hsl(${hue}, 100%, 50%)`; // Return HSL color string
  };

  // Function to determine color based on readmission likelihood
  const getColorForReadmission = (readmitted: number) => {
    return readmitted > 50 ? "#FF6B6B" : "#4CAF50"; // Red for readmitted, green for not readmitted
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={6}>
        <Paper style={{ height: "250px", marginTop: "20px", padding: "20px" }}>
          <Typography
            variant="h6"
            gutterBottom
            style={{ marginBottom: "10px" }}
          >
            Readmission Status
          </Typography>
          <Grid
            container
            justifyContent="center"
            alignItems="center"
            style={{ height: "100%" }}
          >
            <div
              style={{
                width: "100%",
                height: "65%",
                backgroundColor: getColorForReadmission(will_be_readmitted),
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: "bold",
                color: "white",
                fontSize: "24px",
                padding: "20px",
                boxSizing: "border-box",
              }}
            >
              {will_be_readmitted > 50 ? "Readmitted" : "Not Readmitted"}
            </div>
          </Grid>
        </Paper>
      </Grid>
      <Grid item xs={6}>
        <Paper style={{ height: "250px", marginTop: "20px", padding: "20px" }}>
          <Typography
            variant="h6"
            gutterBottom
            style={{ marginBottom: "10px" }}
          >
            Mortality Rate
          </Typography>
          <Grid
            container
            justifyContent="center"
            alignItems="center"
            style={{ height: "100%" }}
          >
            <div
              style={{
                width: "100%",
                height: "65%",
                backgroundColor: getColorForMortality(mortality_rate),
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: "bold",
                color: "white",
                fontSize: "24px",
                padding: "20px",
                boxSizing: "border-box",
              }}
            >
              {mortality_rate}%
            </div>
          </Grid>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default ReadmissionStatus;
