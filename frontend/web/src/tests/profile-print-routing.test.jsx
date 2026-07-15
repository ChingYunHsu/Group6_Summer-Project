import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router-dom";
import Profile from "../pages/Profile";
import MedicalCard from "../pages/MedicalCard";

describe("Web Page 6-1 print medical card flow", () => {
  test(
    "clicking Print Medical Card opens Web Page 6-2",
    async () => {
      const user = userEvent.setup();

      render(
        <MemoryRouter initialEntries={["/profile"]}>
          <Routes>
            <Route
              path="/profile"
              element={<Profile />}
            />

            <Route
              path="/medical-card"
              element={<MedicalCard />}
            />
          </Routes>
        </MemoryRouter>
      );

      const printButton = await screen.findByRole(
        "button",
        {
          name: /print medical card/i,
        }
      );

      await user.click(printButton);

      expect(
        await screen.findByText(
          /medical document preview/i
        )
      ).toBeInTheDocument();

      expect(
        screen.getByText(/^medical alert$/i)
      ).toBeInTheDocument();

      expect(
        screen.getByText(/^alerta médica$/i)
      ).toBeInTheDocument();
    }
  );
});