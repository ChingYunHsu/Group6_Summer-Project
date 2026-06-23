import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import MedicalCard from "../pages/MedicalCard";

const injectedPayload = {
  full_name: "Elena Rostova",
  email: "elena@example.com",
  phone: "+1 (555) 019-2834",
  date_of_birth: "1988-04-12",
  gender: "Female",
  nationality: "Russian",
  address: "1248 Medical Parkway, Suite 300, Boston, MA 02115",
  blood_type: "O+",
  donor_status: "O Positive",
  spoken_languages: ["Russian", "English"],
  allergies: [
    { name: "Penicillin", detail: "Severe reaction" },
    { name: "Latex", detail: "Moderate rash" },
  ],
  conditions: [
    { name: "Asthma", detail: "Managed with inhaler" },
    { name: "Hypothyroidism", detail: "Daily medication" },
  ],
  emergency_contacts: [
    {
      name: "Marcus Rostova",
      relationship: "Spouse",
      phone: "+41 79 987 65 43",
      primary: true,
    },
  ],
};

describe("Web Page 6-2 injected P2P payload rendering", () => {
  test("renders bilingual A4 document from routing state payload", () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/medical-card",
            state: { clinicalPayload: injectedPayload },
          },
        ]}
      >
        <Routes>
          <Route path="/medical-card" element={<MedicalCard />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/MEDICAL ALERT/i)).toBeInTheDocument();
    expect(screen.getByText(/ALERTA MÉDICA/i)).toBeInTheDocument();

    expect(screen.getByText(/Elena Rostova/i)).toBeInTheDocument();
    expect(screen.getByText(/O\+/i)).toBeInTheDocument();
    expect(screen.getByText(/Penicillin/i)).toBeInTheDocument();
    expect(screen.getByText(/Latex/i)).toBeInTheDocument();
    expect(screen.getByText(/Asthma/i)).toBeInTheDocument();
    expect(screen.getByText(/Hypothyroidism/i)).toBeInTheDocument();
    expect(screen.getByText(/Marcus Rostova/i)).toBeInTheDocument();
    expect(screen.getByText(/\+41 79 987 65 43/i)).toBeInTheDocument();
  });
});