import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

describe("Navigation bar routing", () => {
  test("renders navigation links without crashing", () => {
    render(<App />);

    expect(screen.getByRole("link", { name: /ClearPath/i }))
    .toBeInTheDocument();
    expect(screen.getByText(/Live Help Map/i)).toBeInTheDocument();
    expect(screen.getByText(/Insights Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/About Us/i)).toBeInTheDocument();
    expect(screen.getByText(/User Guide/i)).toBeInTheDocument();
  });

  test("clicking Profile navigates to profile page", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: /👩🏻‍⚕️/i }));

    await user.click(screen.getByRole("link", { name: /^Profile$/i }));

    expect(
      screen.getByRole("heading", {
        name: /Personal & Medical Profile/i,
      })
    ).toBeInTheDocument();
  });
});
