import "@testing-library/jest-dom";
import { TextEncoder, TextDecoder } from "util";

globalThis.TextEncoder = TextEncoder;
globalThis.TextDecoder = TextDecoder;

if (typeof window.URL.createObjectURL === "undefined") {
  window.URL.createObjectURL = jest.fn(() => "blob:mock");
}

