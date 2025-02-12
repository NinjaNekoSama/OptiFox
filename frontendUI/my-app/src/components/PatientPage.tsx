"use client";

import React from "react";
import { Card, CardContent, Typography } from "@mui/material";
import SearchBar from "./SearchBar";
import { useRouter } from "next/navigation";
import ReadmissionStatus from "./Predictions";
import PatientTable from "./PatientTable";
import FeatureCard from "./FC/FeatureCard";

interface PatientInfo {
  stay_id: string;
  name: string;
  age: number;
  gender: string;
  los_hour_int: number;
  intime: string;
  outtime: string;
  percentage: number;
}

interface PatientPageProps {
  data: PatientInfo;
  featureDetails: Record<string, Record<string, number | null>>;
  stay_id: number;
  mortality_rate: number;
}

const PatientPage: React.FC<PatientPageProps> = ({
  data,
  featureDetails,
  stay_id,
  mortality_rate,
}) => {
  const router = useRouter();

  // Handles search queries and navigates to the patient's page
  const handleSearch = (query: string) => {
    router.push(`/patients/${query}`);
  };

  // Formats date strings into a more readable format
  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    const date = new Date(dateString);
    return date.toLocaleDateString("en-GB", options);
  };

  // Formats the ICU stay length in hours to two decimal places
  const formatICUStay = (hours: number) => {
    return hours.toFixed(2);
  };

  return (
    <div
      style={{
        position: "relative",
        height: "90vh",
        paddingLeft: "20px",
        paddingRight: "20px",
        paddingTop: "20px",
        gap: "20px",
        display: "grid",
        gridTemplateRows: "auto 1fr",
        gridTemplateColumns: "1fr 1fr",
      }}
    >
      {/* Display readmission status and mortality rate */}
      <div style={{ gridColumn: "1 / span 1", paddingTop: "50px" }}>
        <ReadmissionStatus
          will_be_readmitted={data.percentage}
          mortality_rate={mortality_rate}
        />
      </div>

      {/* Display past 6 days data in a card */}
      <div
        style={{
          gridColumn: "1 / span 1",
          gridRow: "2 / span 1",
          height: "475px",
        }}
      >
        <Card style={{ height: "100%", width: "auto" }}>
          <CardContent>
            <Typography variant="h6">Past 6 days data</Typography>
            {data && (
              <PatientTable
                readmissionLikelihood={data.percentage}
                lengthOfStay={data.los_hour_int}
                stayId={data.stay_id}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Display patient information in a card */}
      <div
        style={{
          gridColumn: "2 / span 1",
          gridRow: "1 / span 1",
          paddingTop: "70px",
        }}
      >
        {data && (
          <Card style={{ height: "auto", width: "100%" }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Patient Information
              </Typography>
              <Typography>
                <strong>Stay ID:</strong> {data.stay_id}
              </Typography>
              <Typography>
                <strong>Name:</strong> {data.name}
              </Typography>
              <Typography>
                <strong>Age:</strong> {data.age}
              </Typography>
              <Typography>
                <strong>Gender:</strong> {data.gender}
              </Typography>
              <Typography>
                <strong>ICU Length of Stay:</strong>{" "}
                {formatICUStay(data.los_hour_int)} hours
              </Typography>
              <Typography>
                <strong>In Time:</strong> {formatDate(data.intime)}
              </Typography>
              <Typography>
                <strong>Out Time:</strong> {formatDate(data.outtime)}
              </Typography>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Display feature details in a FeatureCard */}
      <div
        style={{
          gridColumn: "2 / span 1",
          gridRow: "2 / span 1",
          height: "475px",
        }}
      >
        {featureDetails && (
          <Card
            style={{
              height: "100%",
              width: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <CardContent style={{ flex: 1, overflow: "auto" }}>
              <FeatureCard featureDetails={featureDetails} stay_id={stay_id} />
            </CardContent>
          </Card>
        )}
      </div>

      {/* Search bar positioned at the top left of the page */}
      <div
        style={{
          position: "absolute",
          top: "20px",
          left: "20px",
          zIndex: 999,
          width: "100%",
        }}
      >
        <SearchBar onSearch={handleSearch} />
      </div>
    </div>
  );
};

export default PatientPage;
