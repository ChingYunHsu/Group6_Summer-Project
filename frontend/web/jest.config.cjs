module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/src/setupTests.js"],
  moduleNameMapper: {
    "\\.(css|less|scss|sass)$": "identity-obj-proxy",
  },
  "moduleNameMapper": {
  "^maplibre-gl$": "<rootDir>/src/__mocks__/maplibre-gl.js"
}
};