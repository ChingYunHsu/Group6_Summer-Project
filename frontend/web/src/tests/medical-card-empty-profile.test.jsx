import { render, screen } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router-dom";
import MedicalCard from "../pages/MedicalCard";
import {
  getMedicalProfile,
} from "../services/MedicalProfileApi";
import {
  getUserProfile,
} from "../services/UserProfileApi";

jest.mock("../services/MedicalProfileApi", () => ({
  getMedicalProfile: jest.fn(),
}));

jest.mock("../services/UserProfileApi", () => ({
  getUserProfile: jest.fn(),
}));

describe("Medical Card empty profile rendering", () => {
  beforeEach(() => {
    getUserProfile.mockResolvedValue({
      full_name: "",
      display_name: "",
      email: "",
      phone: "",
      nationality: "",
      spoken_languages: [],
    });

    getMedicalProfile.mockResolvedValue({
      date_of_birth: "",
      gender: "",
      blood_type: "",
      address: "",
      allergies: [],
      medical_conditions: [],
      medications: [],
      emergency_contacts: [],
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test("renders an empty medical document until the user adds details", async () => {
    render(
      <MemoryRouter initialEntries={["/medical-card"]}>
        <Routes>
          <Route
            path="/medical-card"
            element={<MedicalCard />}
          />
        </Routes>
      </MemoryRouter>
    );

    expect(
      await screen.findByText(/^MEDICAL ALERT$/i)
    ).toBeInTheDocument();

    expect(
      screen.getByText(/^ALERTA MÉDICA$/i)
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /No known allergies listed/i
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /No medical conditions listed/i
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /No emergency contact listed/i
      )
    ).toBeInTheDocument();
  });
});