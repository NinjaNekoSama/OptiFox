import { notFound } from "next/navigation";
import FeatureCard from "@/components/FC/FeatureCard";
import PatientPage from "@/components/PatientPage";

// Fetch patient data by ID
async function fetchPatient(id: any) {
  const res = await fetch(
    `http://0.0.0.0:3000/api/v1/predict_readmission/${id}`
  );
  if (!res.ok) {
    return null;
  }
  const data = await res.json();
  return data;
}

// Array of features to be fetched
const features = [
  "Heart Rate",
  "Pain Level",
  "Phosphorous",
  "Respiratory Rate",
  "Temperature Celsius",
  "Braden Score",
  "Glucose",
  "Platelet Count",
];

// Fetch details for a specific feature of the patient
async function fetchFeatureDetails(id: any, feature: any) {
  const res = await fetch(
    `http://0.0.0.0:3000/api/v1/patient/${id}/${feature}`
  );
  if (!res.ok) {
    return { [feature]: {} };
  }
  const data = await res.json();
  return data;
}

export default async function SinglePatientPage({ params }: any) {
  // Retrieve patient data
  const patient: any = await fetchPatient(params.stayId);
  if (!patient) {
    notFound();
  }

  // Collect feature details
  const featureDetails: Record<string, Record<string, number | null>> = {};
  for (const feature of features) {
    const featureData = await fetchFeatureDetails(params.stayId, feature);
    featureDetails[feature] = featureData[feature]; // Only extracting the relevant data
  }

  // Simulate a mortality rate (for demonstration purposes)
  const mortality_rate = Math.floor(Math.random() * 100) + 1;

  return (
    <div>
      {/* Render the patient page with fetched data */}
      <PatientPage
        data={patient}
        featureDetails={featureDetails}
        stay_id={params.stayId}
        mortality_rate={mortality_rate}
      />
    </div>
  );
}
