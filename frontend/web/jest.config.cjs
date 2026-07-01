module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/src/setupTests.js"],
  moduleNameMapper: {
    "\\.(css|less|scss|sass)$": "<rootDir>/src/__mocks__/fileMock.js",
    "^maplibre-gl$": "<rootDir>/src/__mocks__/maplibre-gl.js",
  },
  transform: {
    "^.+\\.[jt]sx?$": "babel-jest",
  },
};