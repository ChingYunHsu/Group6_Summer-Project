const maplibregl = {
  Map: jest.fn().mockImplementation(() => ({
    addControl: jest.fn(),
    remove: jest.fn(),
    on: jest.fn(),
  })),
  Marker: jest.fn().mockImplementation(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  })),
  Popup: jest.fn().mockImplementation(() => ({
    setHTML: jest.fn().mockReturnThis(),
  })),
  NavigationControl: jest.fn(),
};

module.exports = maplibregl;