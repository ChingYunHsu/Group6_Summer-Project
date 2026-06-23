import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Profile from "../pages/Profile";
import MedicalCard from "../pages/MedicalCard";

describe("Web Page 6-1 print medical card flow", () => {
  test("clicking Print Medical Card opens Web Page 6-2", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <Routes>
          <Route path="/profile" element={<Profile />} />
          <Route path="/medical-card" element={<MedicalCard />} />
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: /print medical card/i }));

    expect(screen.getByText(/Medical Document Preview/i)).toBeInTheDocument();
    expect(screen.getByText(/MEDICAL ALERT/i)).toBeInTheDocument();
    expect(screen.getByText(/ALERTA MÉDICA/i)).toBeInTheDocument();
  });
});