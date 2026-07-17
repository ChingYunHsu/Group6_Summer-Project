module.exports = {
  testEnvironment: "jsdom",

  setupFilesAfterEnv: [
    "<rootDir>/src/setupTests.js",
  ],

  moduleNameMapper: {
    "\\.(css|less|scss|sass)$":
      "<rootDir>/src/__mocks__/fileMock.js",

    "\\.(jpg|jpeg|png|gif|webp|svg)$":
      "<rootDir>/src/__mocks__/fileMock.js",

    "^maplibre-gl$":
      "<rootDir>/src/__mocks__/maplibre-gl.js",

    "^\\./apiClient$":
      "<rootDir>/src/__mocks__/apiClientMock.js",

    "LiveHelpMapApi$":
      "<rootDir>/src/__mocks__/LiveHelpMapApiMock.js",

    "InsightsDashboardApi$":
      "<rootDir>/src/__mocks__/InsightsDashboardApiMock.js",

    "FavouritesApi$":
      "<rootDir>/src/__mocks__/FavouritesApiMock.js",
  },

  transform: {
    "^.+\\.[jt]sx?$": "babel-jest",
  },
};